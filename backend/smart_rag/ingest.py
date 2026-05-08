from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import logging
import os
import json
import hashlib
import pickle
from datetime import datetime
import redis
import shutil

from utils.text_utils import clean_text
from utils.validation_utils import validate_text
from utils.file_utils import extract_text_from_pdf, extract_text_from_docx
from utils.config import settings


VECTOR_STORE_PATH = settings.VECTOR_STORE_PATH
MAX_SOURCES = 5

logger = logging.getLogger(__name__)

# Redis connection (singleton)

_redis_client = None

def get_redis_client():
    global _redis_client

    if _redis_client is None:
        logger.info("Connecting to Redis...")
        try:
            _redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=False,
                socket_connect_timeout=3,
                socket_timeout=3
            )
            _redis_client.ping()
            logger.info("✓ Redis connected")
        except Exception as e:
            logger.error(f"✗ Redis connection failed: {e}")
            # Don't raise - allow app to run without cache
            _redis_client = None
            return None

    return _redis_client


# Redis SAFE SCAN helper (replaces KEYS)

def scan_keys(pattern: str):

    r = get_redis_client()
    if r is None:
        logger.info("Redis not available, returning empty keys")
        return []
        
    cursor = 0
    keys = []

    while True:
        cursor, batch = r.scan(cursor=cursor, match=pattern, count=100)
        keys.extend(batch)
        if cursor == 0:
            break

    return keys


# Redis health checks

def check_redis_connection():
    try:
        r = get_redis_client()
        if r is None:
            return {
                "connected": False,
                "error": "Redis client is not available"
            }
        r.ping()
        info = r.info("server")

        return {
            "connected": True,
            "redis_version": info.get("redis_version"),
            "uptime_seconds": info.get("uptime_in_seconds")
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e)
        }


