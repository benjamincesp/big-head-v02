"""
Intelligent Query Cache for Food Service 2025
Implements similarity-based caching with learning patterns
"""

import hashlib
import logging
import time
import json
import os
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
    
    def set(self, query: str, response: Dict[str, Any], agent_type: str = "general", ttl: int = None, force_overwrite: bool = False) -> bool:
        """
        Cache query response with similarity tracking
        
        Args:
            query: User query
            response: Response to cache
            agent_type: Type of agent
            ttl: Time to live
            force_overwrite: Force overwrite existing cache entry
        """
        if not self.redis.is_connected():
            return False
        
        ttl = ttl or self.default_ttl
        
        try:
            # Store main cache entry
            cache_key = self._generate_cache_key(query, agent_type)
            
            # Check if entry exists and force_overwrite is needed
            if not force_overwrite and self.redis.exists(cache_key):
                logger.info(f"Cache entry already exists for query: {query[:50]}... (not overwriting)")
            
            cache_data = {
                **response,
                "cached_at": time.time(),
                "query": query,
                "agent_type": agent_type,
                "ttl": ttl,
                "force_overwritten": force_overwrite
            }
            
            success = self.redis.set(cache_key, cache_data, ex=ttl)
            
            if success and force_overwrite:
                logger.info(f"Cache forcibly overwritten for query: {query[:50]}...")
            
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
    
    def _get_cache_backup_path(self) -> str:
        """Get path for cache backup file"""
        backup_dir = "vector_stores/backups"
        os.makedirs(backup_dir, exist_ok=True)
        return os.path.join(backup_dir, "query_cache_backup.json")
    
    def backup_cache_to_file(self) -> bool:
        """Backup critical cache entries to file"""
        try:
            backup_data = {
                "timestamp": time.time(),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "queries": {},
                "stats": {},
                "total_entries": 0
            }
            
            # Backup recent popular queries (last 100)
            patterns = [f"{self.QUERY_PREFIX}*"]
            
            for pattern in patterns:
                keys = self.redis.get_keys_pattern(pattern)[:100]  # Limit to avoid huge files
                for key in keys:
                    try:
                        value = self.redis.get(key)
                        if value:
                            # Extract agent type and query hash from key
                            key_parts = key.replace(self.QUERY_PREFIX, "").split(":")
                            if len(key_parts) >= 2:
                                agent_type = key_parts[0]
                                query_hash = key_parts[1]
                                
                                backup_data["queries"][key] = {
                                    "agent_type": agent_type,
                                    "response": value.get("response", ""),
                                    "cached_at": value.get("cached_at", time.time()),
                                    "hit_count": value.get("hit_count", 0),
                                    "query_hash": query_hash
                                }
                                backup_data["total_entries"] += 1
                    except Exception as e:
                        logger.warning(f"Could not backup cache entry {key}: {e}")
            
            # Save to file
            backup_file = self._get_cache_backup_path()
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Cache backup saved: {backup_data['total_entries']} entries to {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error backing up cache: {e}")
            return False
    
    def restore_cache_from_file(self) -> bool:
        """Restore cache entries from backup file"""
        try:
            backup_file = self._get_cache_backup_path()
            if not os.path.exists(backup_file):
                logger.info("No cache backup file found")
                return False
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Check if backup is not too old (7 days)
            backup_timestamp = backup_data.get("timestamp", 0)
            if time.time() - backup_timestamp > 7 * 24 * 3600:
                logger.info("Cache backup too old, skipping restore")
                return False
            
            restored_count = 0
            queries = backup_data.get("queries", {})
            
            for cache_key, entry_data in queries.items():
                try:
                    # Restore with shorter TTL since it's from backup
                    backup_ttl = min(self.default_ttl // 2, 1800)  # Max 30 minutes
                    
                    cache_value = {
                        "response": entry_data.get("response", ""),
                        "cached_at": time.time(),  # Update timestamp
                        "hit_count": entry_data.get("hit_count", 0),
                        "restored_from_backup": True
                    }
                    
                    if self.redis.set(cache_key, cache_value, ttl=backup_ttl):
                        restored_count += 1
                except Exception as e:
                    logger.warning(f"Could not restore cache entry {cache_key}: {e}")
            
            logger.info(f"Restored {restored_count} cache entries from backup")
            return restored_count > 0
            
        except Exception as e:
            logger.error(f"Error restoring cache from backup: {e}")
            return False