"""
Document Search Tool for Food Service 2025
Handles PDF document search and indexing for general queries
"""

import os
import logging
import PyPDF2
import pandas as pd
from typing import List, Dict, Any, Optional
from difflib import SequenceMatcher
import re
from .vector_store import VectorStore

logger = logging.getLogger(__name__)

class DocumentSearchTool:
    def __init__(self, folder_path: str):
        """
        Initialize document search tool with vector store
        
        Args:
            folder_path: Path to the folder containing PDF documents
        """
        self.folder_path = folder_path
        self.indexed_documents = {}
        
        # Initialize vector store with error handling
        disable_vector_store = os.getenv('DISABLE_VECTOR_STORE', 'false').lower() == 'true'
        
        if disable_vector_store:
            logger.info("Vector store disabled by environment variable")
            self.vector_store = None
            self.vector_store_enabled = False
        else:
            try:
                vector_store_name = folder_path.replace('/', '_').replace('\\', '_')
                vector_store_path = f"vector_stores/{vector_store_name}"
                self.vector_store = VectorStore(vector_store_path=vector_store_path)
                self.vector_store_enabled = True
            except Exception as e:
                logger.error(f"Failed to initialize vector store: {str(e)}")
                self.vector_store = None
                self.vector_store_enabled = False
        
        self.index_documents()
    
    def index_documents(self) -> None:
        """Index all PDF and Excel documents in the folder"""
        if not os.path.exists(self.folder_path):
            logger.warning(f"Folder path does not exist: {self.folder_path}")
            return
        
        try:
            for filename in os.listdir(self.folder_path):
                file_path = os.path.join(self.folder_path, filename)
                content = None
                
                if filename.lower().endswith('.pdf'):
                    content = self._extract_pdf_content(file_path)
                elif filename.lower().endswith(('.xlsx', '.xls')):
                    content = self._extract_excel_content(file_path)
                
                if content:
                    self.indexed_documents[filename] = {
                        'content': content,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'type': 'pdf' if filename.lower().endswith('.pdf') else 'excel'
                    }
                    logger.info(f"Indexed document: {filename}")
            
            # Add documents to vector store if enabled
            if self.vector_store_enabled:
                self._add_to_vector_store()
            else:
                logger.info("Vector store disabled, using keyword search only")
            
            logger.info(f"Indexed {len(self.indexed_documents)} documents from {self.folder_path}")
            
        except Exception as e:
            logger.error(f"Error indexing documents: {str(e)}")
    
    def _add_to_vector_store(self) -> None:
        """Add documents to vector store with chunking"""
        try:
            if not self.indexed_documents:
                return
            
            # Check if vector store already has documents
            if self.vector_store.get_stats()["total_documents"] >= len(self.indexed_documents):
                logger.info("Vector store already contains documents, skipping re-indexing")
                return
            
            # Clear existing vector store
            self.vector_store.clear()
            
            texts = []
            metadatas = []
            
            for filename, doc_data in self.indexed_documents.items():
                content = doc_data['content']
                
                # Chunk the content with smaller chunks to reduce memory usage
                chunks = self.vector_store.chunk_text(content, chunk_size=500, overlap=50)
                
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) > 10:  # Only add meaningful chunks
                        texts.append(chunk)
                        metadatas.append({
                            'filename': filename,
                            'chunk_id': i,
                            'total_chunks': len(chunks),
                            'file_type': doc_data['type'],
                            'file_path': doc_data['path']
                        })
            
            logger.info(f"Prepared {len(texts)} chunks for vector store")
            
            # Add to vector store (now with batching)
            self.vector_store.add_documents(texts, metadatas)
            logger.info(f"Completed adding chunks to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            logger.warning("Vector store indexing failed, will use keyword search as fallback")
    
    def _extract_pdf_content(self, file_path: str) -> Optional[str]:
        """Extract text content from PDF file"""
        try:
            content = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    content += page.extract_text() + "\n"
            
            # Clean up the content
            content = re.sub(r'\s+', ' ', content).strip()
            return content
            
        except Exception as e:
            logger.error(f"Error extracting PDF content from {file_path}: {str(e)}")
            return None
    
    def _extract_excel_content(self, file_path: str) -> Optional[str]:
        """Extract text content from Excel file"""
        try:
            # Read Excel file
            if file_path.lower().endswith('.xlsx'):
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='openpyxl')
            else:  # .xls
                df_dict = pd.read_excel(file_path, sheet_name=None, engine='xlrd')
            
            content_parts = []
            
            for sheet_name, df in df_dict.items():
                # Add sheet name as header
                content_parts.append(f"\n=== HOJA: {sheet_name} ===\n")
                
                # Convert DataFrame to string with proper formatting
                # Include column headers
                if not df.empty:
                    # Add column headers
                    headers = " | ".join(str(col) for col in df.columns)
                    content_parts.append(f"COLUMNAS: {headers}\n")
                    
                    # Add rows
                    for index, row in df.iterrows():
                        row_data = " | ".join(str(val) if pd.notna(val) else "" for val in row)
                        content_parts.append(f"FILA {index + 1}: {row_data}")
                else:
                    content_parts.append("(Hoja vacía)")
            
            # Join all content
            content = "\n".join(content_parts)
            
            # Clean up the content
            content = re.sub(r'\s+', ' ', content).strip()
            return content
            
        except Exception as e:
            logger.error(f"Error extracting Excel content from {file_path}: {str(e)}")
            return None
    
    def _calculate_relevance_score(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Direct substring match gets high score
        if query_lower in content_lower:
            return 0.9
        
        # Check for keyword matches
        query_words = set(query_lower.split())
        content_words = set(content_lower.split())
        
        if not query_words:
            return 0.0
        
        matches = len(query_words.intersection(content_words))
        keyword_score = matches / len(query_words)
        
        # Use sequence matcher for fuzzy matching
        similarity_score = SequenceMatcher(None, query_lower, content_lower[:1000]).ratio()
        
        # Combined score
        return max(keyword_score * 0.7, similarity_score * 0.3)
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search documents using vector store for semantic similarity
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of relevant document excerpts with scores
        """
        try:
            # Use vector store for semantic search if enabled
            if not self.vector_store_enabled or self.vector_store is None:
                logger.info("Vector store not available, using keyword search")
                return self._fallback_keyword_search(query, max_results)
            
            vector_results = self.vector_store.search(query, k=max_results * 2, score_threshold=0.3)
            
            if not vector_results:
                logger.info("No vector search results, falling back to keyword search")
                return self._fallback_keyword_search(query, max_results)
            
            # Convert vector results to expected format
            results = []
            seen_files = set()
            
            for result in vector_results:
                metadata = result['metadata']
                filename = metadata['filename']
                
                # Avoid duplicate files in results
                if filename in seen_files:
                    continue
                seen_files.add(filename)
                
                results.append({
                    'file': filename,
                    'score': result['score'],
                    'content': result['document'],
                    'path': metadata['file_path'],
                    'chunk_id': metadata['chunk_id'],
                    'vector_score': True
                })
                
                if len(results) >= max_results:
                    break
            
            logger.info(f"Vector search found {len(results)} results for: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            return self._fallback_keyword_search(query, max_results)
    
    def _fallback_keyword_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Fallback to keyword-based search if vector search fails"""
        try:
            results = []
            
            for filename, doc_data in self.indexed_documents.items():
                content = doc_data['content']
                
                # Calculate relevance score
                score = self._calculate_relevance_score(query, content)
                
                if score > 0.1:  # Minimum threshold
                    # Extract relevant excerpt
                    excerpt = self._extract_relevant_excerpt(query, content)
                    
                    results.append({
                        'file': filename,
                        'score': score,
                        'content': excerpt,
                        'path': doc_data['path'],
                        'size': doc_data['size'],
                        'vector_score': False
                    })
            
            # Sort by score (descending) and limit results
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error in fallback search: {str(e)}")
            return []
    
    def _extract_relevant_excerpt(self, query: str, content: str, max_length: int = 500) -> str:
        """Extract relevant excerpt from content based on query"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Find the best match position
        best_pos = content_lower.find(query_lower)
        
        if best_pos == -1:
            # If no direct match, find best keyword match
            query_words = query_lower.split()
            best_pos = 0
            best_score = 0
            
            for i in range(0, len(content_lower) - 100, 50):
                excerpt = content_lower[i:i + 200]
                score = sum(1 for word in query_words if word in excerpt)
                if score > best_score:
                    best_score = score
                    best_pos = i
        
        # Extract excerpt around the best position
        start = max(0, best_pos - 100)
        end = min(len(content), best_pos + max_length)
        
        excerpt = content[start:end].strip()
        
        # Add ellipsis if truncated
        if start > 0:
            excerpt = "..." + excerpt
        if end < len(content):
            excerpt = excerpt + "..."
        
        return excerpt
    
    def refresh_index(self) -> None:
        """Refresh the document index and vector store"""
        self.indexed_documents.clear()
        if self.vector_store_enabled and self.vector_store:
            self.vector_store.clear()
        self.index_documents()
        logger.info("Document index refreshed")
    
    def get_indexed_files(self) -> List[str]:
        """Get list of indexed file names"""
        return list(self.indexed_documents.keys())
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed documents and vector store"""
        if not self.indexed_documents:
            return {
                "total_documents": 0,
                "total_size": 0,
                "folder_path": self.folder_path,
                "vector_store": self.vector_store.get_stats() if self.vector_store_enabled and self.vector_store else {"status": "disabled"}
            }
        
        total_size = sum(doc['size'] for doc in self.indexed_documents.values())
        
        return {
            "total_documents": len(self.indexed_documents),
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "folder_path": self.folder_path,
            "document_names": list(self.indexed_documents.keys()),
            "vector_store": self.vector_store.get_stats() if self.vector_store_enabled and self.vector_store else {"status": "disabled"}
        }