from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import anyio

from rag.smart_rag import SmartRAG
from utils.logger import setup_logger

router = APIRouter(prefix="/api", tags=["Query"])
logger = setup_logger(__name__)


class QueryRequest(BaseModel):
    question: str
    k: Optional[int] = 3
    use_cache: Optional[bool] = True


class QueryResponse(BaseModel):
    answer: str
    context: str
    num_sources: int
    sources: Optional[List[str]] = None
    cached: bool = False


class CacheStatsResponse(BaseModel):
    cached_queries: int
    max_queries: int
    ttl_seconds: Optional[int]
    recent_queries: List[Dict[str, Any]]


@router.get("/health")
async def health():

    return {
        "status": "ok"
    }


@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):

    try:
        # Initialize RAG with cache setting
        rag = SmartRAG(use_cache=req.use_cache)
        
        result = await anyio.to_thread.run_sync(
            rag.query, req.question, req.k
        )

        if isinstance(result, str):
            raise HTTPException(status_code=404, detail=result)

        sources = [
            chunk.strip()
            for chunk in result["context"].split("\n\n")
            if chunk.strip()
        ] if result["context"] else []

        return QueryResponse(
            answer=result["answer"],
            context=result["context"],
            num_sources=result["num_sources"],
            sources=sources,
            cached=result.get("cached", False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error while handling query")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats():

    try:
        rag = SmartRAG()
        stats = await anyio.to_thread.run_sync(rag.get_cache_stats)
        
        if "error" in stats:
            raise HTTPException(status_code=503, detail=stats["error"])
        
        return CacheStatsResponse(**stats)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error getting cache stats")
        raise HTTPException(status_code=500, detail=str(e))