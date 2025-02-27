"""
Vector store for RAG application.
Implements a local vector store for testing.
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LocalVectorStore:
    """Simple in-memory vector store for testing RAG applications."""
    
    def __init__(
        self,
        embeddings_field: str = "embedding",
        content_field: str = "content",
        metadata_field: str = "metadata",
        persist_directory: Optional[str] = None
    ):
        """
        Initialize the local vector store.
        
        Args:
            embeddings_field: Field containing embeddings in documents
            content_field: Field containing text content in documents
            metadata_field: Field containing metadata in documents
            persist_directory: Directory to persist vector store data
        """
        self.embeddings_field = embeddings_field
        self.content_field = content_field
        self.metadata_field = metadata_field
        self.persist_directory = persist_directory
        
        # Initialize an empty vector store
        self.documents = []
        self.embeddings = []
        
        # Create persist directory if it doesn't exist
        if persist_directory and not os.path.exists(persist_directory):
            os.makedirs(persist_directory)
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of document dictionaries with embeddings
            
        Returns:
            Number of documents added
        """
        added_count = 0
        
        for doc in documents:
            if self.embeddings_field not in doc:
                logger.warning(f"Document missing embedding field: {self.embeddings_field}")
                continue
                
            if self.content_field not in doc:
                logger.warning(f"Document missing content field: {self.content_field}")
                continue
            
            # Convert embedding to numpy array for efficient similarity computation
            embedding = np.array(doc[self.embeddings_field])
            
            # Add to vector store
            self.documents.append(doc)
            self.embeddings.append(embedding)
            added_count += 1
        
        logger.info(f"Added {added_count} documents to vector store")
        return added_count
    
    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 4,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents by embedding.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            score_threshold: Minimum similarity score threshold
            
        Returns:
            List of similar documents with similarity scores
        """
        if not self.embeddings:
            logger.warning("Vector store is empty")
            return []
        
        # Convert query embedding to numpy array
        query_embedding_np = np.array(query_embedding)
        
        # Compute cosine similarity
        similarities = []
        for i, doc_embedding in enumerate(self.embeddings):
            # Normalize vectors for cosine similarity
            query_norm = np.linalg.norm(query_embedding_np)
            doc_norm = np.linalg.norm(doc_embedding)
            
            if query_norm > 0 and doc_norm > 0:
                # Cosine similarity = dot product of normalized vectors
                similarity = np.dot(query_embedding_np, doc_embedding) / (query_norm * doc_norm)
                similarities.append((i, float(similarity)))
        
        # Sort by similarity score (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Apply similarity threshold if specified
        if score_threshold is not None:
            similarities = [(i, score) for i, score in similarities if score >= score_threshold]
        
        # Get top-k results
        top_k = similarities[:k]
        
        # Create result list
        results = []
        for idx, score in top_k:
            doc = self.documents[idx].copy()
            # Add similarity score to results
            doc["similarity_score"] = score
            # Remove embedding to reduce response size
            if self.embeddings_field in doc:
                del doc[self.embeddings_field]
            results.append(doc)
        
        return results
    
    def save(self, filename: Optional[str] = None) -> bool:
        """
        Save the vector store to disk.
        
        Args:
            filename: Filename to save to (defaults to timestamp)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.persist_directory:
            logger.warning("No persist directory specified")
            return False
        
        if not filename:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"vector_store_{timestamp}.json"
        
        file_path = os.path.join(self.persist_directory, filename)
        
        try:
            # Prepare data for saving
            data = {
                "documents": self.documents,
                "metadata": {
                    "count": len(self.documents),
                    "created_at": datetime.now().isoformat(),
                    "embeddings_field": self.embeddings_field,
                    "content_field": self.content_field,
                    "metadata_field": self.metadata_field
                }
            }
            
            # Save to file
            with open(file_path, 'w') as f:
                json.dump(data, f)
            
            logger.info(f"Saved vector store with {len(self.documents)} documents to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
            return False
    
    def load(self, file_path: str) -> bool:
        """
        Load the vector store from disk.
        
        Args:
            file_path: Path to vector store file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load from file
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract documents
            documents = data.get("documents", [])
            
            # Clear existing data
            self.documents = []
            self.embeddings = []
            
            # Add documents
            self.add_documents(documents)
            
            logger.info(f"Loaded vector store with {len(self.documents)} documents from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False
    
    def get_document_by_id(self, doc_id: str, id_field: str = "id") -> Optional[Dict[str, Any]]:
        """
        Get a document by ID.
        
        Args:
            doc_id: Document ID to find
            id_field: Field containing the document ID
            
        Returns:
            Document if found, None otherwise
        """
        for doc in self.documents:
            if id_field in doc and doc[id_field] == doc_id:
                return doc
        return None

# Example usage function
def create_vector_store_from_file(input_path: str, output_dir: str):
    """
    Create a vector store from a file with embedded documents.
    
    Args:
        input_path: Path to input JSON file with embedded documents
        output_dir: Directory to save the vector store
    """
    # Load embedded documents
    try:
        with open(input_path, 'r') as f:
            documents = json.load(f)
        logger.info(f"Loaded {len(documents)} documents from {input_path}")
    except Exception as e:
        logger.error(f"Error loading documents: {str(e)}")
        return False
    
    # Initialize vector store
    vector_store = LocalVectorStore(persist_directory=output_dir)
    
    # Add documents
    vector_store.add_documents(documents)
    
    # Save vector store
    return vector_store.save()