def get_redis_health():
    try:
        r = get_redis_client()
        if r is None:
            return {
                "status": "unavailable",
                "error": "Redis client is not available"
            }

        all_keys = scan_keys("*")
        chunk_keys = scan_keys("chunks:*")
        memory = r.info("memory")

        return {
            "status": "healthy",
            "total_keys": len(all_keys),
            "chunk_keys": len(chunk_keys),
            "metadata_exists": r.exists("vector_store:metadata") == 1,
            "memory_used_mb": round(memory.get("used_memory", 0) / (1024 * 1024), 2)
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Embeddings singleton

_embeddings = None

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings


# Helper functions

def compute_content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Query cache invalidation

def invalidate_query_cache():

    try:
        r = get_redis_client()
        if r is None:
            logger.info("Redis not available, skipping cache invalidation")
            return False
            
        deleted_count = 0
        
        # Delete query cache
        if r.exists("rag:query_cache"):
            r.delete("rag:query_cache")
            deleted_count += 1
            
        # Delete query order
        if r.exists("rag:query_order"):
            r.delete("rag:query_order")
            deleted_count += 1
            
        if deleted_count > 0:
            logger.info(f"Query cache invalidated ({deleted_count} keys cleared)")
            
        return True
    except Exception as e:
        logger.error(f"Failed to invalidate query cache: {e}")
        return False


# Metadata management (Redis)

def load_metadata():
    try:
        r = get_redis_client()
        if r is None:
            logger.info("Redis not available, using empty metadata")
            return {"sources": [], "source_order": []}
            
        data = r.get("vector_store:metadata")

        if data:
            return json.loads(data.decode("utf-8"))

        return {"sources": [], "source_order": []}

    except Exception as e:
        logger.error(f"Metadata load failed: {e}")
        return {"sources": [], "source_order": []}


def save_metadata(metadata: dict):
    r = get_redis_client()
    if r is None:
        logger.warning("Redis not available, metadata not saved")
        return
    r.set("vector_store:metadata", json.dumps(metadata, indent=2))


# Chunk cache management (Redis)

def load_chunks_cache():
    r = get_redis_client()
    if r is None:
        logger.info("Redis not available, chunks cache empty")
        return {}
        
    cache = {}

    for key in scan_keys("chunks:*"):
        source_id = key.decode().replace("chunks:", "")
        data = r.get(key)
        if data:
            cache[source_id] = pickle.loads(data)

    return cache


def save_chunks_for_source(source_id: str, chunks):
    r = get_redis_client()
    if r is None:
        logger.warning("Redis not available, chunks not saved")
        return
    r.set(f"chunks:{source_id}", pickle.dumps(chunks))


def delete_chunks_for_source(source_id: str):
    r = get_redis_client()
    if r is None:
        logger.warning("Redis not available, chunks not deleted")
        return
    r.delete(f"chunks:{source_id}")


# Duplicate content checking

def check_duplicate_content(content_hash: str, metadata: dict):
    for src in metadata["sources"]:
        if src["content_hash"] == content_hash:
            return {"is_duplicate": True, "existing_source": src}
    return {"is_duplicate": False}


# FAISS vector store rebuild

def rebuild_vector_store_without_source(remove_source_id: str):
    chunks_cache = load_chunks_cache()
    all_chunks = []

    for sid, chunks in chunks_cache.items():
        if sid != remove_source_id:
            all_chunks.extend(chunks)

    if not all_chunks:
        return None

    return FAISS.from_documents(all_chunks, get_embeddings())


# Ingest raw text

def ingest_raw_text(raw_text: str, source_name: str = "api"):
    validate_text(raw_text)
    raw_text = clean_text(raw_text)

    content_hash = compute_content_hash(raw_text)
    metadata = load_metadata()

    dup = check_duplicate_content(content_hash, metadata)
    if dup["is_duplicate"]:
        return {
            "duplicate": True,
            "message": "Content already exists",
            "existing_source": dup["existing_source"]["source_name"],
            "current_sources": len(metadata["sources"]),
            "max_sources": MAX_SOURCES
        }

    timestamp = datetime.now().isoformat()
    source_id = f"{source_name}_{timestamp}"

    document = Document(
        page_content=raw_text,
        metadata={
            "source": source_name,
            "source_id": source_id,
            "timestamp": timestamp,
            "content_hash": content_hash
        }
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents([document])

    embeddings = get_embeddings()
    removed_source = None

    if len(metadata["source_order"]) >= MAX_SOURCES:
        oldest = metadata["source_order"].pop(0)

        for i, src in enumerate(metadata["sources"]):
            if src["source_id"] == oldest:
                removed_source = src["source_name"]
                metadata["sources"].pop(i)
                break

        delete_chunks_for_source(oldest)
        vector_store = rebuild_vector_store_without_source(oldest)

        if vector_store is None:
            vector_store = FAISS.from_documents(chunks, embeddings)
        else:
            vector_store.add_documents(chunks)

    else:
        if os.path.exists(VECTOR_STORE_PATH):
            vector_store = FAISS.load_local(
                VECTOR_STORE_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
            vector_store.add_documents(chunks)
        else:
            vector_store = FAISS.from_documents(chunks, embeddings)

    save_chunks_for_source(source_id, chunks)

    metadata["sources"].append({
        "source_id": source_id,
        "source_name": source_name,
        "timestamp": timestamp,
        "num_chunks": len(chunks),
        "content_hash": content_hash
    })
    metadata["source_order"].append(source_id)

    vector_store.save_local(VECTOR_STORE_PATH)
    save_metadata(metadata)

    # Invalidate query cache since new content was added
    invalidate_query_cache()

    return {
        "duplicate": False,
        "message": "Content ingested successfully",
        "chunks_added": len(chunks),
        "removed_source": removed_source,
        "current_sources": len(metadata["sources"]),
        "max_sources": MAX_SOURCES,
        "source_id": source_id
    }


# Ingest file content

def ingest_file_content(file_bytes: bytes, filename: str):
    name = filename.lower()

    if name.endswith(".txt"):
        text = file_bytes.decode("utf-8")
    elif name.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif name.endswith(".docx"):
        text = extract_text_from_docx(file_bytes)
    else:
        raise ValueError("Unsupported file format")

    return ingest_raw_text(text, filename)


# Admin helper functions

def get_current_sources():
    metadata = load_metadata()
    return {
        "sources": metadata["sources"],
        "count": len(metadata["sources"]),
        "max_sources": MAX_SOURCES
    }


def get_active_source_ids():
    metadata = load_metadata()
    return set(metadata["source_order"])


def clear_all_sources():
    r = get_redis_client()

    keys = scan_keys("chunks:*")
    if keys and r is not None:
        r.delete(*keys)

    if r is not None:
        r.delete("vector_store:metadata")

    if os.path.exists(VECTOR_STORE_PATH):
        shutil.rmtree(VECTOR_STORE_PATH)

    # Invalidate query cache
    invalidate_query_cache()

    return "All sources cleared"
