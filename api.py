"""
FastAPI REST API for Food Service 2025 Multi-Agent System
Provides REST endpoints for interacting with the multi-agent system
"""

import logging
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Path, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from orchestrator import FoodServiceOrchestrator
from websocket_handler import ChatWebSocketManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration and exceptions
from config import config
from exceptions import *
from intelligent_supervisor import IntelligentSupervisor

# Initialize FastAPI app
app = FastAPI(
    title="Food Service 2025 Multi-Agent API",
    description="Sistema multi-agente para consultas sobre Food Service 2025",
    version="1.0.0",
    docs_url="/docs" if config.is_development() else None,
    redoc_url="/redoc" if config.is_development() else None
)

# Configure CORS with security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins temporarily for development
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize orchestrator with configuration
print("🔧 DEBUG: Starting API initialization...")
try:
    print("✅ DEBUG: Configuration loaded and validated")
    
    redis_config = config.get_redis_config()
    print(f"🔧 DEBUG: Creating orchestrator with Redis config: {redis_config}")
    
    orchestrator = FoodServiceOrchestrator(config.OPENAI_API_KEY, redis_config)
    print("✅ DEBUG: Orchestrator created successfully!")
    
    # Initialize intelligent supervisor
    print("🧠 DEBUG: Creating intelligent supervisor...")
    supervisor = IntelligentSupervisor(config.OPENAI_API_KEY)
    print("✅ DEBUG: Intelligent supervisor created successfully!")
    
    # Initialize WebSocket chat manager
    print("💬 DEBUG: Creating WebSocket chat manager...")
    chat_manager = ChatWebSocketManager(orchestrator.redis_manager, orchestrator, supervisor)
    print("✅ DEBUG: WebSocket chat manager created successfully!")
    
except ConfigError as e:
    print(f"❌ DEBUG: Configuration error: {str(e)}")
    logger.error(f"Configuration error: {str(e)}")
    raise
except Exception as e:
    print(f"❌ DEBUG: Orchestrator initialization failed: {str(e)}")
    logger.error(f"Orchestrator initialization failed: {str(e)}")
    raise

# Pydantic models with validation
class QueryRequest(BaseModel):
    query: str = Field(
        ..., 
        description="Consulta del usuario", 
        min_length=1, 
        max_length=config.MAX_QUERY_LENGTH
    )
    agent_type: Optional[str] = Field(
        None, 
        description="Tipo de agente específico (opcional)",
        pattern="^(general|exhibitors|visitors)$"
    )
    use_cache: bool = Field(True, description="Usar cache para la consulta")

class QueryResponse(BaseModel):
    response: str

class SmartQueryRequest(BaseModel):
    query: str = Field(
        ..., 
        description="Consulta del usuario", 
        min_length=1, 
        max_length=config.MAX_QUERY_LENGTH
    )
    use_cache: bool = Field(True, description="Usar cache para la consulta")
    include_routing_info: bool = Field(False, description="Incluir información sobre la decisión de enrutamiento")

class SmartQueryResponse(BaseModel):
    response: str
    agent_used: str
    routing_confidence: float
    routing_explanation: Optional[str] = None

class ChatSessionRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="ID del usuario (opcional)")
    agent_type: str = Field("general", description="Tipo de agente", pattern="^(general|exhibitors|visitors)$")

class ChatSessionResponse(BaseModel):
    session_id: str
    user_id: str
    agent_type: str
    created_at: float

# API Endpoints

# WebSocket Chat Endpoint
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None, description="ID de sesión existente para reanudar"),
    user_id: Optional[str] = Query(None, description="ID del usuario"),
    agent_type: str = Query("general", description="Tipo de agente")
):
    """
    WebSocket endpoint para chat en tiempo real con memoria persistente
    
    - **session_id**: ID de sesión existente para reanudar conversación (opcional)
    - **user_id**: Identificador del usuario (opcional)
    - **agent_type**: Tipo de agente (general, exhibitors, visitors)
    """
    await chat_manager.connect(websocket, session_id, user_id, agent_type)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await chat_manager.handle_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        await chat_manager.disconnect(websocket)

# Chat Management REST Endpoints
@app.post("/chat/session", response_model=ChatSessionResponse)
async def create_chat_session(request: ChatSessionRequest):
    """
    Crear nueva sesión de chat
    
    - **user_id**: ID del usuario (opcional)
    - **agent_type**: Tipo de agente para la sesión
    """
    try:
        session_id = chat_manager.chat_memory.create_session(
            user_id=request.user_id,
            agent_type=request.agent_type
        )
        
        if not session_id:
            raise HTTPException(status_code=500, detail="Failed to create chat session")
        
        session_info = chat_manager.chat_memory.get_session_info(session_id)
        
        return ChatSessionResponse(
            session_id=session_id,
            user_id=session_info["user_id"],
            agent_type=session_info["agent_type"],
            created_at=session_info["created_at"]
        )
        
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@app.get("/chat/session/{session_id}")
async def get_chat_session(session_id: str = Path(..., description="ID de la sesión")):
    """
    Obtener información de sesión de chat
    """
    try:
        session_info = chat_manager.chat_memory.get_session_info(session_id)
        
        if not session_info:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return session_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving session: {str(e)}")

@app.get("/chat/session/{session_id}/messages")
async def get_chat_messages(
    session_id: str = Path(..., description="ID de la sesión"),
    limit: Optional[int] = Query(None, description="Límite de mensajes", ge=1, le=100)
):
    """
    Obtener mensajes de una sesión de chat
    """
    try:
        messages = chat_manager.chat_memory.get_messages(session_id, limit)
        return {"session_id": session_id, "messages": messages}
        
    except Exception as e:
        logger.error(f"Error getting chat messages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")

