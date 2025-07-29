"""
Configuration Management for Food Service 2025
Handles environment variables with validation and defaults
"""

import os
import logging
from typing import Any, Dict, Optional
from exceptions import FSError

logger = logging.getLogger(__name__)

class ConfigError(FSError):
    """Configuration related errors"""
    pass

class Config:
    """Configuration manager with validation"""
    
    def __init__(self):
        self._load_config()
        self._validate_config()
    
    def _load_config(self):
        """Load configuration from environment variables"""
        # OpenAI Configuration
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.OPENAI_TIMEOUT = float(os.getenv('OPENAI_TIMEOUT', 30))
        self.OPENAI_MAX_RETRIES = int(os.getenv('OPENAI_MAX_RETRIES', 3))
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Redis Configuration
        # Handle Heroku Redis addon (REDIS_URL) or individual config vars
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            # Parse Heroku Redis URL: redis://h:password@host:port
            import urllib.parse
            parsed = urllib.parse.urlparse(redis_url)
            self.REDIS_HOST = parsed.hostname
            self.REDIS_PORT = parsed.port or 6379
            self.REDIS_PASSWORD = parsed.password
            self.REDIS_DB = 0  # Heroku Redis uses DB 0
        else:
            # Use individual environment variables (for local development)
            self.REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
            self.REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
            self.REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
            self.REDIS_DB = int(os.getenv('REDIS_DB', 0))
        
        self.REDIS_SOCKET_TIMEOUT = int(os.getenv('REDIS_SOCKET_TIMEOUT', 10))
        self.REDIS_CONNECT_TIMEOUT = int(os.getenv('REDIS_CONNECT_TIMEOUT', 5))
        
        # API Configuration
        self.HOST = os.getenv('HOST', '0.0.0.0')
        self.PORT = int(os.getenv('PORT', 8000))
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
        
        # Cache Configuration
        self.CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))
        self.CACHE_SIMILARITY_THRESHOLD = float(os.getenv('CACHE_SIMILARITY_THRESHOLD', 0.8))
        
        # Query Configuration
        self.MAX_QUERY_LENGTH = int(os.getenv('MAX_QUERY_LENGTH', 1000))
        self.MAX_RESPONSE_TOKENS = int(os.getenv('MAX_RESPONSE_TOKENS', 500))
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # Vector Store Configuration
        self.DISABLE_VECTOR_STORE = os.getenv('DISABLE_VECTOR_STORE', 'false').lower() == 'true'
        
        # Security Configuration
        self.ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
        self.CORS_ALLOW_CREDENTIALS = os.getenv('CORS_ALLOW_CREDENTIALS', 'true').lower() == 'true'
        
        # Rate Limiting
        self.RATE_LIMIT = os.getenv('RATE_LIMIT', '30/minute')
        
    def _validate_config(self):
        """Validate critical configuration"""
        errors = []
        
        # Validate required fields
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is required")
        
        # Validate OpenAI config
        if self.OPENAI_TIMEOUT <= 0:
            errors.append("OPENAI_TIMEOUT must be positive")
        
        if self.OPENAI_MAX_RETRIES < 0:
            errors.append("OPENAI_MAX_RETRIES must be non-negative")
        
        # Validate Redis config
        if not (1 <= self.REDIS_PORT <= 65535):
            errors.append("REDIS_PORT must be between 1 and 65535")
        
        if self.REDIS_SOCKET_TIMEOUT <= 0:
            errors.append("REDIS_SOCKET_TIMEOUT must be positive")
        
        # Validate API config
        if not (1 <= self.PORT <= 65535):
            errors.append("PORT must be between 1 and 65535")
        
        # Validate cache config
        if self.CACHE_TTL <= 0:
            errors.append("CACHE_TTL must be positive")
        
        if not (0 <= self.CACHE_SIMILARITY_THRESHOLD <= 1):
            errors.append("CACHE_SIMILARITY_THRESHOLD must be between 0 and 1")
        
        # Validate query config
        if self.MAX_QUERY_LENGTH <= 0:
            errors.append("MAX_QUERY_LENGTH must be positive")
        
        if self.MAX_RESPONSE_TOKENS <= 0:
            errors.append("MAX_RESPONSE_TOKENS must be positive")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.LOG_LEVEL not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")
        
        if errors:
            raise ConfigError(f"Configuration validation failed: {'; '.join(errors)}")
        
        logger.info("Configuration validation passed")
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration dictionary"""
        return {
            'host': self.REDIS_HOST,
            'port': self.REDIS_PORT,
            'password': self.REDIS_PASSWORD,
            'db': self.REDIS_DB,
            'socket_timeout': self.REDIS_SOCKET_TIMEOUT,
            'socket_connect_timeout': self.REDIS_CONNECT_TIMEOUT
        }
    
    def get_openai_config(self) -> Dict[str, Any]:
        """Get OpenAI configuration dictionary"""
        return {
            'api_key': self.OPENAI_API_KEY,
            'timeout': self.OPENAI_TIMEOUT,
            'max_retries': self.OPENAI_MAX_RETRIES,
            'model': self.OPENAI_MODEL
        }
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration dictionary"""
        return {
            'host': self.HOST,
            'port': self.PORT,
            'environment': self.ENVIRONMENT,
            'allowed_origins': self.ALLOWED_ORIGINS,
            'cors_allow_credentials': self.CORS_ALLOW_CREDENTIALS,
            'rate_limit': self.RATE_LIMIT
        }
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() == 'development'
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() == 'production'
    
    def to_dict(self) -> Dict[str, Any]:
        """Get all configuration as dictionary (without sensitive data)"""
        return {
            # OpenAI (without API key)
            'openai_timeout': self.OPENAI_TIMEOUT,
            'openai_max_retries': self.OPENAI_MAX_RETRIES,
            'openai_model': self.OPENAI_MODEL,
            
            # Redis (without password)
            'redis_host': self.REDIS_HOST,
            'redis_port': self.REDIS_PORT,
            'redis_db': self.REDIS_DB,
            'redis_socket_timeout': self.REDIS_SOCKET_TIMEOUT,
            'redis_connect_timeout': self.REDIS_CONNECT_TIMEOUT,
            
            # API
            'host': self.HOST,
            'port': self.PORT,
            'environment': self.ENVIRONMENT,
            'allowed_origins': self.ALLOWED_ORIGINS,
            'rate_limit': self.RATE_LIMIT,
            
            # Cache
            'cache_ttl': self.CACHE_TTL,
            'cache_similarity_threshold': self.CACHE_SIMILARITY_THRESHOLD,
            
            # Query
            'max_query_length': self.MAX_QUERY_LENGTH,
            'max_response_tokens': self.MAX_RESPONSE_TOKENS,
            
            # Other
            'log_level': self.LOG_LEVEL,
            'disable_vector_store': self.DISABLE_VECTOR_STORE
        }

# Global configuration instance
config = Config()