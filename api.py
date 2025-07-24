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

# Initialize FastAPI app
app = FastAPI(
    title="Food Service 2025 Multi-Agent API",
    description="Sistema multi-agente para consultas sobre Food Service 2025",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
openai_api_key = os.getenv('OPENAI_API_KEY')
if not openai_api_key:
    logger.error("OPENAI_API_KEY environment variable not set")
    raise ValueError("OPENAI_API_KEY environment variable is required")

redis_config = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'password': os.getenv('REDIS_PASSWORD'),
    'db': int(os.getenv('REDIS_DB', 0))
}

orchestrator = FoodServiceOrchestrator(openai_api_key, redis_config)

# Pydantic models
class QueryRequest(BaseModel):
    query: str = Field(..., description="Consulta del usuario", min_length=1)
    agent_type: Optional[str] = Field(None, description="Tipo de agente específico (opcional)")
    use_cache: bool = Field(True, description="Usar cache para la consulta")

class QueryResponse(BaseModel):
    response: str

# API Endpoints

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
    
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')
    
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=os.getenv('ENVIRONMENT', 'production') == 'development',
        log_level="info"
    )