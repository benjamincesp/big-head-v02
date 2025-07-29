"""
WebSocket Handler for Real-time Chat with Memory
Integrates with ChatMemoryManager for persistent conversation history
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Set
from fastapi import WebSocket, WebSocketDisconnect
from cache.redis_manager import RedisManager
from cache.chat_memory_manager import ChatMemoryManager

logger = logging.getLogger(__name__)

class ChatWebSocketManager:
    def __init__(self, redis_manager: RedisManager, orchestrator, supervisor):
        """
        Initialize WebSocket manager with chat memory and intelligent supervisor
        
        Args:
            redis_manager: Redis connection manager
            orchestrator: Main orchestrator
            supervisor: Intelligent supervisor for routing
        """
        self.redis_manager = redis_manager
        self.chat_memory = ChatMemoryManager(redis_manager)
        self.orchestrator = orchestrator
        self.supervisor = supervisor
        
        # Active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_sessions: Dict[WebSocket, str] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str = None, user_id: str = None, agent_type: str = "auto"):
        """
        Accept WebSocket connection and create/resume chat session
        
        Args:
            websocket: WebSocket connection
            session_id: Optional existing session ID to resume
            user_id: Optional user identifier
            agent_type: Type of agent (auto for intelligent routing, or specific agent)
        """
        await websocket.accept()
        
        try:
            # Create new session or resume existing one
            if session_id and self.chat_memory.get_session_info(session_id):
                # Resume existing session
                current_session_id = session_id
                logger.info(f"Resuming chat session: {session_id}")
                
                # Send chat history
                await self._send_chat_history(websocket, session_id)
            else:
                # Create new session
                current_session_id = self.chat_memory.create_session(user_id, agent_type)
                if not current_session_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to create chat session"
                    })
                    await websocket.close()
                    return
                
                logger.info(f"Created new chat session: {current_session_id}")
            
            # Store connection mapping
            self.active_connections[current_session_id] = websocket
            self.connection_sessions[websocket] = current_session_id
            
            # Store connection metadata
            self.connection_metadata[current_session_id] = {
                "user_id": user_id or "anonymous",
                "agent_type": agent_type,
                "connected_at": time.time(),
                "last_activity": time.time()
            }
            
            # Send connection success message
            await websocket.send_json({
                "type": "connection_established",
                "session_id": current_session_id,
                "agent_type": agent_type,
                "message": "Chat session established successfully"
            })
            
        except Exception as e:
            logger.error(f"Error establishing WebSocket connection: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Connection failed"
            })
            await websocket.close()
    
    async def disconnect(self, websocket: WebSocket):
        """
        Handle WebSocket disconnection
        
        Args:
            websocket: WebSocket connection to disconnect
        """
        try:
            session_id = self.connection_sessions.get(websocket)
            
            if session_id:
                # Update last activity and remove from active connections
                if session_id in self.connection_metadata:
                    self.connection_metadata[session_id]["disconnected_at"] = time.time()
                
                # Remove from active connections
                self.active_connections.pop(session_id, None)
                self.connection_sessions.pop(websocket, None)
                
                logger.info(f"WebSocket disconnected for session: {session_id}")
                
                # Optionally close the session (or keep it for potential reconnection)
                # self.chat_memory.close_session(session_id)
            
        except Exception as e:
            logger.error(f"Error handling WebSocket disconnection: {str(e)}")
    
    async def handle_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Handle incoming WebSocket message
        
        Args:
            websocket: WebSocket connection
            message: Parsed JSON message
        """
        try:
            session_id = self.connection_sessions.get(websocket)
            if not session_id:
                await websocket.send_json({
                    "type": "error",
                    "message": "No active session"
                })
                return
            
            message_type = message.get("type", "")
            
            if message_type == "chat_message":
                await self._handle_chat_message(websocket, session_id, message)
            elif message_type == "get_history":
                await self._send_chat_history(websocket, session_id)
            elif message_type == "clear_history":
                await self._clear_chat_history(websocket, session_id)
            elif message_type == "session_info":
                await self._send_session_info(websocket, session_id)
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Message processing failed"
            })
    
    async def _handle_chat_message(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """
        Handle chat message from user
        
        Args:
            websocket: WebSocket connection
            session_id: Chat session ID
            message: Message data
        """
        try:
            user_message = message.get("content", "").strip()
            if not user_message:
                await websocket.send_json({
                    "type": "error",
                    "message": "Empty message"
                })
                return
            
            # Add user message to chat history
            self.chat_memory.add_message(
                session_id=session_id,
                role="user",
                content=user_message,
                metadata={"source": "websocket", "timestamp": time.time()}
            )
            
            # Send acknowledgment that user message was received
            await websocket.send_json({
                "type": "message_received",
                "message": "Processing your message..."
            })
            
            # Get conversation history for context
            conversation_history = self.chat_memory.get_openai_format_messages(session_id, limit=20)
            
            # Always use intelligent supervisor to analyze and route the message
            try:
                # Send initial typing indicator
                typing_data = {
                    "type": "typing",
                    "message": "🧠 Analyzing your question and selecting the best agent...",
                    "is_typing": True
                }
                logger.info(f"Sending typing indicator: {typing_data}")
                await websocket.send_json(typing_data)
                
                # Process with intelligent supervisor (automatic agent selection)
                agent_response = await self._process_with_intelligent_supervisor(
                    websocket,
                    user_message, 
                    conversation_history
                )
                
                if agent_response:
                    # Send "finishing up" typing indicator
                    await websocket.send_json({
                        "type": "typing",
                        "message": "📝 Finalizing response...",
                        "is_typing": True
                    })
                    
                    # Add assistant response to chat history
                    self.chat_memory.add_message(
                        session_id=session_id,
                        role="assistant",
                        content=agent_response["response"],
                        metadata={
                            "agent_type": agent_response.get("agent_used", "general"),
                            "processing_time": agent_response.get("processing_time", 0),
                            "confidence": agent_response.get("routing_confidence", 0),
                            "sources": agent_response.get("sources", []),
                            "routing_explanation": agent_response.get("routing_explanation", "")
                        }
                    )
                    
                    # Stop typing indicator before sending response
                    await websocket.send_json({
                        "type": "typing",
                        "message": "",
                        "is_typing": False
                    })
                    
                    # Send response to user
                    await websocket.send_json({
                        "type": "chat_response",
                        "content": agent_response["response"],
                        "metadata": {
                            "agent_type": agent_response.get("agent_used", "general"),
                            "processing_time": agent_response.get("processing_time", 0),
                            "confidence": agent_response.get("routing_confidence", 0),
                            "sources": agent_response.get("sources", []),
                            "routing_explanation": agent_response.get("routing_explanation", ""),
                            "timestamp": time.time()
                        }
                    })
                else:
                    # Stop typing indicator on error
                    await websocket.send_json({
                        "type": "typing",
                        "message": "",
                        "is_typing": False
                    })
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to process your message"
                    })
                    
            except Exception as e:
                logger.error(f"Error processing message with agent: {str(e)}")
                # Stop typing indicator on error
                await websocket.send_json({
                    "type": "typing",
                    "message": "",
                    "is_typing": False
                })
                await websocket.send_json({
                    "type": "error",
                    "message": "Error processing your message"
                })
                
        except Exception as e:
            logger.error(f"Error handling chat message: {str(e)}")
            await websocket.send_json({
                "type": "error",
                "message": "Message handling failed"
            })
    
    async def _process_with_intelligent_supervisor(self, websocket: WebSocket, message: str, conversation_history: list) -> Dict[str, Any]:
        """
        Process message with intelligent supervisor for automatic agent selection
        
        Args:
            websocket: WebSocket connection for sending typing updates
            message: User message
            conversation_history: Previous conversation messages
            
        Returns:
            Agent response with routing metadata
        """
        try:
            start_time = time.time()
            
            # Step 1: Use intelligent supervisor to route the query
            await websocket.send_json({
                "type": "typing",
                "message": "🎯 Selecting best agent for your question...",
                "is_typing": True
            })
            
            routing_decision = await asyncio.to_thread(
                self.supervisor.route_query,
                message
            )
            selected_agent = routing_decision.selected_agent.value
            
            logger.info(f"WebSocket smart routing selected: {selected_agent} (confidence: {routing_decision.confidence:.2f})")
            
            # Step 2: Send agent-specific typing indicator
            agent_names = {
                "general": "🤖 General Assistant",
                "exhibitors": "🏢 Exhibitors Specialist", 
                "visitors": "👥 Visitors Specialist"
            }
            agent_display = agent_names.get(selected_agent, selected_agent)
            
            await websocket.send_json({
                "type": "typing",
                "message": f"✨ {agent_display} is preparing your response...",
                "is_typing": True,
                "agent_selected": selected_agent
            })
            
            # Step 3: Process query with selected agent and conversation history
            result = await asyncio.to_thread(
                self.orchestrator.process_query,
                message,
                selected_agent,
                True,  # use_cache
                conversation_history
            )
            
            processing_time = time.time() - start_time
            
            # Step 3: Get routing explanation
            routing_explanation = self.supervisor.get_routing_explanation(routing_decision)
            
            return {
                "response": result.get("response", "I couldn't process your request."),
                "processing_time": processing_time,
                "agent_used": selected_agent,
                "routing_confidence": routing_decision.confidence,
                "routing_explanation": routing_explanation,
                "sources": result.get("sources", []),
                "success": result.get("success", True)
            }
            
        except Exception as e:
            logger.error(f"Error processing with agent: {str(e)}")
            return None
    
    async def _send_chat_history(self, websocket: WebSocket, session_id: str):
        """Send chat history to client"""
        try:
            messages = self.chat_memory.get_messages(session_id)
            await websocket.send_json({
                "type": "chat_history",
                "messages": messages,
                "session_id": session_id
            })
        except Exception as e:
            logger.error(f"Error sending chat history: {str(e)}")
    
    async def _clear_chat_history(self, websocket: WebSocket, session_id: str):
        """Clear chat history for session"""
        try:
            # Delete chat messages but keep session metadata
            chat_key = self.chat_memory._get_chat_key(session_id)
            self.chat_memory.redis.set(chat_key, [], ex=self.chat_memory.default_ttl)
            
            await websocket.send_json({
                "type": "history_cleared",
                "message": "Chat history cleared",
                "session_id": session_id
            })
        except Exception as e:
            logger.error(f"Error clearing chat history: {str(e)}")
    
    async def _send_session_info(self, websocket: WebSocket, session_id: str):
        """Send session information to client"""
        try:
            session_info = self.chat_memory.get_session_info(session_id)
            connection_info = self.connection_metadata.get(session_id, {})
            
            await websocket.send_json({
                "type": "session_info",
                "session_data": session_info,
                "connection_data": connection_info
            })
        except Exception as e:
            logger.error(f"Error sending session info: {str(e)}")
    
    def get_active_sessions_count(self) -> int:
        """Get number of active WebSocket connections"""
        return len(self.active_connections)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        return {
            "active_websocket_connections": len(self.active_connections),
            "total_connection_metadata": len(self.connection_metadata),
            "chat_memory_stats": self.chat_memory.get_chat_stats()
        }