@app.delete("/chat/session/{session_id}")
async def close_chat_session(session_id: str = Path(..., description="ID de la sesión")):
    """
    Cerrar sesión de chat
    """
    try:
        success = chat_manager.chat_memory.close_session(session_id)
        
        if success:
            return {"message": "Chat session closed successfully", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Chat session not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing chat session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error closing session: {str(e)}")

@app.get("/chat/stats")
async def get_chat_stats():
    """
    Obtener estadísticas del sistema de chat
    """
    try:
        stats = chat_manager.get_session_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting chat stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")

@app.get("/food-service/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Food Service 2025 Multi-Agent API"
    }

@app.post("/food-service/admin/backup")
async def create_backup():
    """Create backup of cache and document state"""
    try:
        backup_results = {
            "timestamp": datetime.now().isoformat(),
            "cache_backup": False,
            "document_backups": {}
        }
        
        # Backup cache
        try:
            backup_results["cache_backup"] = orchestrator.query_cache.backup_cache_to_file()
        except Exception as e:
            logger.error(f"Cache backup failed: {e}")
        
        # Backup document states for each agent
        for agent_name, agent in orchestrator.agents.items():
            try:
                if hasattr(agent, 'document_search'):
                    agent.document_search._save_backup_state()
                    backup_results["document_backups"][agent_name] = True
                elif hasattr(agent, 'exhibitor_tool'):
                    agent.exhibitor_tool._save_backup_state()
                    backup_results["document_backups"][agent_name] = True
                elif hasattr(agent, 'visitor_tool'):
                    agent.visitor_tool._save_backup_state()
                    backup_results["document_backups"][agent_name] = True
                else:
                    backup_results["document_backups"][agent_name] = False
            except Exception as e:
                logger.error(f"Document backup failed for {agent_name}: {e}")
                backup_results["document_backups"][agent_name] = False
        
        return {
            "status": "success",
            "message": "Backup process completed",
            "results": backup_results
        }
        
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Procesar consulta usando el sistema multi-agente de Food Service 2025
    
    - **query**: La consulta del usuario sobre expositores, visitantes o información general
    - **agent_type**: Tipo de agente específico (opcional: general, exhibitors, visitors)
    - **use_cache**: Si usar cache para la consulta (por defecto: true)
    """
    try:
        logger.info(f"Processing query: {request.query[:100]}...")
        
        # Validate agent type if provided
        if request.agent_type and request.agent_type not in ['general', 'exhibitors', 'visitors']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent_type. Must be one of: general, exhibitors, visitors"
            )
        
        # Process query
        result = orchestrator.process_query(
            query=request.query,
            agent_type=request.agent_type,
            use_cache=request.use_cache
        )
        
        # Return only the response text
        return QueryResponse(response=result.get("response", ""))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@app.post("/smart-query", response_model=SmartQueryResponse)
async def process_smart_query(request: SmartQueryRequest):
    """
    Procesar consulta usando el supervisor inteligente para selección automática de agente
    
    - **query**: La consulta del usuario sobre Food Service 2025
    - **use_cache**: Si usar cache para la consulta (por defecto: true)  
    - **include_routing_info**: Si incluir explicación del enrutamiento (por defecto: false)
    """
    try:
        logger.info(f"Processing smart query: {request.query[:100]}...")
        
        # Step 1: Use intelligent supervisor to route the query
        routing_decision = supervisor.route_query(request.query)
        selected_agent = routing_decision.selected_agent.value
        
        logger.info(f"Smart routing selected: {selected_agent} (confidence: {routing_decision.confidence:.2f})")
        
        # Step 2: Process query with selected agent
        result = orchestrator.process_query(
            query=request.query,
            agent_type=selected_agent,
            use_cache=request.use_cache
        )
        
        # Step 3: Prepare response
        response = SmartQueryResponse(
            response=result.get("response", ""),
            agent_used=selected_agent,
            routing_confidence=routing_decision.confidence
        )
        
        # Include routing explanation if requested
        if request.include_routing_info:
            response.routing_explanation = supervisor.get_routing_explanation(routing_decision)
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing smart query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint no encontrado",
            "message": "El endpoint solicitado no existe",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "message": "Ha ocurrido un error interno. Por favor intente más tarde.",
            "timestamp": datetime.now().isoformat()
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Food Service 2025 API started")
    logger.info("📋 Available endpoints:")
    logger.info("   • POST /query - Manual agent selection")
    logger.info("   • POST /smart-query - Automatic agent selection with intelligent routing")
    logger.info("   • WebSocket /ws/chat - Real-time chat with conversation memory")
    logger.info("   • POST /chat/session - Create new chat session")
    logger.info("   • GET /chat/session/{id} - Get session info")
    logger.info("   • GET /chat/session/{id}/messages - Get session messages")
    logger.info("   • DELETE /chat/session/{id} - Close session")
    logger.info("   • GET /chat/stats - Chat system statistics")
    logger.info(f"📊 Orchestrator initialized with {len(orchestrator.agents)} agents")
    logger.info(f"🧠 Intelligent supervisor initialized with AI-powered routing")
    logger.info(f"💬 Chat memory system initialized with persistent Redis storage")
    logger.info(f"💾 Redis connected: {orchestrator.redis_manager.is_connected()}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Food Service 2025 API shutting down")

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 DEBUG: Starting uvicorn server...")
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    print(f"🌐 DEBUG: Server will run on {host}:{port}")
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=os.getenv('ENVIRONMENT', 'production') == 'development',
        log_level="info"
    )