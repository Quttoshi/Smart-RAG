from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
from typing import Dict, Any

from utils.config import GROQ_API_KEY, VECTOR_STORE_PATH
from utils.faiss_utils import load_faiss_store
from utils.logger import setup_logger

from smart_rag.ingest import get_redis_client
from smart_rag.redis_cache import RedisQueryCache

logger = setup_logger(__name__)


class SmartRAG:
    def __init__(
        self,
        vector_store_path=VECTOR_STORE_PATH,
        use_cache: bool = True
    ):
        self.vector_store_path = vector_store_path
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vector_store = None

        self.client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Initialize query cache using existing Redis connection
        self.use_cache = use_cache
        self.cache = None
        
        if use_cache:
            try:
                redis_client = get_redis_client()
                if redis_client is not None:
                    self.cache = RedisQueryCache(
                        redis_client=redis_client,
                        max_queries=5,
                        ttl=3600  # 1 hour cache
                    )
                    logger.info("Query cache initialized using existing Redis connection")
                else:
                    logger.warning("Redis client is None. Proceeding without cache.")
                    self.use_cache = False
            except Exception as e:
                logger.warning(f"Failed to initialize query cache: {e}. Proceeding without cache.")
                self.use_cache = False

    def load_vector_store(self):
        
        self.vector_store = load_faiss_store(
            self.vector_store_path,
            self.embeddings
        )
        logger.info("FAISS vector store loaded successfully")

    def query(self, question: str, k: int = 3) -> Dict[str, Any]:

        # Check cache first
        if self.use_cache and self.cache:
            cached_response = self.cache.get(question, k)
            if cached_response:
                logger.info("Returning cached response")
                # Add cached flag to response
                cached_response["response"]["cached"] = True
                return cached_response["response"]
        
        # Cache miss - proceed with normal RAG pipeline
        logger.info("Loading latest vector store for query...")
        self.load_vector_store()
        
        if self.vector_store is None:
            return {
                "answer": "No vector store found. Please ingest documents first.",
                "context": "",
                "num_sources": 0,
                "cached": False
            }

        # Perform similarity search
        docs = self.vector_store.similarity_search(question, k=k)
        if not docs:
            return {
                "answer": "No relevant information found.",
                "context": "",
                "num_sources": 0,
                "cached": False
            }

    
        context = "\n\n".join(d.page_content for d in docs)

        prompt = f"""
Context:
{context}

Question: {question}
Answer:
"""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Answer strictly from context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        result = {
            "answer": response.choices[0].message.content,
            "context": context,
            "num_sources": len(docs),
            "cached": False
        }
        
        # Cache the result
        if self.use_cache and self.cache:
            self.cache.set(question, result, k)
        
        return result

    def clear_cache(self) -> bool:
        """Clear the query cache."""
        if self.cache:
            return self.cache.clear()
        return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return {"error": "Cache not initialized"}

    def invalidate_cache(self) -> bool:

        if self.cache:
            logger.info("Invalidating query cache after document ingestion")
            return self.cache.invalidate_all()
        return False