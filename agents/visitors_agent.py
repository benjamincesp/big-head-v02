"""
Visitors Agent for Food Service 2025
Handles visitor-specific queries with exact data extraction
"""

import logging
from typing import Dict, Any, List
from tools.visitor_query import VisitorQueryTool
from openai_client import get_openai_client
from exceptions import OpenAIError, DocumentError, AgentError

logger = logging.getLogger(__name__)

class VisitorsAgent:
    def __init__(self, openai_api_key: str):
        print("👥 DEBUG: VisitorsAgent - Setting up robust OpenAI client...")
        try:
            self.openai_client = get_openai_client(openai_api_key)
            print("👥 DEBUG: VisitorsAgent - Robust OpenAI client initialized")
        except Exception as e:
            print(f"❌ DEBUG: VisitorsAgent - OpenAI client failed: {str(e)}")
            raise AgentError(f"Failed to initialize OpenAI client: {str(e)}")
        
        print("👥 DEBUG: VisitorsAgent - Initializing visitor tool for 'folders/visitors'...")
        try:
            self.visitor_tool = VisitorQueryTool("folders/visitors")
            print("👥 DEBUG: VisitorsAgent - Visitor tool initialized")
        except Exception as e:
            print(f"❌ DEBUG: VisitorsAgent - Visitor tool failed: {str(e)}")
            raise AgentError(f"Failed to initialize visitor tool: {str(e)}")
        
        self.agent_type = "visitors"
        print("✅ DEBUG: VisitorsAgent initialization complete")
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process visitor-specific queries
        Returns only exact data, never invents information
        """
        try:
            # Extract visitor data based on query
            visitor_data = self.visitor_tool.extract_visitor_info(query)
            
            if not any([visitor_data["daily_stats"], visitor_data["demographics"], 
                       visitor_data["total_visitors"], visitor_data["trends"]]):
                return {
                    "agent": self.agent_type,
                    "response": "👥 No se encontraron datos específicos de visitantes para esta consulta.",
                    "data": visitor_data,
                    "success": True
                }
            
            # Format response with exact data
            response_parts = []
            
            if visitor_data["total_visitors"]:
                response_parts.append(f"👥 **Total de visitantes:** {visitor_data['total_visitors']}")
            
            if visitor_data["daily_stats"]:
                response_parts.append("\n📅 **Estadísticas por día:**")
                for day, count in visitor_data["daily_stats"].items():
                    response_parts.append(f"• {day}: {count} visitantes")
            
            if visitor_data["demographics"]:
                response_parts.append("\n📊 **Demografía de visitantes:**")
                for demo_key, demo_value in visitor_data["demographics"].items():
                    response_parts.append(f"• {demo_key}: {demo_value}")
            
            if visitor_data["trends"]:
                response_parts.append("\n📈 **Tendencias:**")
                for trend in visitor_data["trends"]:
                    response_parts.append(f"• {trend}")
            
            # Use GPT only for formatting, not for inventing data
            if response_parts:
                formatted_response = "\n".join(response_parts)
                
                prompt = f"""
                Formatea la siguiente información de visitantes de Food Service 2025.
                NO agregues información que no esté presente.
                NO inventes números o datos.
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
                final_response = "👥 No se encontraron datos específicos de visitantes."
            
            return {
                "agent": self.agent_type,
                "response": final_response,
                "data": visitor_data,
                "success": True
            }
            
        except OpenAIError as e:
            logger.error(f"OpenAI error in VisitorsAgent: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"🤖 Error de conexión con el servicio de IA. Intente nuevamente en unos momentos.",
                "data": {"daily_stats": {}, "demographics": {}, "total_visitors": None, "trends": []},
                "success": False,
                "error_type": "openai_error",
                "error_details": e.to_dict()
            }
        except DocumentError as e:
            logger.error(f"Document error in VisitorsAgent: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"📄 Error al procesar documentos de visitantes: {str(e)}",
                "data": {"daily_stats": {}, "demographics": {}, "total_visitors": None, "trends": []},
                "success": False,
                "error_type": "document_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error in VisitorsAgent.process_query: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"❌ Error interno del sistema. Por favor intente nuevamente.",
                "data": {"daily_stats": {}, "demographics": {}, "total_visitors": None, "trends": []},
                "success": False,
                "error_type": "system_error"
            }
    
    def refresh_data(self) -> Dict[str, Any]:
        """Refresh the visitor data index"""
        try:
            self.visitor_tool.refresh_index()
            return {
                "agent": self.agent_type,
                "message": "✅ Datos de visitantes actualizados correctamente",
                "success": True
            }
        except Exception as e:
            logger.error(f"Error refreshing VisitorsAgent data: {str(e)}")
            return {
                "agent": self.agent_type,
                "message": f"❌ Error al actualizar datos de visitantes: {str(e)}",
                "success": False
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get visitor agent statistics"""
        stats = self.visitor_tool.get_statistics()
        return {
            "agent": self.agent_type,
            "documents_processed": stats["documents_processed"],
            "visitors_data_points": stats["total_data_points"],
            "folder_path": "folders/visitors"
        }