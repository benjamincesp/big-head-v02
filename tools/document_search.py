"""
Document Search Tool for Food Service 2025
Handles PDF document search and indexing for general queries
"""

import os
import logging
import PyPDF2
import pandas as pd
import json
import hashlib
import time
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
        print(f"📚 DEBUG: DocumentSearchTool - Initializing for folder: {folder_path}")
        self.folder_path = folder_path
        self.indexed_documents = {}
        
        # Initialize vector store with error handling
        print("🔧 DEBUG: DocumentSearchTool - Checking vector store configuration...")
        disable_vector_store = os.getenv('DISABLE_VECTOR_STORE', 'false').lower() == 'true'
        
        if disable_vector_store:
            print("⚠️ DEBUG: Vector store disabled by environment variable")
            logger.info("Vector store disabled by environment variable")
            self.vector_store = None
            self.vector_store_enabled = False
        else:
            try:
                print("🔧 DEBUG: DocumentSearchTool - Creating vector store...")
                vector_store_name = folder_path.replace('/', '_').replace('\\', '_')
                vector_store_path = f"vector_stores/{vector_store_name}"
                self.vector_store = VectorStore(vector_store_path=vector_store_path)
                self.vector_store_enabled = True
                print("✅ DEBUG: DocumentSearchTool - Vector store created")
            except Exception as e:
                print(f"❌ DEBUG: DocumentSearchTool - Vector store failed: {str(e)}")
                logger.error(f"Failed to initialize vector store: {str(e)}")
                self.vector_store = None
                self.vector_store_enabled = False
        
        print("📚 DEBUG: DocumentSearchTool - Starting document indexing...")
        self.index_documents()
        print("✅ DEBUG: DocumentSearchTool - Initialization complete")
    
    def _calculate_folder_hash(self) -> str:
        """Calculate hash of all files in folder to detect changes"""
        hash_md5 = hashlib.md5()
        
        if not os.path.exists(self.folder_path):
            return hash_md5.hexdigest()
            
        # Get all PDF and Excel files sorted by name for consistent hashing
        files = []
        for filename in sorted(os.listdir(self.folder_path)):
            if filename.lower().endswith(('.pdf', '.xlsx', '.xls')):
                file_path = os.path.join(self.folder_path, filename)
                if os.path.isfile(file_path):
                    files.append((filename, os.path.getmtime(file_path), os.path.getsize(file_path)))
        
        # Hash the file metadata (name, modification time, size)
        for filename, mtime, size in files:
            hash_md5.update(f"{filename}:{mtime}:{size}".encode())
        
        return hash_md5.hexdigest()
    
    def _get_hash_file_path(self) -> str:
        """Get consistent path for hash file"""
        hash_dir = 'vector_stores'
        os.makedirs(hash_dir, exist_ok=True)
        safe_folder_name = self.folder_path.replace('/', '_').replace('\\', '_')
        return os.path.join(hash_dir, f'{safe_folder_name}_hash.json')
    
    def _load_folder_hash(self) -> Optional[str]:
        """Load stored hash from file"""
        hash_file = self._get_hash_file_path()
        if os.path.exists(hash_file):
            try:
                with open(hash_file, 'r') as f:
                    data = json.load(f)
                    hash_value = data.get('hash')
                    print(f"📂 DEBUG: Loaded hash from {hash_file}: {hash_value[:8] if hash_value else 'None'}...")
                    return hash_value
            except Exception as e:
                logger.warning(f"Could not load folder hash: {e}")
        else:
            print(f"📂 DEBUG: No hash file found at {hash_file}")
        return None
    
    def _save_folder_hash(self, folder_hash: str) -> None:
        """Save folder hash to file"""
        hash_file = self._get_hash_file_path()
        try:
            with open(hash_file, 'w') as f:
                json.dump({
                    'hash': folder_hash,
                    'timestamp': time.time(),
                    'folder_path': self.folder_path,
                    'created_at': time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
            print(f"💾 DEBUG: Saved hash to {hash_file}: {folder_hash[:8]}...")
        except Exception as e:
            logger.warning(f"Could not save folder hash: {e}")
    
    def _documents_changed(self) -> bool:
        """Check if documents have changed since last indexing"""
        current_hash = self._calculate_folder_hash()
        stored_hash = self._load_folder_hash()
        
        if stored_hash is None:
            print(f"📚 DEBUG: No stored hash found, will index documents")
            return True
            
        if current_hash != stored_hash:
            print(f"📚 DEBUG: Document changes detected (hash mismatch)")
            return True
            
        print(f"📚 DEBUG: No document changes detected, will skip indexing")
        return False
    
    def _get_backup_file_path(self) -> str:
        """Get path for backup file"""
        backup_dir = "vector_stores/backups"
        os.makedirs(backup_dir, exist_ok=True)
        safe_folder_name = self.folder_path.replace('/', '_').replace('\\', '_')
        return os.path.join(backup_dir, f"{safe_folder_name}_backup.json")
    
    def _save_backup_state(self) -> None:
        """Save document state to backup file"""
        try:
            backup_data = {
                "timestamp": time.time(),
                "folder_path": self.folder_path,
                "folder_hash": self._calculate_folder_hash(),
                "indexed_documents": {},
                "total_documents": len(self.indexed_documents),
                "vector_store_enabled": self.vector_store_enabled,
                "metadata": {
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "1.0"
                }
            }
            
            # Save document content and metadata (but not full content to save space)
            for filename, doc_data in self.indexed_documents.items():
                backup_data["indexed_documents"][filename] = {
                    "path": doc_data.get("path", ""),
                    "size": doc_data.get("size", 0),
                    "type": doc_data.get("type", "unknown"),
                    "content_preview": doc_data.get("content", "")[:500] + "..." if len(doc_data.get("content", "")) > 500 else doc_data.get("content", ""),
                    "content_length": len(doc_data.get("content", "")),
                    "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            
            backup_file = self._get_backup_file_path()
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
                
            print(f"💾 DEBUG: Saved backup state to {backup_file}")
            logger.info(f"Document state backed up to {backup_file}")
            
        except Exception as e:
            logger.warning(f"Could not save backup state: {e}")
    
    def _load_backup_state(self) -> Optional[Dict[str, Any]]:
        """Load document state from backup file"""
        try:
            backup_file = self._get_backup_file_path()
            if os.path.exists(backup_file):
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                    
                print(f"📂 DEBUG: Loaded backup state from {backup_file}")
                logger.info(f"Backup state loaded from {backup_file}")
                return backup_data
        except Exception as e:
            logger.warning(f"Could not load backup state: {e}")
        return None
    
    def _validate_backup_state(self, backup_data: Dict[str, Any]) -> bool:
        """Validate if backup state is still valid"""
        try:
            if not backup_data:
                return False
                
            # Check if folder hash matches
            stored_hash = backup_data.get("folder_hash", "")
            current_hash = self._calculate_folder_hash()
            
            if stored_hash != current_hash:
                print(f"📂 DEBUG: Backup state invalid - hash mismatch")
                return False
                
            # Check if backup is not too old (24 hours)
            backup_timestamp = backup_data.get("timestamp", 0)
            if time.time() - backup_timestamp > 24 * 3600:
                print(f"📂 DEBUG: Backup state too old ({time.time() - backup_timestamp:.0f}s)")
                return False
                
            print(f"📂 DEBUG: Backup state is valid")
            return True
            
        except Exception as e:
            logger.warning(f"Error validating backup state: {e}")
            return False
    
    def _restore_from_backup(self) -> bool:
        """Restore document state from backup if available and valid"""
        try:
            backup_data = self._load_backup_state()
            if not backup_data or not self._validate_backup_state(backup_data):
                return False
                
            # Restore indexed documents (minimal version for emergency)
            restored_docs = backup_data.get("indexed_documents", {})
            self.indexed_documents = {}
            
            for filename, doc_info in restored_docs.items():
                # For emergency restore, we only keep metadata
                # Full content would need to be re-extracted if needed
                self.indexed_documents[filename] = {
                    "content": f"[BACKUP RESTORE] Document: {filename} (Size: {doc_info.get('size', 0)} bytes)",
                    "path": doc_info.get("path", ""),
                    "size": doc_info.get("size", 0),
                    "type": doc_info.get("type", "unknown"),
                    "restored_from_backup": True,
                    "backup_content_preview": doc_info.get("content_preview", "")
                }
            
            print(f"🔄 DEBUG: Restored {len(self.indexed_documents)} documents from backup")
            logger.info(f"Successfully restored {len(self.indexed_documents)} documents from backup")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False
    
    def index_documents(self) -> None:
        """Index all PDF and Excel documents in the folder"""
        if not os.path.exists(self.folder_path):
            logger.warning(f"Folder path does not exist: {self.folder_path}")
            return
        
        # Check if documents have changed
        if not self._documents_changed():
            print(f"📚 DEBUG: No document changes detected")
            
            # If we have indexed documents in memory, we're good
            if self.indexed_documents:
                print(f"📚 DEBUG: Already have {len(self.indexed_documents)} documents indexed, skipping")
                return
            
            # If no indexed documents but vector store has them, load basic info
            if self.vector_store_enabled and self.vector_store:
                stats = self.vector_store.get_stats()
                if stats["total_documents"] > 0:
                    print(f"📚 DEBUG: Vector store has {stats['total_documents']} documents, using that")
                    # Create minimal indexed_documents for consistency
                    for i in range(stats["total_documents"]):
                        self.indexed_documents[f"cached_doc_{i}"] = {
                            "content": "[Loaded from vector store]",
                            "path": "cached",
                            "size": 0,
                            "type": "cached"
                        }
                    return
            
            # Try to restore from backup as last resort
            if self._restore_from_backup():
                print(f"📚 DEBUG: Restored from backup, indexing complete")
                return
            
            print(f"📚 DEBUG: No cached data found, will re-index documents")
        
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
            
            # CRITICAL: Save state only after everything is complete
            print("💾 DEBUG: Saving indexing state...")
            
            # Save the current folder hash after successful indexing
            current_hash = self._calculate_folder_hash()
            self._save_folder_hash(current_hash)
            print(f"📚 DEBUG: Saved folder hash: {current_hash[:8]}...")
            
            # Save backup state for emergency recovery
            try:
                self._save_backup_state()
                print("💾 DEBUG: Saved backup state")
            except Exception as e:
                logger.warning(f"Backup save failed: {e}")
                
            print("✅ DEBUG: Document indexing completed successfully")
            
        except Exception as e:
            logger.error(f"Error indexing documents: {str(e)}")
            print(f"❌ DEBUG: Indexing failed: {str(e)}")
    
    def _add_to_vector_store(self) -> None:
        """Add documents to vector store with chunking"""
        try:
            if not self.indexed_documents:
                return
            
            # Get vector store stats
            stats = self.vector_store.get_stats()
            existing_docs = stats["total_documents"]
            
            print(f"🔍 DEBUG: Vector store has {existing_docs} documents, we have {len(self.indexed_documents)} indexed")
            
            # If vector store already has the same or more documents, skip
            if existing_docs >= len(self.indexed_documents):
                logger.info(f"Vector store already contains {existing_docs} documents, skipping re-indexing")
                return
            
            # Only clear if we actually need to re-index
            if existing_docs > 0:
                logger.info("Clearing existing vector store for re-indexing...")
                self.vector_store.clear()
            else:
                logger.info("Adding documents to empty vector store...")
            
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