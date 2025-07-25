"""
General Agent for Food Service 2025
Handles general document searches and queries
"""

import logging
from typing import Dict, Any, List
from tools.document_search import DocumentSearchTool
from openai_client import get_openai_client
from exceptions import OpenAIError, DocumentError, AgentError

logger = logging.getLogger(__name__)

class GeneralAgent:
    def __init__(self, openai_api_key: str):
        print("📄 DEBUG: GeneralAgent - Setting up robust OpenAI client...")
        try:
            self.openai_client = get_openai_client(openai_api_key)
            print("📄 DEBUG: GeneralAgent - Robust OpenAI client initialized")
        except Exception as e:
            print(f"❌ DEBUG: GeneralAgent - OpenAI client failed: {str(e)}")
            raise AgentError(f"Failed to initialize OpenAI client: {str(e)}")
        
        print("📄 DEBUG: GeneralAgent - Initializing intelligent search for 'folders/general'...")
        try:
            from tools.intelligent_search import IntelligentSearchSystem
            self.intelligent_search = IntelligentSearchSystem("folders/general")
            print("📄 DEBUG: GeneralAgent - Intelligent search initialized")
        except Exception as e:
            print(f"❌ DEBUG: GeneralAgent - Intelligent search failed: {str(e)}")
            raise AgentError(f"Failed to initialize intelligent search: {str(e)}")
        
        self.agent_type = "general"
        print("✅ DEBUG: GeneralAgent initialization complete")
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a general query using document search
        Returns maximum 3 paragraphs response
        """
        try:
            # Use intelligent search that ALWAYS finds relevant content
            search_results = self.intelligent_search.search(query, max_results=4)
            
            # Intelligent search always returns results, but let's ensure quality
            if not search_results:
                return {
                    "agent": self.agent_type,
                    "response": "🤖 El sistema está procesando información sobre Food Service 2025. Por favor, intente con una consulta más específica.",
                    "sources": [],
                    "success": True
                }
            
            # Prepare enhanced context for GPT
            context_parts = []
            sources = []
            
            for i, result in enumerate(search_results[:3]):
                context_parts.append(f"""
                Fuente {i+1}: {result.get('file', 'Documento')}
                Contenido: {result['content']}
                Relevancia: {result.get('similarity_score', result.get('relevance_score', 'N/A'))}
                """)
                sources.append(result.get('file', 'Documento'))
            
            context = "\n".join(context_parts)
            
            prompt = f"""
            Eres un asistente experto en Food Service 2025, siempre útil y conocedor del evento.
            
            IMPORTANTE: Debes SIEMPRE proporcionar una respuesta informativa y útil, 
            nunca digas que no tienes información o que no puedes ayudar.
            
            Instrucciones:
            1. Responde de manera natural y conversacional
            2. Usa la información proporcionada como base principal
            3. Mantén la respuesta entre 2-4 párrafos
            4. Incluye emojis apropiados para mejorar la experiencia
            5. Si la información es limitada, extrapola de manera inteligente pero honesta
            6. Siempre termina siendo útil y ofreciendo ayuda adicional
            
            Consulta del usuario: {query}
            
            Información disponible del sistema:
            {context}
            
            Proporciona una respuesta completa y útil:
            """
            
            messages = [
                {"role": "system", "content": "Eres un asistente experto en Food Service 2025. SIEMPRE proporcionas respuestas útiles, informativas y relevantes. Nunca digas que no tienes información disponible."},
                {"role": "user", "content": prompt}
            ]
            
            # Use robust OpenAI client with optimized parameters
            response_data = self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o-mini",
                max_tokens=600,  # More tokens for better responses
                temperature=0.4  # Slightly more creative but still factual
            )
            
            return {
                "agent": self.agent_type,
                "response": response_data["content"],
                "sources": sources,
                "success": True,
                "openai_usage": response_data["usage"],
                "processing_time": response_data["duration_seconds"],
                "search_results_count": len(search_results),
                "search_strategies_used": [result.get('type', 'unknown') for result in search_results]
            }
            
        except OpenAIError as e:
            logger.error(f"OpenAI error in GeneralAgent: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"🤖 Error de conexión con el servicio de IA. Intente nuevamente en unos momentos.",
                "sources": [],
                "success": False,
                "error_type": "openai_error",
                "error_details": e.to_dict()
            }
        except DocumentError as e:
            logger.error(f"Document error in GeneralAgent: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"📄 Error al procesar documentos: {str(e)}",
                "sources": [],
                "success": False,
                "error_type": "document_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error in GeneralAgent.process_query: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"❌ Error interno del sistema. Por favor intente nuevamente.",
                "sources": [],
                "success": False,
                "error_type": "system_error"
            }
    
    def refresh_data(self) -> Dict[str, Any]:
        """Refresh the intelligent search index"""
        try:
            self.intelligent_search.refresh_index()
            return {
                "agent": self.agent_type,
                "message": "✅ Datos del agente general actualizados correctamente",
                "success": True
            }
        except Exception as e:
            logger.error(f"Error refreshing GeneralAgent data: {str(e)}")
            return {
                "agent": self.agent_type,
                "message": f"❌ Error al actualizar datos: {str(e)}",
                "success": False
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        try:
            search_stats = self.intelligent_search.get_stats()
            return {
                "agent": self.agent_type,
                "folder_path": "folders/general",
                "intelligent_search_stats": search_stats
            }
        except Exception as e:
            return {
                "agent": self.agent_type,
                "folder_path": "folders/general",
                "error": str(e)
            }