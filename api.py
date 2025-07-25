"""
FastAPI REST API for Food Service 2025 Multi-Agent System
Provides REST endpoints for interacting with the multi-agent system
"""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from orchestrator import FoodServiceOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import configuration and exceptions
from config import config
from exceptions import *

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
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=["POST", "GET"],
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

# API Endpoints

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
    logger.info("🚀 Food Service 2025 API started - Single endpoint: POST /query")
    logger.info(f"📊 Orchestrator initialized with {len(orchestrator.agents)} agents")
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