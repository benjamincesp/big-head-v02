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
        
        print("🏢 DEBUG: ExhibitorsAgent - Initializing exhibitor tool for 'folders/exhibitors'...")
        try:
            self.exhibitor_tool = ExhibitorQueryTool("folders/exhibitors")
            print("🏢 DEBUG: ExhibitorsAgent - Exhibitor tool initialized")
        except Exception as e:
            print(f"❌ DEBUG: ExhibitorsAgent - Exhibitor tool failed: {str(e)}")
            raise AgentError(f"Failed to initialize exhibitor tool: {str(e)}")
        
        self.agent_type = "exhibitors"
        print("✅ DEBUG: ExhibitorsAgent initialization complete")
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process exhibitor-specific queries
        Returns only exact data, never invents information
        """
        try:
            # Extract exhibitor data based on query
            exhibitor_data = self.exhibitor_tool.extract_exhibitor_info(query)
            
            if not exhibitor_data["companies"] and not exhibitor_data["stats"]:
                return {
                    "agent": self.agent_type,
                    "response": "🏢 No se encontraron datos específicos de expositores para esta consulta.",
                    "data": exhibitor_data,
                    "success": True
                }
            
            # Format response with exact data
            response_parts = []
            
            if exhibitor_data["companies"]:
                response_parts.append("🏢 **Empresas expositoras encontradas:**")
                for company in exhibitor_data["companies"][:10]:  # Limit to 10
                    stand_info = f" (Stand: {company['stand']})" if company.get('stand') else ""
                    response_parts.append(f"• {company['name']}{stand_info}")
            
            if exhibitor_data["stats"]:
                response_parts.append("\n📊 **Estadísticas de expositores:**")
                for stat_key, stat_value in exhibitor_data["stats"].items():
                    response_parts.append(f"• {stat_key}: {stat_value}")
            
            # Use GPT only for formatting and structure, not for inventing data
            if response_parts:
                formatted_response = "\n".join(response_parts)
                
                prompt = f"""
                Formatea la siguiente información de expositores de Food Service 2025.
                NO agregues información que no esté presente.
                NO inventes datos.
                Solo mejora la presentación y añade emojis apropiados.
                
                Información:
                {formatted_response}
                
                Consulta original: {query}
                """
                
                messages = [
                    {"role": "system", "content": "Eres un formateador de datos. Solo mejora la presentación sin agregar información nueva."},
                    {"role": "user", "content": prompt}
                ]
                
                gpt_response = self.openai_client.chat_completion(
                    messages=messages,
                    model="gpt-4o-mini",
                    max_tokens=400,
                    temperature=0.1
                )
                
                final_response = gpt_response["content"]
            else:
                final_response = "🏢 No se encontraron datos específicos de expositores."
            
            return {
                "agent": self.agent_type,
                "response": final_response,
                "data": exhibitor_data,
                "success": True
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
        """Refresh the exhibitor data index"""
        try:
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