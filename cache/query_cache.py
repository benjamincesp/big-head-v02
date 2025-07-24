"""
Intelligent Query Cache for Food Service 2025
Implements similarity-based caching with learning patterns
"""

import hashlib
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from difflib import SequenceMatcher
from .redis_manager import RedisManager

logger = logging.getLogger(__name__)

class QueryCache:
    def __init__(self, redis_manager: RedisManager, default_ttl: int = 3600):
        """
        Initialize query cache with intelligent similarity detection
        
        Args:
            redis_manager: Redis connection manager
            default_ttl: Default TTL for cache entries in seconds
        """
        self.redis = redis_manager
        self.default_ttl = default_ttl
        self.similarity_threshold = 0.8  # 80% similarity threshold
        
        # Cache prefixes
        self.QUERY_PREFIX = "fs2024:query:"
        self.COUNTER_PREFIX = "fs2024:counter:"
        self.SIMILARITY_PREFIX = "fs2024:similarity:"
        self.STATS_PREFIX = "fs2024:stats:"
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for better matching"""
        return query.lower().strip().replace("  ", " ")
    
    def _generate_cache_key(self, query: str, agent_type: str = "general") -> str:
        """Generate cache key for query"""
        normalized = self._normalize_query(query)
        query_hash = hashlib.md5(normalized.encode()).hexdigest()
        return f"{self.QUERY_PREFIX}{agent_type}:{query_hash}"
    
    def _generate_similarity_key(self, query: str, agent_type: str = "general") -> str:
        """Generate similarity tracking key"""
        normalized = self._normalize_query(query)
        query_hash = hashlib.md5(normalized.encode()).hexdigest()
        return f"{self.SIMILARITY_PREFIX}{agent_type}:{query_hash}"
    
    def _calculate_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries"""
        norm1 = self._normalize_query(query1)
        norm2 = self._normalize_query(query2)
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _find_similar_cached_queries(self, query: str, agent_type: str) -> List[Tuple[str, float, str]]:
        """Find similar cached queries above threshold"""
        if not self.redis.is_connected():
            return []
        
        similar_queries = []
        pattern = f"{self.SIMILARITY_PREFIX}{agent_type}:*"
        
        try:
            similarity_keys = self.redis.get_keys_pattern(pattern)
            
            for sim_key in similarity_keys:
                stored_data = self.redis.get(sim_key)
                if stored_data and isinstance(stored_data, dict):
                    stored_query = stored_data.get("original_query", "")
                    similarity = self._calculate_similarity(query, stored_query)
                    
                    if similarity >= self.similarity_threshold:
                        cache_key = stored_data.get("cache_key", "")
                        similar_queries.append((stored_query, similarity, cache_key))
            
            # Sort by similarity (descending)
            similar_queries.sort(key=lambda x: x[1], reverse=True)
            return similar_queries[:3]  # Return top 3 similar queries
            
        except Exception as e:
            logger.error(f"Error finding similar queries: {str(e)}")
            return []
    
    def get(self, query: str, agent_type: str = "general") -> Optional[Dict[str, Any]]:
        """
        Get cached response for query, including similarity-based matches
        """
        if not self.redis.is_connected():
            return None
        
        # Try exact match first
        cache_key = self._generate_cache_key(query, agent_type)
        cached_result = self.redis.get(cache_key)
        
        if cached_result:
            # Increment hit counter
            counter_key = f"{self.COUNTER_PREFIX}{cache_key}"
            self.redis.incr(counter_key)
            
            logger.info(f"Cache HIT (exact) for query: {query[:50]}...")
            
            if isinstance(cached_result, dict):
                cached_result["cache_hit"] = True
                cached_result["cache_type"] = "exact"
                return cached_result
        
        # Try similarity-based matching
        similar_queries = self._find_similar_cached_queries(query, agent_type)
        
        for similar_query, similarity, similar_cache_key in similar_queries:
            if similar_cache_key:
                similar_result = self.redis.get(similar_cache_key)
                if similar_result and isinstance(similar_result, dict):
                    # Increment similarity hit counter
                    counter_key = f"{self.COUNTER_PREFIX}{similar_cache_key}"
                    self.redis.incr(counter_key)
                    
                    logger.info(f"Cache HIT (similar {similarity:.2f}) for query: {query[:50]}...")
                    
                    similar_result["cache_hit"] = True
                    similar_result["cache_type"] = "similar"
                    similar_result["similarity_score"] = similarity
                    similar_result["original_query"] = similar_query
                    return similar_result
        
        logger.info(f"Cache MISS for query: {query[:50]}...")
        return None
    
    def set(self, query: str, response: Dict[str, Any], agent_type: str = "general", ttl: int = None) -> bool:
        """
        Cache query response with similarity tracking
        """
        if not self.redis.is_connected():
            return False
        
        ttl = ttl or self.default_ttl
        
        try:
            # Store main cache entry
            cache_key = self._generate_cache_key(query, agent_type)
            cache_data = {
                **response,
                "cached_at": time.time(),
                "query": query,
                "agent_type": agent_type,
                "ttl": ttl
            }
            
            success = self.redis.set(cache_key, cache_data, ex=ttl)
            
            if success:
                # Store similarity tracking data
                similarity_key = self._generate_similarity_key(query, agent_type)
                similarity_data = {
                    "original_query": query,
                    "cache_key": cache_key,
                    "agent_type": agent_type,
                    "created_at": time.time()
                }
                self.redis.set(similarity_key, similarity_data, ex=ttl)
                
                # Initialize hit counter
                counter_key = f"{self.COUNTER_PREFIX}{cache_key}"
                self.redis.set(counter_key, 0, ex=ttl)
                
                logger.info(f"Cached response for query: {query[:50]}...")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error caching query response: {str(e)}")
            return False
    
    def invalidate_agent_cache(self, agent_type: str) -> bool:
        """Invalidate all cache entries for a specific agent"""
        if not self.redis.is_connected():
            return False
        
        try:
            patterns = [
                f"{self.QUERY_PREFIX}{agent_type}:*",
                f"{self.SIMILARITY_PREFIX}{agent_type}:*",
                f"{self.COUNTER_PREFIX}*{agent_type}:*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                keys = self.redis.get_keys_pattern(pattern)
                for key in keys:
                    if self.redis.delete(key):
                        deleted_count += 1
            
            logger.info(f"Invalidated {deleted_count} cache entries for agent: {agent_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache for agent {agent_type}: {str(e)}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        if not self.redis.is_connected():
            return {"connected": False}
        
        try:
            stats = {
                "connected": True,
                "redis_stats": self.redis.get_stats(),
                "agent_stats": {}
            }
            
            # Get stats for each agent type
            for agent_type in ["general", "exhibitors", "visitors"]:
                query_pattern = f"{self.QUERY_PREFIX}{agent_type}:*"
                counter_pattern = f"{self.COUNTER_PREFIX}*{agent_type}:*"
                
                query_keys = self.redis.get_keys_pattern(query_pattern)
                counter_keys = self.redis.get_keys_pattern(counter_pattern)
                
                total_hits = 0
                for counter_key in counter_keys:
                    hits = self.redis.get(counter_key)
                    if hits and isinstance(hits, (int, str)):
                        total_hits += int(hits)
                
                stats["agent_stats"][agent_type] = {
                    "cached_queries": len(query_keys),
                    "total_hits": total_hits,
                    "avg_hits_per_query": round(total_hits / len(query_keys), 2) if query_keys else 0
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"connected": False, "error": str(e)}
    
    def clear_all_cache(self) -> bool:
        """Clear all Food Service 2025 cache entries"""
        if not self.redis.is_connected():
            return False
        
        try:
            patterns = [
                f"{self.QUERY_PREFIX}*",
                f"{self.SIMILARITY_PREFIX}*",
                f"{self.COUNTER_PREFIX}*",
                f"{self.STATS_PREFIX}*"
            ]
            
            deleted_count = 0
            for pattern in patterns:
                keys = self.redis.get_keys_pattern(pattern)
                for key in keys:
                    if self.redis.delete(key):
                        deleted_count += 1
            
            logger.info(f"Cleared {deleted_count} cache entries")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False