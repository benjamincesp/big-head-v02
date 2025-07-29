"""
Chat Memory Manager for Food Service 2025
Manages conversation history per session/chat ID using Redis
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List
from .redis_manager import RedisManager

logger = logging.getLogger(__name__)

class ChatMemoryManager:
    def __init__(self, redis_manager: RedisManager, default_ttl: int = 86400):  # 24h default
        """
        Initialize chat memory manager
        
        Args:
            redis_manager: Redis connection manager
            default_ttl: Default TTL for chat sessions in seconds (24h)
        """
        self.redis = redis_manager
        self.default_ttl = default_ttl
        self.max_messages_per_session = 50  # Limit to prevent memory issues
        
        # Cache prefixes
        self.CHAT_PREFIX = "fs2024:chat:"
        self.SESSION_PREFIX = "fs2024:session:"
        self.ACTIVE_SESSIONS_PREFIX = "fs2024:active_sessions"
    
    def generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"session_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    def _get_chat_key(self, session_id: str) -> str:
        """Generate Redis key for chat messages"""
        return f"{self.CHAT_PREFIX}{session_id}"
    
    def _get_session_key(self, session_id: str) -> str:
        """Generate Redis key for session metadata"""
        return f"{self.SESSION_PREFIX}{session_id}"
    
    def create_session(self, user_id: str = None, agent_type: str = "general") -> str:
        """
        Create new chat session
        
        Args:
            user_id: Optional user identifier
            agent_type: Type of agent (general, exhibitors, visitors)
            
        Returns:
            session_id: Unique session identifier
        """
        if not self.redis.is_connected():
            logger.error("Redis not connected, cannot create session")
            return None
        
        session_id = self.generate_session_id()
        
        try:
            # Create session metadata
            session_data = {
                "session_id": session_id,
                "user_id": user_id or "anonymous",
                "agent_type": agent_type,
                "created_at": time.time(),
                "last_activity": time.time(),
                "message_count": 0,
                "active": True
            }
            
            session_key = self._get_session_key(session_id)
            chat_key = self._get_chat_key(session_id)
            
            # Store session metadata and initialize empty messages array
            success_session = self.redis.set(session_key, session_data, ex=self.default_ttl)
            success_chat = self.redis.set(chat_key, [], ex=self.default_ttl)
            
            if success_session and success_chat:
                # Add to active sessions list
                self.redis.redis_client.sadd(self.ACTIVE_SESSIONS_PREFIX, session_id)
                self.redis.redis_client.expire(self.ACTIVE_SESSIONS_PREFIX, self.default_ttl)
                
                logger.info(f"Created chat session: {session_id} for user: {user_id or 'anonymous'}")
                return session_id
            else:
                logger.error(f"Failed to create session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            return None
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Add message to chat session
        
        Args:
            session_id: Session identifier
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata (agent_type, timestamp, etc.)
            
        Returns:
            bool: Success status
        """
        if not self.redis.is_connected():
            logger.error("Redis not connected, cannot add message")
            return False
        
        try:
            chat_key = self._get_chat_key(session_id)
            session_key = self._get_session_key(session_id)
            
            # Check if session exists
            session_data = self.redis.get(session_key)
            if not session_data:
                logger.warning(f"Session {session_id} not found, cannot add message")
                return False
            
            # Get current messages
            messages = self.redis.get(chat_key) or []
            
            # Create message object
            message = {
                "role": role,
                "content": content,
                "timestamp": time.time(),
                "message_id": str(uuid.uuid4())[:8],
                "metadata": metadata or {}
            }
            
            # Add message to list
            messages.append(message)
            
            # Limit messages per session to prevent memory issues
            if len(messages) > self.max_messages_per_session:
                messages = messages[-self.max_messages_per_session:]
                logger.info(f"Trimmed messages for session {session_id} to {self.max_messages_per_session}")
            
            # Update messages and session metadata
            success_chat = self.redis.set(chat_key, messages, ex=self.default_ttl)
            
            # Update session metadata
            session_data["last_activity"] = time.time()
            session_data["message_count"] = len(messages)
            success_session = self.redis.set(session_key, session_data, ex=self.default_ttl)
            
            if success_chat and success_session:
                logger.debug(f"Added {role} message to session {session_id}")
                return True
            else:
                logger.error(f"Failed to update session {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {str(e)}")
            return False
    
    def get_messages(self, session_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get messages from chat session
        
        Args:
            session_id: Session identifier
            limit: Optional limit on number of messages to return
            
        Returns:
            List of messages
        """
        if not self.redis.is_connected():
            logger.error("Redis not connected, cannot get messages")
            return []
        
        try:
            chat_key = self._get_chat_key(session_id)
            messages = self.redis.get(chat_key) or []
            
            if limit and len(messages) > limit:
                messages = messages[-limit:]
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {str(e)}")
            return []
    
    def get_openai_format_messages(self, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get messages in OpenAI API format
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages to include
            
        Returns:
            List of messages in OpenAI format
        """
        messages = self.get_messages(session_id, limit)
        
        # Convert to OpenAI format
        openai_messages = []
        for msg in messages:
            openai_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return openai_messages
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        if not self.redis.is_connected():
            return None
        
        try:
            session_key = self._get_session_key(session_id)
            return self.redis.get(session_key)
        except Exception as e:
            logger.error(f"Error getting session info for {session_id}: {str(e)}")
            return None
    
    def close_session(self, session_id: str) -> bool:
        """
        Close/deactivate chat session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: Success status
        """
        if not self.redis.is_connected():
            return False
        
        try:
            session_key = self._get_session_key(session_id)
            session_data = self.redis.get(session_key)
            
            if session_data:
                session_data["active"] = False
                session_data["closed_at"] = time.time()
                
                # Update session and remove from active sessions
                success = self.redis.set(session_key, session_data, ex=self.default_ttl)
                self.redis.redis_client.srem(self.ACTIVE_SESSIONS_PREFIX, session_id)
                
                logger.info(f"Closed session: {session_id}")
                return success
            
            return False
            
        except Exception as e:
            logger.error(f"Error closing session {session_id}: {str(e)}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions
        
        Returns:
            int: Number of sessions cleaned up
        """
        if not self.redis.is_connected():
            return 0
        
        try:
            cleaned_count = 0
            current_time = time.time()
            
            # Get all session keys
            pattern = f"{self.SESSION_PREFIX}*"
            session_keys = self.redis.get_keys_pattern(pattern)
            
            for session_key in session_keys:
                session_data = self.redis.get(session_key)
                if session_data:
                    last_activity = session_data.get("last_activity", 0)
                    
                    # If session is older than TTL, clean it up
                    if current_time - last_activity > self.default_ttl:
                        session_id = session_data.get("session_id", "")
                        chat_key = self._get_chat_key(session_id)
                        
                        # Delete session and chat data
                        self.redis.delete(session_key)
                        self.redis.delete(chat_key)
                        self.redis.redis_client.srem(self.ACTIVE_SESSIONS_PREFIX, session_id)
                        
                        cleaned_count += 1
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} expired sessions")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {str(e)}")
            return 0
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs"""
        if not self.redis.is_connected():
            return []
        
        try:
            return list(self.redis.redis_client.smembers(self.ACTIVE_SESSIONS_PREFIX))
        except Exception as e:
            logger.error(f"Error getting active sessions: {str(e)}")
            return []
    
    def get_chat_stats(self) -> Dict[str, Any]:
        """Get comprehensive chat statistics"""
        if not self.redis.is_connected():
            return {"connected": False}
        
        try:
            active_sessions = self.get_active_sessions()
            total_sessions = len(self.redis.get_keys_pattern(f"{self.SESSION_PREFIX}*"))
            total_chats = len(self.redis.get_keys_pattern(f"{self.CHAT_PREFIX}*"))
            
            # Get message count statistics
            total_messages = 0
            agent_type_stats = {}
            
            for session_id in active_sessions:
                session_info = self.get_session_info(session_id)
                if session_info:
                    agent_type = session_info.get("agent_type", "general")
                    message_count = session_info.get("message_count", 0)
                    
                    total_messages += message_count
                    
                    if agent_type not in agent_type_stats:
                        agent_type_stats[agent_type] = {"sessions": 0, "messages": 0}
                    
                    agent_type_stats[agent_type]["sessions"] += 1
                    agent_type_stats[agent_type]["messages"] += message_count
            
            return {
                "connected": True,
                "active_sessions": len(active_sessions),
                "total_sessions": total_sessions,
                "total_chats": total_chats,
                "total_messages": total_messages,
                "agent_type_stats": agent_type_stats,
                "max_messages_per_session": self.max_messages_per_session,
                "default_ttl_hours": self.default_ttl / 3600
            }
            
        except Exception as e:
            logger.error(f"Error getting chat stats: {str(e)}")
            return {"connected": False, "error": str(e)}