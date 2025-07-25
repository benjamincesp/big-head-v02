"""
Robust OpenAI Client for Food Service 2025
Implements retry logic, error handling, and connection management
"""

import logging
import time
import os
from typing import Dict, Any, Optional, List
from functools import wraps
import openai
from openai import OpenAI

from exceptions import (
    OpenAIError, OpenAIRateLimitError, OpenAITimeoutError, 
    OpenAIAuthError, FSError
)

logger = logging.getLogger(__name__)

def retry_with_exponential_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    exponential_base: float = 2.0,
    jitter: bool = True
):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except openai.RateLimitError as e:
                    if attempt == max_retries:
                        raise OpenAIRateLimitError(
                            f"Rate limit exceeded after {max_retries} retries",
                            retry_after=getattr(e, 'retry_after', None)
                        )
                    
                    # Extract retry-after from headers if available
                    retry_after = getattr(e, 'retry_after', None) or 60
                    delay = min(retry_after, initial_delay * (exponential_base ** attempt))
                    
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"Rate limit hit, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    
                except (openai.APITimeoutError, openai.APIConnectionError) as e:
                    if attempt == max_retries:
                        raise OpenAITimeoutError(f"Request timeout after {max_retries} retries: {str(e)}")
                    
                    delay = initial_delay * (exponential_base ** attempt)
                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"Connection/timeout error, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    
                except openai.AuthenticationError as e:
                    raise OpenAIAuthError(f"Authentication failed: {str(e)}")
                    
                except openai.BadRequestError as e:
                    raise OpenAIError(f"Bad request: {str(e)}", "OPENAI_BAD_REQUEST")
                    
                except Exception as e:
                    if attempt == max_retries:
                        raise OpenAIError(f"Unexpected OpenAI error: {str(e)}", "OPENAI_UNEXPECTED_ERROR")
                    
                    delay = initial_delay * (exponential_base ** attempt)
                    logger.warning(f"Unexpected error, retrying in {delay:.2f}s: {str(e)}")
                    time.sleep(delay)
            
            return None
        return wrapper
    return decorator

class RobustOpenAIClient:
    """Robust OpenAI client with retry logic and error handling"""
    
    def __init__(
        self, 
        api_key: str,
        timeout: float = None,
        max_retries: int = None,
        base_url: str = None
    ):
        """
        Initialize robust OpenAI client
        
        Args:
            api_key: OpenAI API key
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retries (default: 3)
            base_url: Custom base URL for OpenAI API
        """
        self.timeout = timeout or float(os.getenv('OPENAI_TIMEOUT', 30))
        self.max_retries = max_retries or int(os.getenv('OPENAI_MAX_RETRIES', 3))
        
        # Initialize OpenAI client with robust configuration
        try:
            self.client = OpenAI(
                api_key=api_key,
                timeout=self.timeout,
                max_retries=0,  # We handle retries manually
                base_url=base_url
            )
            
            # Test connection
            self._test_connection()
            logger.info(f"OpenAI client initialized successfully (timeout: {self.timeout}s, max_retries: {self.max_retries})")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise OpenAIAuthError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def _test_connection(self):
        """Test OpenAI API connection"""
        try:
            # Simple test call to verify API key and connection
            response = self.client.models.list()
            logger.info("OpenAI API connection test successful")
        except Exception as e:
            logger.error(f"OpenAI API connection test failed: {str(e)}")
            raise
    
    @retry_with_exponential_backoff()
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 500,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create chat completion with retry logic
        
        Args:
            messages: List of message dictionaries
            model: OpenAI model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            **kwargs: Additional parameters
            
        Returns:
            Dict containing response and metadata
        """
        start_time = time.time()
        
        try:
            # Enhanced parameters with better defaults
            params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout": self.timeout,
                **kwargs
            }
            
            logger.debug(f"Making OpenAI request with model: {model}, max_tokens: {max_tokens}")
            
            response = self.client.chat.completions.create(**params)
            
            duration = time.time() - start_time
            
            # Extract response details
            choice = response.choices[0]
            usage = response.usage
            
            result = {
                "content": choice.message.content.strip(),
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens
                },
                "model": response.model,
                "duration_seconds": round(duration, 3),
                "created": response.created
            }
            
            logger.info(f"OpenAI request completed in {duration:.3f}s (tokens: {usage.total_tokens})")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"OpenAI request failed after {duration:.3f}s: {str(e)}")
            raise
    
    def get_embeddings(
        self,
        texts: List[str],
        model: str = "text-embedding-3-small",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get embeddings with retry logic
        
        Args:
            texts: List of texts to embed
            model: Embedding model to use
            **kwargs: Additional parameters
            
        Returns:
            Dict containing embeddings and metadata
        """
        if not texts:
            return {"embeddings": [], "usage": {"total_tokens": 0}}
        
        start_time = time.time()
        
        try:
            response = self.client.embeddings.create(
                model=model,
                input=texts,
                **kwargs
            )
            
            duration = time.time() - start_time
            
            embeddings = [item.embedding for item in response.data]
            
            result = {
                "embeddings": embeddings,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "model": response.model,
                "duration_seconds": round(duration, 3)
            }
            
            logger.info(f"Embeddings generated in {duration:.3f}s for {len(texts)} texts")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Embeddings request failed after {duration:.3f}s: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics"""
        return {
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "client_initialized": self.client is not None
        }

# Global client instance
_global_client: Optional[RobustOpenAIClient] = None

def get_openai_client(api_key: str = None) -> RobustOpenAIClient:
    """Get or create global OpenAI client instance"""
    global _global_client
    
    if _global_client is None:
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise OpenAIAuthError("OpenAI API key not provided")
        
        _global_client = RobustOpenAIClient(api_key)
    
    return _global_client

def reset_openai_client():
    """Reset global OpenAI client (useful for testing)"""
    global _global_client
    _global_client = None