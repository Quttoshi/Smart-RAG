import json
import hashlib
from typing import Optional, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RedisQueryCache:
    
    def __init__(
        self,
        redis_client,
        max_queries: int = 5,
        ttl: int = 3600 
    ):
        self.client = redis_client
        self.max_queries = max_queries
        self.ttl = ttl
        self.cache_key = "rag:query_cache"
        self.order_key = "rag:query_order"
        
        logger.info("Query cache initialized with existing Redis connection")

    def _generate_key(self, question: str, k: int = 3) -> str:
        query_str = f"{question.lower().strip()}:{k}"
        return hashlib.md5(query_str.encode()).hexdigest()

    def get(self, question: str, k: int = 3) -> Optional[Dict[str, Any]]:
        try:
            query_key = self._generate_key(question, k)
            cached_data = self.client.hget(self.cache_key, query_key)
            
            if cached_data:
                logger.info(f"Cache HIT for query: {question[:50]}...")
                
                self.client.lrem(self.order_key, 0, query_key)
                self.client.rpush(self.order_key, query_key)
                
                return json.loads(cached_data.decode("utf-8"))
            
            logger.info(f"Cache MISS for query: {question[:50]}...")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def set(self, question: str, response: Dict[str, Any], k: int = 3) -> bool:
        try:
            query_key = self._generate_key(question, k)
            
            cache_entry = {
                "question": question,
                "k": k,
                "response": response
            }
            
            # Add to hash
            self.client.hset(
                self.cache_key,
                query_key,
                json.dumps(cache_entry)
            )
            
            self.client.lrem(self.order_key, 0, query_key)
            self.client.rpush(self.order_key, query_key)
            
            current_size = self.client.llen(self.order_key)
            if current_size > self.max_queries:
     
                oldest_key = self.client.lpop(self.order_key)
                if oldest_key:
                    self.client.hdel(self.cache_key, oldest_key)
                    logger.info(f"Evicted oldest cache entry to maintain limit of {self.max_queries}")
            

            self.client.expire(self.cache_key, self.ttl)
            self.client.expire(self.order_key, self.ttl)
            
            logger.info(f"Cached response for query: {question[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False

    def clear(self) -> bool:
   
        try:
            self.client.delete(self.cache_key)
            self.client.delete(self.order_key)
            logger.info("Query cache cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:

        try:
            size = self.client.hlen(self.cache_key)
            ttl = self.client.ttl(self.cache_key)

            query_keys = self.client.lrange(self.order_key, 0, -1)
            cached_queries = []
            
            for qkey in query_keys[-5:]:
                data = self.client.hget(self.cache_key, qkey)
                if data:
                    entry = json.loads(data.decode("utf-8"))
                    cached_queries.append({
                        "question": entry["question"][:100],
                        "k": entry["k"]
                    })
            
            return {
                "cached_queries": size,
                "max_queries": self.max_queries,
                "ttl_seconds": ttl if ttl > 0 else None,
                "recent_queries": list(reversed(cached_queries)) 
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "cached_queries": 0,
                "max_queries": self.max_queries,
                "ttl_seconds": None,
                "recent_queries": []
            }

    def invalidate_all(self) -> bool:
        return self.clear()