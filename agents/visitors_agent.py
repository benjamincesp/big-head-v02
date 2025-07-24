"""
Visitors Agent for Food Service 2025
Handles visitor-specific queries with exact data extraction
"""

import logging
import openai
from typing import Dict, Any, List
from tools.visitor_query import VisitorQueryTool

logger = logging.getLogger(__name__)

class VisitorsAgent:
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.visitor_tool = VisitorQueryTool("folders/visitors")
        self.agent_type = "visitors"
        
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
                
                gpt_response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "Eres un formateador de datos. Solo mejora la presentación sin agregar información nueva."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=400,
                    temperature=0.1
                )
                
                final_response = gpt_response.choices[0].message.content.strip()
            else:
                final_response = "👥 No se encontraron datos específicos de visitantes."
            
            return {
                "agent": self.agent_type,
                "response": final_response,
                "data": visitor_data,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in VisitorsAgent.process_query: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"❌ Error al procesar consulta de visitantes: {str(e)}",
                "data": {"daily_stats": {}, "demographics": {}, "total_visitors": None, "trends": []},
                "success": False
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