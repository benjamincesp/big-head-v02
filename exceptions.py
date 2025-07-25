"""
Custom Exceptions for Food Service 2025 Multi-Agent System
Provides structured error handling for better debugging and user experience
"""

class FSError(Exception):
    """Base exception for Food Service system"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code or "FS_GENERIC_ERROR"
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }

class OpenAIError(FSError):
    """OpenAI API related errors"""
    pass

class OpenAIRateLimitError(OpenAIError):
    """OpenAI API rate limit exceeded"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(
            message, 
            "OPENAI_RATE_LIMIT", 
            {"retry_after": retry_after}
        )

class OpenAITimeoutError(OpenAIError):
    """OpenAI API timeout error"""
    def __init__(self, message: str = "Request timeout"):
        super().__init__(message, "OPENAI_TIMEOUT")

class OpenAIAuthError(OpenAIError):
    """OpenAI API authentication error"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "OPENAI_AUTH_ERROR")

class CacheError(FSError):
    """Cache-related errors"""
    pass

class RedisConnectionError(CacheError):
    """Redis connection error"""
    def __init__(self, message: str = "Redis connection failed"):
        super().__init__(message, "REDIS_CONNECTION_ERROR")

class CacheOperationError(CacheError):
    """Cache operation error"""
    def __init__(self, operation: str, message: str = None):
        message = message or f"Cache {operation} operation failed"
        super().__init__(message, "CACHE_OPERATION_ERROR", {"operation": operation})

class DocumentError(FSError):
    """Document processing errors"""
    pass

class DocumentNotFoundError(DocumentError):
    """Document file not found"""
    def __init__(self, file_path: str):
        super().__init__(
            f"Document not found: {file_path}", 
            "DOCUMENT_NOT_FOUND",
            {"file_path": file_path}
        )

class DocumentProcessingError(DocumentError):
    """Document processing failed"""
    def __init__(self, file_path: str, error: str):
        super().__init__(
            f"Failed to process document {file_path}: {error}",
            "DOCUMENT_PROCESSING_ERROR",
            {"file_path": file_path, "processing_error": error}
        )

class VectorStoreError(FSError):
    """Vector store operations errors"""
    pass

class AgentError(FSError):
    """Agent processing errors"""
    pass

class AgentNotFoundError(AgentError):
    """Requested agent type not found"""
    def __init__(self, agent_type: str):
        super().__init__(
            f"Agent not found: {agent_type}",
            "AGENT_NOT_FOUND",
            {"agent_type": agent_type}
        )

class QueryValidationError(FSError):
    """Query validation error"""
    def __init__(self, message: str, query: str = None):
        super().__init__(
            message,
            "QUERY_VALIDATION_ERROR",
            {"query": query[:100] if query else None}
        )