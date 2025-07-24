"""
General Agent for Food Service 2025
Handles general document searches and queries
"""

import logging
import openai
from typing import Dict, Any, List
from tools.document_search import DocumentSearchTool

logger = logging.getLogger(__name__)

class GeneralAgent:
    def __init__(self, openai_api_key: str):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        self.document_search = DocumentSearchTool("folders/general")
        self.agent_type = "general"
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a general query using document search
        Returns maximum 3 paragraphs response
        """
        try:
            # Search for relevant documents
            search_results = self.document_search.search(query)
            
            if not search_results:
                return {
                    "agent": self.agent_type,
                    "response": "📋 No se encontró información relevante en los documentos generales.",
                    "sources": [],
                    "success": True
                }
            
            # Prepare context for GPT
            context = "\n".join([f"Documento: {result['file']}\nContenido: {result['content']}" 
                               for result in search_results[:3]])
            
            prompt = f"""
            Eres un asistente especializado en Food Service 2025. 
            Responde la siguiente consulta basándote únicamente en la información proporcionada.
            Mantén la respuesta concisa, máximo 3 párrafos.
            Usa emojis apropiados para mejorar la experiencia del usuario.
            
            Consulta: {query}
            
            Información disponible:
            {context}
            
            Respuesta:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en eventos de Food Service. Responde de manera concisa y útil."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return {
                "agent": self.agent_type,
                "response": response.choices[0].message.content.strip(),
                "sources": [result['file'] for result in search_results[:3]],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in GeneralAgent.process_query: {str(e)}")
            return {
                "agent": self.agent_type,
                "response": f"❌ Error al procesar la consulta: {str(e)}",
                "sources": [],
                "success": False
            }
    
    def refresh_data(self) -> Dict[str, Any]:
        """Refresh the document search index"""
        try:
            self.document_search.refresh_index()
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
        return {
            "agent": self.agent_type,
            "documents_indexed": len(self.document_search.get_indexed_files()),
            "folder_path": "folders/general"
        }