"""
Exhibitors Agent for Food Service 2025
Handles exhibitor-specific queries with exact data extraction
"""

import logging
from typing import Dict, Any, List
from tools.exhibitor_query import ExhibitorQueryTool
from openai_client import get_openai_client
from exceptions import OpenAIError, DocumentError, AgentError

logger = logging.getLogger(__name__)

class ExhibitorsAgent:
    def __init__(self, openai_api_key: str):
        print("🏢 DEBUG: ExhibitorsAgent - Setting up robust OpenAI client...")
        try:
            self.openai_client = get_openai_client(openai_api_key)
            print("🏢 DEBUG: ExhibitorsAgent - Robust OpenAI client initialized")
        except Exception as e:
            print(f"❌ DEBUG: ExhibitorsAgent - OpenAI client failed: {str(e)}")
            raise AgentError(f"Failed to initialize OpenAI client: {str(e)}")
        
        print("🏢 DEBUG: ExhibitorsAgent - Initializing intelligent search for 'folders/exhibitors'...")
        try:
            from tools.intelligent_search import IntelligentSearchSystem
            self.intelligent_search = IntelligentSearchSystem("folders/exhibitors")
            # Keep the original tool as backup
            self.exhibitor_tool = ExhibitorQueryTool("folders/exhibitors")
            print("🏢 DEBUG: ExhibitorsAgent - Intelligent search and exhibitor tool initialized")
        except Exception as e:
            print(f"❌ DEBUG: ExhibitorsAgent - Initialization failed: {str(e)}")
            raise AgentError(f"Failed to initialize exhibitors agent: {str(e)}")
        
        self.agent_type = "exhibitors"
        print("✅ DEBUG: ExhibitorsAgent initialization complete")
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process exhibitor-specific queries with intelligent search
        """
        try:
            # Use intelligent search that ALWAYS finds relevant content
            search_results = self.intelligent_search.search(query, max_results=4)
            
            # Also try the original exhibitor tool for specific data extraction
            try:
                exhibitor_data = self.exhibitor_tool.extract_exhibitor_info(query)
            except:
                exhibitor_data = {"companies": [], "stats": {}}
            
            # Prepare enhanced context from intelligent search
            context_parts = []
            sources = []
            
            for i, result in enumerate(search_results[:3]):
                context_parts.append(f"""
                Fuente {i+1}: {result.get('file', 'Documento de Expositores')}
                Contenido: {result['content']}
                """)
                sources.append(result.get('file', 'Documento'))
            
            # Add any structured data found
            if exhibitor_data["companies"]:
                companies_text = "\\n".join([f"• {company['name']}" + (f" (Stand: {company['stand']})" if company.get('stand') else "") 
                                          for company in exhibitor_data["companies"][:5]])
                context_parts.append(f"\\nEmpresas encontradas:\\n{companies_text}")
            
            context = "\\n".join(context_parts)
            
            prompt = f"""
            Eres un experto en Food Service 2025 especializado en información de EXPOSITORES y EMPRESAS.
            
            IMPORTANTE: Proporciona SIEMPRE una respuesta útil e informativa sobre expositores.
            
            Instrucciones:
            1. Enfócate en información de empresas, expositores, stands, y participantes comerciales
            2. Usa la información proporcionada como base principal
            3. Mantén la respuesta entre 2-4 párrafos
            4. Incluye emojis apropiados (🏢, 🏪, 📊, 🌟)
            5. Si encuentras empresas específicas, menciónalas
            6. Si la información es limitada, proporciona contexto general sobre expositores del evento
            
            Consulta del usuario: {query}
            
            Información disponible sobre expositores:
            {context}
            
            Proporciona una respuesta completa sobre expositores:
            """
            
            messages = [
                {"role": "system", "content": "Eres un especialista en Food Service 2025 enfocado en expositores y empresas participantes. SIEMPRE proporcionas información útil sobre el aspecto comercial del evento."},
                {"role": "user", "content": prompt}
            ]
            
            # Use robust OpenAI client
            response_data = self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o-mini",
                max_tokens=600,
                temperature=0.4
            )
            
            return {
                "agent": self.agent_type,
                "response": response_data["content"],
                "sources": sources,
                "success": True,
                "openai_usage": response_data["usage"],
                "processing_time": response_data["duration_seconds"],
                "search_results_count": len(search_results),
                "data": exhibitor_data
            }
            
        except OpenAIError as e:
            logger.error(f"OpenAI error in ExhibitorsAgent: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"🤖 Error de conexión con el servicio de IA. Intente nuevamente en unos momentos.",
                "data": {"companies": [], "stats": {}},
                "success": False,
                "error_type": "openai_error",
                "error_details": e.to_dict()
            }
        except DocumentError as e:
            logger.error(f"Document error in ExhibitorsAgent: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"📄 Error al procesar documentos de expositores: {str(e)}",
                "data": {"companies": [], "stats": {}},
                "success": False,
                "error_type": "document_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error in ExhibitorsAgent.process_query: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"❌ Error interno del sistema. Por favor intente nuevamente.",
                "data": {"companies": [], "stats": {}},
                "success": False,
                "error_type": "system_error"
            }
    
    def refresh_data(self) -> Dict[str, Any]:
        """Refresh the intelligent search and exhibitor data index"""
        try:
            self.intelligent_search.refresh_index()
            self.exhibitor_tool.refresh_index()
            return {
                "agent": self.agent_type,
                "message": "✅ Datos de expositores actualizados correctamente",
                "success": True
            }
        except Exception as e:
            logger.error(f"Error refreshing ExhibitorsAgent data: {str(e)}")
            return {
                "agent": self.agent_type,
                "message": f"❌ Error al actualizar datos de expositores: {str(e)}",
                "success": False
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get exhibitor agent statistics"""
        stats = self.exhibitor_tool.get_statistics()
        return {
            "agent": self.agent_type,
            "documents_processed": stats["documents_processed"],
            "companies_found": stats["total_companies"],
            "folder_path": "folders/exhibitors"
        }