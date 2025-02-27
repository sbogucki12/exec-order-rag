"""
Embeddings generator for RAG application.
Handles creating vector embeddings for document chunks.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Union
import numpy as np

# For local embeddings
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingsGenerator:
    """Generates embeddings for document chunks using various embedding models."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        use_local: bool = True,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the embeddings generator.
        
        Args:
            model_name: Name of the embedding model to use
            use_local: Whether to use a local model or Azure OpenAI
            cache_dir: Optional directory to cache embeddings
        """
        self.model_name = model_name
        self.use_local = use_local
        self.cache_dir = cache_dir
        
        if use_local:
            logger.info(f"Loading local embedding model: {model_name}")
            try:
                self.model = SentenceTransformer(model_name)
                logger.info("Local embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading embedding model: {str(e)}")
                raise
        else:
            # We'll implement Azure OpenAI embeddings later
            logger.info("Using Azure OpenAI for embeddings (not implemented yet)")
            self.model = None
            
        # Create cache directory if it doesn't exist
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def generate_embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            logger.warning("Empty list provided for embedding generation")
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            if self.use_local:
                # Use local SentenceTransformer model
                embeddings = self.model.encode(texts)
                # Convert numpy arrays to lists for JSON serialization
                embeddings_list = embeddings.tolist()
                logger.info(f"Successfully generated {len(embeddings_list)} embeddings")
                return embeddings_list
            else:
                # This will be implemented later with Azure OpenAI
                logger.warning("Azure OpenAI embeddings not implemented yet")
                return [[0.0] * 384] * len(texts)  # Placeholder
        
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def process_document_chunks(
        self,
        chunks: List[Dict[str, Any]],
        content_field: str = "content"
    ) -> List[Dict[str, Any]]:
        """
        Process document chunks by adding embeddings.
        
        Args:
            chunks: List of document chunks
            content_field: Field name containing the text to embed
            
        Returns:
            List of document chunks with embeddings
        """
        logger.info(f"Processing embeddings for {len(chunks)} chunks")
        
        # Extract texts from chunks
        texts = [chunk[content_field] for chunk in chunks if content_field in chunk]
        
        if len(texts) != len(chunks):
            logger.warning(f"Some chunks ({len(chunks) - len(texts)}) are missing the '{content_field}' field")
        
        # Generate embeddings
        embeddings = self.generate_embeddings(texts)
        
        # Add embeddings to chunks
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            if i < len(embeddings):
                chunk_with_embedding = chunk.copy()
                chunk_with_embedding["embedding"] = embeddings[i]
                processed_chunks.append(chunk_with_embedding)
        
        logger.info(f"Successfully processed embeddings for {len(processed_chunks)} chunks")
        return processed_chunks
    
    def save_processed_chunks(
        self,
        chunks: List[Dict[str, Any]],
        output_path: str
    ) -> bool:
        """
        Save processed chunks to a file.
        
        Args:
            chunks: List of document chunks with embeddings
            output_path: Path to save the processed chunks
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, 'w') as f:
                json.dump(chunks, f)
            logger.info(f"Saved {len(chunks)} processed chunks to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving processed chunks: {str(e)}")
            return False
    
    def load_processed_chunks(
        self,
        input_path: str
    ) -> List[Dict[str, Any]]:
        """
        Load processed chunks from a file.
        
        Args:
            input_path: Path to load the processed chunks from
            
        Returns:
            List of document chunks with embeddings
        """
        try:
            with open(input_path, 'r') as f:
                chunks = json.load(f)
            logger.info(f"Loaded {len(chunks)} processed chunks from {input_path}")
            return chunks
        except Exception as e:
            logger.error(f"Error loading processed chunks: {str(e)}")
            return []

# Example usage function
def generate_embeddings_for_file(input_path: str, output_path: str, use_local: bool = True):
    """
    Generate embeddings for chunks in a file.
    
    Args:
        input_path: Path to input JSON file with document chunks
        output_path: Path to save the processed chunks with embeddings
        use_local: Whether to use a local model or Azure OpenAI
    """
    # Load document chunks
    try:
        with open(input_path, 'r') as f:
            chunks = json.load(f)
        logger.info(f"Loaded {len(chunks)} chunks from {input_path}")
    except Exception as e:
        logger.error(f"Error loading chunks: {str(e)}")
        return False
    
    # Initialize embeddings generator
    generator = EmbeddingsGenerator(use_local=use_local)
    
    # Generate embeddings
    chunks_with_embeddings = generator.process_document_chunks(chunks)
    
    # Save processed chunks
    return generator.save_processed_chunks(chunks_with_embeddings, output_path)