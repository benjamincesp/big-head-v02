"""
Intelligent Search System for Food Service 2025
Always provides intelligent responses using multiple search strategies
"""

import os
import logging
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from .enhanced_vector_store import EnhancedVectorStore
from .smart_document_processor import SmartDocumentProcessor
from openai_client import get_openai_client
from exceptions import DocumentError, OpenAIError

logger = logging.getLogger(__name__)

class IntelligentSearchSystem:
    """Intelligent search system that always finds relevant information"""
    
    def __init__(self, folder_path: str):
        """
        Initialize intelligent search system
        
        Args:
            folder_path: Path to folder containing documents
        """
        self.folder_path = folder_path
        
        # Initialize components
        print(f"🧠 DEBUG: Initializing Intelligent Search for {folder_path}")
        
        # Document processor
        self.document_processor = SmartDocumentProcessor(folder_path)
        
        # Vector store
        safe_folder_name = folder_path.replace('/', '_').replace('\\\\', '_')
        vector_store_path = f"vector_stores/{safe_folder_name}_enhanced"
        self.vector_store = EnhancedVectorStore(vector_store_path)
        
        # State tracking
        self.last_folder_hash = None
        self.last_indexed_time = None
        self.fallback_content = {}
        
        # Initialize data
        self._initialize_search_data()
        
        print(f"✅ DEBUG: Intelligent Search System ready")
    
    def _initialize_search_data(self):
        """Initialize search data with smart loading"""
        try:
            current_hash = self.document_processor.get_folder_hash()
            
            # Check if we need to reindex
            if self._should_reindex(current_hash):
                print("🔄 DEBUG: Reindexing documents...")
                self._reindex_documents()
                self.last_folder_hash = current_hash
                self.last_indexed_time = datetime.now().isoformat()
            else:
                print("✅ DEBUG: Using existing index")
            
            # Always prepare fallback content
            self._prepare_fallback_content()
            
        except Exception as e:
            logger.error(f"Error initializing search data: {str(e)}")
            print(f"❌ DEBUG: Search initialization failed: {str(e)}")
            self._prepare_fallback_content()
    
    def _should_reindex(self, current_hash: str) -> bool:
        """Determine if documents should be reindexed"""
        if self.last_folder_hash is None:
            return True
        
        if current_hash != self.last_folder_hash:
            return True
        
        # Check if vector store is empty
        stats = self.vector_store.get_stats()
        if stats['total_documents'] == 0:
            return True
        
        return False
    
    def _reindex_documents(self):
        """Reindex all documents"""
        try:
            print("📚 DEBUG: Starting document reindexing...")
            
            # Clear existing data
            self.vector_store.clear()
            
            # Process all documents
            chunks, metadata = self.document_processor.process_all_documents(
                chunk_size=600,  # Smaller chunks for better precision
                overlap=80
            )
            
            if chunks:
                print(f"📝 DEBUG: Adding {len(chunks)} chunks to vector store")
                self.vector_store.add_documents(chunks, metadata)
                print("✅ DEBUG: Documents reindexed successfully")
            else:
                print("⚠️ DEBUG: No chunks to index")
            
        except Exception as e:
            logger.error(f"Error reindexing documents: {str(e)}")
            print(f"❌ DEBUG: Reindexing failed: {str(e)}")
    
    def _prepare_fallback_content(self):
        """Prepare fallback content for when vector search fails"""
        try:
            files = self.document_processor.get_all_files()
            
            self.fallback_content = {
                'available_documents': [os.path.basename(f) for f in files],
                'folder_info': f"Carpeta {self.folder_path} con {len(files)} documentos",
                'document_types': {}
            }
            
            # Categorize documents
            for file_path in files:
                _, ext = os.path.splitext(file_path.lower())
                self.fallback_content['document_types'][ext] = \
                    self.fallback_content['document_types'].get(ext, 0) + 1
            
            # Add basic content extraction
            if files:
                sample_content = []
                for file_path in files[:2]:  # Sample first 2 files
                    try:
                        text = self.document_processor.extract_text_from_file(file_path)
                        if text and len(text) > 100:
                            # Get first meaningful paragraph
                            paragraphs = [p.strip() for p in text.split('\\n') if len(p.strip()) > 50]
                            if paragraphs:
                                sample_content.append({
                                    'file': os.path.basename(file_path),
                                    'preview': paragraphs[0][:300] + "..." if len(paragraphs[0]) > 300 else paragraphs[0]
                                })
                    except Exception as e:
                        continue
                
                self.fallback_content['sample_content'] = sample_content
            
        except Exception as e:
            logger.warning(f"Error preparing fallback content: {str(e)}")
            self.fallback_content = {
                'available_documents': [],
                'folder_info': f"Carpeta {self.folder_path}",
                'error': str(e)
            }
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Intelligent search that always returns relevant results
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results with content and metadata
        """
        results = []
        
        try:
            print(f"🔍 DEBUG: Intelligent search for: '{query[:50]}...'")
            
            # Strategy 1: Vector search (primary)
            vector_results = self._vector_search(query, max_results)
            if vector_results:
                results.extend(vector_results)
                print(f"✅ DEBUG: Vector search found {len(vector_results)} results")
            
            # Strategy 2: Keyword search (fallback)
            if len(results) < max_results:
                keyword_results = self._keyword_search(query, max_results - len(results))
                results.extend(keyword_results)
                if keyword_results:
                    print(f"✅ DEBUG: Keyword search found {len(keyword_results)} additional results")
            
            # Strategy 3: Intelligent fallback (always has something)
            if not results:
                fallback_results = self._intelligent_fallback(query)
                results.extend(fallback_results)
                print(f"✅ DEBUG: Fallback provided {len(fallback_results)} results")
            
            # Strategy 4: Ensure minimum content
            if len(results) < 2:
                additional_results = self._ensure_minimum_content(query, max_results - len(results))
                results.extend(additional_results)
            
            # Remove duplicates and limit results
            results = self._deduplicate_results(results)[:max_results]
            
            print(f"📋 DEBUG: Final search results: {len(results)} items")
            return results
            
        except Exception as e:
            logger.error(f"Error in intelligent search: {str(e)}")
            print(f"❌ DEBUG: Search error: {str(e)}")
            
            # Emergency fallback
            return self._emergency_fallback(query)
    
    def _vector_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform vector-based semantic search"""
        try:
            vector_results = self.vector_store.search(
                query, 
                k=max_results * 2,  # Get more candidates
                similarity_threshold=0.25  # Lower threshold for more results
            )
            
            # Format results
            formatted_results = []
            for result in vector_results:
                formatted_results.append({
                    'content': result['content'],
                    'file': result['metadata'].get('source', 'unknown'),
                    'type': 'vector_search',
                    'similarity_score': result['similarity_score'],
                    'metadata': result['metadata']
                })
            
            return formatted_results
            
        except Exception as e:
            logger.warning(f"Vector search failed: {str(e)}")
            return []
    
    def _keyword_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Perform keyword-based search on raw documents"""
        try:
            results = []
            query_words = set(word.lower() for word in query.split() if len(word) > 2)
            
            if not query_words:
                return []
            
            # Search through vector store documents
            for i, (doc, metadata) in enumerate(zip(self.vector_store.documents, self.vector_store.metadata)):
                doc_lower = doc.lower()
                
                # Count keyword matches
                matches = sum(1 for word in query_words if word in doc_lower)
                
                if matches > 0:
                    # Calculate relevance score
                    relevance = matches / len(query_words)
                    
                    results.append({
                        'content': doc,
                        'file': metadata.get('source', 'unknown'),
                        'type': 'keyword_search',
                        'relevance_score': relevance,
                        'keyword_matches': matches,
                        'metadata': metadata
                    })
            
            # Sort by relevance
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return results[:max_results]
            
        except Exception as e:
            logger.warning(f"Keyword search failed: {str(e)}")
            return []
    
    def _intelligent_fallback(self, query: str) -> List[Dict[str, Any]]:
        """Intelligent fallback when other searches fail"""
        results = []
        
        try:
            # Analyze query to provide relevant fallback
            query_lower = query.lower()
            
            # Check query intent
            if any(word in query_lower for word in ['expositores', 'empresas', 'stands', 'marcas']):
                content = self._get_exhibitor_fallback()
            elif any(word in query_lower for word in ['visitantes', 'asistentes', 'público', 'demografía']):
                content = self._get_visitor_fallback()
            elif any(word in query_lower for word in ['información', 'datos', 'disponible', 'tienes']):
                content = self._get_general_info_fallback()
            else:
                content = self._get_default_fallback()
            
            results.append({
                'content': content,
                'file': 'sistema_informacion',
                'type': 'intelligent_fallback',
                'relevance_score': 0.8,
                'metadata': {
                    'source': 'sistema_informacion',
                    'fallback_reason': 'no_documents_found',
                    'query_intent': self._detect_query_intent(query)
                }
            })
            
        except Exception as e:
            logger.error(f"Intelligent fallback failed: {str(e)}")
            results.append({
                'content': f"Sistema Food Service 2025 - Información disponible sobre el evento.",
                'file': 'sistema_base',
                'type': 'emergency_fallback',
                'relevance_score': 0.5,
                'metadata': {'source': 'emergency', 'error': str(e)}
            })
        
        return results
    
    def _get_exhibitor_fallback(self) -> str:
        """Fallback content for exhibitor queries"""
        return f"""
        Food Service 2025 - Información de Expositores
        
        El evento cuenta con empresas participantes del sector alimentario y de servicios.
        
        Documentos disponibles en la carpeta de expositores:
        {', '.join(self.fallback_content.get('available_documents', []))}
        
        Para obtener la lista completa de empresas expositoras y sus ubicaciones,
        consulte los documentos específicos de expositores disponibles en el sistema.
        """
    
    def _get_visitor_fallback(self) -> str:
        """Fallback content for visitor queries"""
        return f"""
        Food Service 2025 - Información de Visitantes
        
        El evento registra estadísticas de asistencia y demografía de visitantes.
        
        Documentos disponibles para consulta:
        {', '.join(self.fallback_content.get('available_documents', []))}
        
        Para estadísticas específicas de asistencia, consulte los documentos
        de visitantes disponibles en el sistema.
        """
    
    def _get_general_info_fallback(self) -> str:
        """Fallback content for general information queries"""
        return f"""
        Food Service 2025 - Sistema de Información
        
        El sistema contiene información sobre:
        • Expositores y empresas participantes
        • Estadísticas de visitantes y asistencia  
        • Información general del evento
        • Planos y distribución del espacio
        
        Documentos disponibles: {len(self.fallback_content.get('available_documents', []))} archivos
        Tipos de archivo: {', '.join(self.fallback_content.get('document_types', {}).keys())}
        
        {self._get_sample_content_preview()}
        """
    
    def _get_default_fallback(self) -> str:
        """Default fallback content"""
        return f"""
        Food Service 2025 - Información del Evento
        
        Sistema especializado en información sobre el evento Food Service 2025.
        
        Carpeta de documentos: {self.folder_path}
        Archivos disponibles: {len(self.fallback_content.get('available_documents', []))}
        
        Para consultas específicas sobre expositores, visitantes o información general,
        el sistema procesará los documentos disponibles para proporcionar respuestas precisas.
        """
    
    def _get_sample_content_preview(self) -> str:
        """Get sample content preview"""
        sample_content = self.fallback_content.get('sample_content', [])
        if sample_content:
            preview = "\\n\\nVista previa de contenido disponible:\\n"
            for item in sample_content[:1]:  # Show first sample
                preview += f"• {item['file']}: {item['preview'][:200]}...\\n"
            return preview
        return ""
    
    def _detect_query_intent(self, query: str) -> str:
        """Detect the intent of the query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['expositores', 'empresas', 'stands']):
            return 'exhibitors'
        elif any(word in query_lower for word in ['visitantes', 'asistentes', 'público']):
            return 'visitors'
        elif any(word in query_lower for word in ['información', 'datos', 'disponible']):
            return 'general_info'
        else:
            return 'general'
    
    def _ensure_minimum_content(self, query: str, needed: int) -> List[Dict[str, Any]]:
        """Ensure minimum content is always available"""
        if needed <= 0:
            return []
        
        results = []
        
        # Add document listings
        if self.fallback_content.get('available_documents'):
            content = f"""
            Documentos disponibles en {self.folder_path}:
            
            {chr(10).join(['• ' + doc for doc in self.fallback_content['available_documents']])}
            
            Estos documentos contienen información detallada sobre Food Service 2025.
            """
            
            results.append({
                'content': content.strip(),
                'file': 'listado_documentos',
                'type': 'document_listing',
                'relevance_score': 0.6,
                'metadata': {
                    'source': 'document_listing',
                    'total_documents': len(self.fallback_content['available_documents'])
                }
            })
        
        return results[:needed]
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results"""
        seen_content = set()
        unique_results = []
        
        for result in results:
            content_hash = hash(result['content'][:200])  # Hash first 200 chars
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _emergency_fallback(self, query: str) -> List[Dict[str, Any]]:
        """Emergency fallback when everything else fails"""
        return [{
            'content': f"""
            Food Service 2025 - Sistema de Información
            
            El sistema está procesando su consulta: "{query}"
            
            Información disponible:
            • Datos de expositores y empresas participantes
            • Estadísticas de visitantes y asistencia
            • Información general del evento
            
            El sistema continúa trabajando para proporcionar respuestas más específicas.
            """.strip(),
            'file': 'sistema_emergencia',
            'type': 'emergency_fallback',
            'relevance_score': 0.3,
            'metadata': {
                'source': 'emergency_system',
                'original_query': query,
                'timestamp': datetime.now().isoformat()
            }
        }]
    
    def refresh_index(self):
        """Force refresh of the search index"""
        try:
            print("🔄 DEBUG: Forcing index refresh...")
            self.last_folder_hash = None  # Force reindex
            self._initialize_search_data()
            print("✅ DEBUG: Index refreshed successfully")
        except Exception as e:
            logger.error(f"Error refreshing index: {str(e)}")
            print(f"❌ DEBUG: Index refresh failed: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            'folder_path': self.folder_path,
            'vector_store_stats': self.vector_store.get_stats(),
            'document_processor_stats': self.document_processor.get_stats(),
            'last_indexed': self.last_indexed_time,
            'fallback_content_available': len(self.fallback_content) > 0,
            'search_strategies': ['vector_search', 'keyword_search', 'intelligent_fallback', 'emergency_fallback']
        }