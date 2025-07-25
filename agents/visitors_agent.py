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
        
        print("👥 DEBUG: VisitorsAgent - Initializing intelligent search for 'folders/visitors'...")
        try:
            from tools.intelligent_search import IntelligentSearchSystem
            self.intelligent_search = IntelligentSearchSystem("folders/visitors")
            # Keep the original tool as backup
            self.visitor_tool = VisitorQueryTool("folders/visitors")
            print("👥 DEBUG: VisitorsAgent - Intelligent search and visitor tool initialized")
        except Exception as e:
            print(f"❌ DEBUG: VisitorsAgent - Initialization failed: {str(e)}")
            raise AgentError(f"Failed to initialize visitors agent: {str(e)}")
        
        self.agent_type = "visitors"
        print("✅ DEBUG: VisitorsAgent initialization complete")
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process visitor-specific queries with intelligent search
        """
        try:
            # Use intelligent search that ALWAYS finds relevant content
            search_results = self.intelligent_search.search(query, max_results=4)
            
            # Also try the original visitor tool for specific data extraction
            try:
                visitor_data = self.visitor_tool.extract_visitor_info(query)
            except:
                visitor_data = {"daily_stats": {}, "demographics": {}, "total_visitors": None, "trends": []}
            
            # Prepare enhanced context from intelligent search
            context_parts = []
            sources = []
            
            for i, result in enumerate(search_results[:3]):
                context_parts.append(f"""
                Fuente {i+1}: {result.get('file', 'Documento de Visitantes')}
                Contenido: {result['content']}
                """)
                sources.append(result.get('file', 'Documento'))
            
            # Add any structured data found
            if visitor_data["total_visitors"]:
                context_parts.append(f"\\nTotal de visitantes: {visitor_data['total_visitors']}")
            
            if visitor_data["demographics"]:
                demo_text = "\\n".join([f"• {key}: {value}" for key, value in visitor_data["demographics"].items()])
                context_parts.append(f"\\nDemografía encontrada:\\n{demo_text}")
            
            context = "\\n".join(context_parts)
            
            prompt = f"""
            Eres un experto en Food Service 2025 especializado en información de VISITANTES y ASISTENCIA.
            
            IMPORTANTE: Proporciona SIEMPRE una respuesta útil e informativa sobre visitantes.
            
            Instrucciones:
            1. Enfócate en información de visitantes, asistencia, demografía, y estadísticas de público
            2. Usa la información proporcionada como base principal
            3. Mantén la respuesta entre 2-4 párrafos
            4. Incluye emojis apropiados (👥, 📊, 📈, 🎯)
            5. Si encuentras números específicos de asistencia, menciónalos
            6. Si la información es limitada, proporciona contexto general sobre el perfil de visitantes del evento
            7. Habla sobre el tipo de profesionales que asisten, sectores representados, etc.
            
            Consulta del usuario: {query}
            
            Información disponible sobre visitantes:
            {context}
            
            Proporciona una respuesta completa sobre visitantes:
            """
            
            messages = [
                {"role": "system", "content": "Eres un especialista en Food Service 2025 enfocado en visitantes y estadísticas de asistencia. SIEMPRE proporcionas información útil sobre el público del evento."},
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
                "data": visitor_data
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
        """Refresh the intelligent search and visitor data index"""
        try:
            self.intelligent_search.refresh_index()
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