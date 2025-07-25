"""
Redis Manager for Food Service 2025 Cache System
Handles Redis connections and basic operations
"""

import redis
import json
import logging
import time
from typing import Any, Optional, Dict
import os

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self, 
                 host: str = None, 
                 port: int = None, 
                 db: int = 0, 
                 password: str = None,
                 decode_responses: bool = True,
                 socket_timeout: int = None,
                 socket_connect_timeout: int = None,
                 retry_on_timeout: bool = True,
                 max_retries: int = 3):
        """Initialize Redis connection with enhanced configuration"""
        self.host = host or os.getenv('REDIS_HOST', 'localhost')
        self.port = port or int(os.getenv('REDIS_PORT', 6379))
        self.db = db
        self.password = password or os.getenv('REDIS_PASSWORD')
        self.socket_timeout = socket_timeout or int(os.getenv('REDIS_SOCKET_TIMEOUT', 10))
        self.socket_connect_timeout = socket_connect_timeout or int(os.getenv('REDIS_CONNECT_TIMEOUT', 5))
        self.retry_on_timeout = retry_on_timeout
        self.max_retries = max_retries
        
        self._connect_with_retry()
    
    def _connect_with_retry(self):
        """Connect to Redis with retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                self.redis_client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=self.socket_connect_timeout,
                    socket_timeout=self.socket_timeout,
                    retry_on_timeout=self.retry_on_timeout,
                    health_check_interval=30
                )
                
                # Test connection
                self.redis_client.ping()
                logger.info(f"Successfully connected to Redis at {self.host}:{self.port} (attempt {attempt + 1})")
                return
                
            except redis.ConnectionError as e:
                if attempt == self.max_retries:
                    logger.error(f"Failed to connect to Redis after {self.max_retries + 1} attempts: {str(e)}")
                    self.redis_client = None
                    return
                
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Redis connection attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error(f"Unexpected Redis connection error: {str(e)}")
                self.redis_client = None
                return
    
    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def set(self, key: str, value: Any, ex: int = None) -> bool:
        """Set a key-value pair with optional expiration"""
        if not self.is_connected():
            logger.warning("Redis not connected, cannot set value")
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            
            result = self.redis_client.set(key, value, ex=ex)
            return result
        except Exception as e:
            logger.error(f"Error setting Redis key {key}: {str(e)}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        if not self.is_connected():
            logger.warning("Redis not connected, cannot get value")
            return None
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to parse JSON
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Error getting Redis key {key}: {str(e)}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a key"""
        if not self.is_connected():
            return False
        
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Error deleting Redis key {key}: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.is_connected():
            return False
        
        try:
            return self.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking Redis key {key}: {str(e)}")
            return False
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a counter"""
        if not self.is_connected():
            return None
        
        try:
            return self.redis_client.incr(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing Redis key {key}: {str(e)}")
            return None
    
    def get_keys_pattern(self, pattern: str) -> list:
        """Get keys matching a pattern"""
        if not self.is_connected():
            return []
        
        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Error getting keys with pattern {pattern}: {str(e)}")
            return []
    
    def flush_db(self) -> bool:
        """Flush current database"""
        if not self.is_connected():
            return False
        
        try:
            self.redis_client.flushdb()
            logger.info("Redis database flushed")
            return True
        except Exception as e:
            logger.error(f"Error flushing Redis database: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        if not self.is_connected():
            return {"connected": False}
        
        try:
            info = self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "Unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"Error getting Redis stats: {str(e)}")
            return {"connected": False, "error": str(e)}