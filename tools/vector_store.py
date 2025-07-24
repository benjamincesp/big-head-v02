"""
Vector Store for Food Service 2025
Implements FAISS-based vector storage with sentence transformers
"""

import os
import pickle
import logging
import numpy as np
import faiss
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
import hashlib

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", vector_store_path: str = "vector_stores"):
        """
        Initialize vector store with sentence transformer model
        
        Args:
            model_name: Sentence transformer model name
            vector_store_path: Path to store vector indices
        """
        self.model_name = model_name
        self.vector_store_path = vector_store_path
        self.model = None
        self.index = None
        self.documents = []
        self.metadatas = []
        
        # Create vector store directory
        os.makedirs(vector_store_path, exist_ok=True)
        
        # Load or initialize
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """Load existing vector store or initialize new one"""
        try:
            # Load sentence transformer model
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            
            # Try to load existing index
            index_path = os.path.join(self.vector_store_path, "faiss_index.bin")
            docs_path = os.path.join(self.vector_store_path, "documents.pkl")
            meta_path = os.path.join(self.vector_store_path, "metadata.pkl")
            
            if os.path.exists(index_path) and os.path.exists(docs_path):
                logger.info("Loading existing vector store...")
                self.index = faiss.read_index(index_path)
                
                with open(docs_path, 'rb') as f:
                    self.documents = pickle.load(f)
                
                with open(meta_path, 'rb') as f:
                    self.metadatas = pickle.load(f)
                
                logger.info(f"Loaded vector store with {len(self.documents)} documents")
            else:
                logger.info("Initializing new vector store...")
                # Create empty FAISS index
                dimension = self.model.get_sentence_embedding_dimension()
                self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
                
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise
    
    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]]) -> None:
        """
        Add documents to vector store in batches
        
        Args:
            texts: List of text documents
            metadatas: List of metadata dicts for each document
        """
        if len(texts) != len(metadatas):
            raise ValueError("Number of texts and metadatas must match")
        
        try:
            logger.info(f"Adding {len(texts)} documents to vector store in batches...")
            
            # Process in batches to avoid memory issues
            batch_size = 50  # Process 50 chunks at a time
            total_processed = 0
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                
                try:
                    # Generate embeddings for batch
                    logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1} ({len(batch_texts)} items)")
                    embeddings = self.model.encode(batch_texts, normalize_embeddings=True, show_progress_bar=False)
                    
                    # Add to FAISS index
                    self.index.add(embeddings.astype('float32'))
                    
                    # Store documents and metadata
                    self.documents.extend(batch_texts)
                    self.metadatas.extend(batch_metadatas)
                    
                    total_processed += len(batch_texts)
                    logger.info(f"Processed {total_processed}/{len(texts)} documents")
                    
                except Exception as batch_error:
                    logger.error(f"Error processing batch {i//batch_size + 1}: {str(batch_error)}")
                    # Continue with next batch instead of failing completely
                    continue
            
            # Save to disk
            self._save_to_disk()
            
            logger.info(f"Successfully added {total_processed} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            # Don't re-raise, just log the error to prevent startup failure
            logger.warning("Vector store initialization failed, falling back to keyword search")
    
    def search(self, query: str, k: int = 5, score_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Search for similar documents
        
        Args:
            query: Search query
            k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of results with documents and metadata
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        try:
            # Generate query embedding
            query_embedding = self.model.encode([query], normalize_embeddings=True)
            
            # Search in FAISS index
            scores, indices = self.index.search(query_embedding.astype('float32'), k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and score >= score_threshold:  # Valid result and above threshold
                    results.append({
                        'document': self.documents[idx],
                        'metadata': self.metadatas[idx],
                        'score': float(score),
                        'index': int(idx)
                    })
            
            logger.info(f"Found {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []
    
    def _save_to_disk(self) -> None:
        """Save vector store to disk"""
        try:
            index_path = os.path.join(self.vector_store_path, "faiss_index.bin")
            docs_path = os.path.join(self.vector_store_path, "documents.pkl")
            meta_path = os.path.join(self.vector_store_path, "metadata.pkl")
            
            # Save FAISS index
            faiss.write_index(self.index, index_path)
            
            # Save documents and metadata
            with open(docs_path, 'wb') as f:
                pickle.dump(self.documents, f)
            
            with open(meta_path, 'wb') as f:
                pickle.dump(self.metadatas, f)
                
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
            raise
    
    def clear(self) -> None:
        """Clear all documents from vector store"""
        try:
            # Reset index
            dimension = self.model.get_sentence_embedding_dimension()
            self.index = faiss.IndexFlatIP(dimension)
            
            # Clear data
            self.documents = []
            self.metadatas = []
            
            # Save empty state
            self._save_to_disk()
            
            logger.info("Vector store cleared")
            
        except Exception as e:
            logger.error(f"Error clearing vector store: {str(e)}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        return {
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal if self.index else 0,
            "model_name": self.model_name,
            "dimension": self.model.get_sentence_embedding_dimension() if self.model else 0,
            "vector_store_path": self.vector_store_path
        }
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            
            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence ending
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks