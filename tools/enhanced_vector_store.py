"""
Enhanced Vector Store for Food Service 2025
Robust document processing with fallback mechanisms
"""

import os
import json
import logging
import hashlib
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from openai_client import get_openai_client
from exceptions import VectorStoreError, DocumentError

logger = logging.getLogger(__name__)

class EnhancedVectorStore:
    """Enhanced vector store with robust document processing"""
    
    def __init__(self, store_path: str, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize enhanced vector store
        
        Args:
            store_path: Path to store vector data
            embedding_model: SentenceTransformer model name
        """
        self.store_path = store_path
        self.embedding_model_name = embedding_model
        self.dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # Create directories
        os.makedirs(store_path, exist_ok=True)
        
        # Initialize components
        self.embedding_model = None
        self.faiss_index = None
        self.documents = []
        self.metadata = []
        
        # File paths
        self.index_path = os.path.join(store_path, "faiss_index.bin")
        self.metadata_path = os.path.join(store_path, "metadata.json")
        self.documents_path = os.path.join(store_path, "documents.json")
        
        # Initialize with error handling
        self._initialize_safely()
    
    def _initialize_safely(self):
        """Initialize components with comprehensive error handling"""
        try:
            print(f"🔧 DEBUG: Initializing Enhanced Vector Store at {self.store_path}")
            
            # Try to load sentence transformer
            try:
                print(f"📚 DEBUG: Loading embedding model: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                print("✅ DEBUG: Embedding model loaded successfully")
            except Exception as e:
                print(f"⚠️ DEBUG: Failed to load embedding model: {str(e)}")
                print("🔄 DEBUG: Will use OpenAI embeddings as fallback")
                self.embedding_model = None
            
            # Initialize FAISS index
            self.faiss_index = faiss.IndexFlatIP(self.dimension)
            print("✅ DEBUG: FAISS index initialized")
            
            # Try to load existing data
            if self._load_existing_data():
                print("✅ DEBUG: Loaded existing vector store data")
            else:
                print("ℹ️ DEBUG: No existing data found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error initializing Enhanced Vector Store: {str(e)}")
            print(f"❌ DEBUG: Vector store initialization failed: {str(e)}")
            # Don't raise, we'll handle this gracefully
    
    def _load_existing_data(self) -> bool:
        """Load existing vector store data"""
        try:
            # Load FAISS index
            if os.path.exists(self.index_path):
                self.faiss_index = faiss.read_index(self.index_path)
                print(f"📚 DEBUG: Loaded FAISS index with {self.faiss_index.ntotal} vectors")
            
            # Load metadata
            if os.path.exists(self.metadata_path):
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                print(f"📋 DEBUG: Loaded {len(self.metadata)} metadata entries")
            
            # Load documents
            if os.path.exists(self.documents_path):
                with open(self.documents_path, 'r', encoding='utf-8') as f:
                    self.documents = json.load(f)
                print(f"📄 DEBUG: Loaded {len(self.documents)} document chunks")
            
            return len(self.documents) > 0
            
        except Exception as e:
            logger.warning(f"Could not load existing data: {str(e)}")
            return False
    
    def _save_data(self):
        """Save vector store data to disk"""
        try:
            # Save FAISS index
            if self.faiss_index and self.faiss_index.ntotal > 0:
                faiss.write_index(self.faiss_index, self.index_path)
            
            # Save metadata
            with open(self.metadata_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
            
            # Save documents
            with open(self.documents_path, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)
            
            print(f"💾 DEBUG: Saved vector store data ({len(self.documents)} documents)")
            
        except Exception as e:
            logger.error(f"Error saving vector store data: {str(e)}")
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings using available method"""
        if not texts:
            return np.array([]).reshape(0, self.dimension)
        
        try:
            # Try SentenceTransformer first
            if self.embedding_model:
                print(f"🔧 DEBUG: Generating {len(texts)} embeddings with SentenceTransformer")
                embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
                print("✅ DEBUG: SentenceTransformer embeddings generated")
                return embeddings
            
            # Fallback to OpenAI embeddings
            print(f"🔧 DEBUG: Generating {len(texts)} embeddings with OpenAI")
            client = get_openai_client()
            
            # Process in batches to avoid token limits
            batch_size = 50
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = client.get_embeddings(batch, model="text-embedding-3-small")
                all_embeddings.extend(response["embeddings"])
            
            embeddings = np.array(all_embeddings)
            print("✅ DEBUG: OpenAI embeddings generated")
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            print(f"❌ DEBUG: Embedding generation failed: {str(e)}")
            # Return zero embeddings as last resort
            return np.zeros((len(texts), self.dimension))
    
    def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]]):
        """Add documents to the vector store"""
        if not documents or len(documents) != len(metadatas):
            return
        
        try:
            print(f"📚 DEBUG: Adding {len(documents)} documents to vector store")
            
            # Generate embeddings
            embeddings = self._get_embeddings(documents)
            
            if embeddings.shape[0] == 0:
                print("⚠️ DEBUG: No embeddings generated, skipping document addition")
                return
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add to FAISS index
            self.faiss_index.add(embeddings)
            
            # Store documents and metadata
            start_idx = len(self.documents)
            self.documents.extend(documents)
            self.metadata.extend(metadatas)
            
            # Save to disk
            self._save_data()
            
            print(f"✅ DEBUG: Added {len(documents)} documents (total: {len(self.documents)})")
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            print(f"❌ DEBUG: Failed to add documents: {str(e)}")
    
    def search(self, query: str, k: int = 5, similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if not query.strip():
            return []
        
        try:
            print(f"🔍 DEBUG: Searching for: '{query[:50]}...' (k={k})")
            
            # Check if we have data
            if not self.documents or self.faiss_index.ntotal == 0:
                print("⚠️ DEBUG: No documents in vector store")
                return []
            
            # Generate query embedding
            query_embeddings = self._get_embeddings([query])
            
            if query_embeddings.shape[0] == 0:
                print("⚠️ DEBUG: Could not generate query embedding")
                return []
            
            # Normalize query embedding
            faiss.normalize_L2(query_embeddings)
            
            # Search in FAISS
            search_k = min(k * 2, self.faiss_index.ntotal)  # Get more candidates
            scores, indices = self.faiss_index.search(query_embeddings, search_k)
            
            # Process results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and score >= similarity_threshold:
                    results.append({
                        'content': self.documents[idx],
                        'metadata': self.metadata[idx],
                        'similarity_score': float(score)
                    })
            
            # Sort by similarity and limit results
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = results[:k]
            
            print(f"✅ DEBUG: Found {len(results)} relevant documents")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            print(f"❌ DEBUG: Search failed: {str(e)}")
            return []
    
    def clear(self):
        """Clear all data from vector store"""
        try:
            self.faiss_index = faiss.IndexFlatIP(self.dimension)
            self.documents = []
            self.metadata = []
            
            # Remove files
            for file_path in [self.index_path, self.metadata_path, self.documents_path]:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            print("🗑️ DEBUG: Vector store cleared")
            
        except Exception as e:
            logger.error(f"Error clearing vector store: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            'total_documents': len(self.documents),
            'total_vectors': self.faiss_index.ntotal if self.faiss_index else 0,
            'embedding_model': self.embedding_model_name,
            'dimension': self.dimension,
            'store_path': self.store_path,
            'has_sentence_transformer': self.embedding_model is not None
        }