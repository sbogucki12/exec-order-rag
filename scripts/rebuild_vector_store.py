"""
Script to rebuild the vector store from documents in the data directory.
This will clear the existing vector store and recreate it.
"""
import os
import sys
import shutil
import logging
from pathlib import Path
import json

# Add the parent directory to sys.path to enable imports from src
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from src.document_processor import DocumentProcessor
from src.vector_store import LocalVectorStore
from src.embeddings import EmbeddingsGenerator
from config import VECTOR_DB_PATH, EMBEDDING_MODEL_NAME, CHUNK_SIZE, CHUNK_OVERLAP

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_vector_store(vector_store_path):
    """Clear the existing vector store."""
    try:
        if os.path.isfile(vector_store_path):
            logger.info(f"Removing existing vector store file: {vector_store_path}")
            os.remove(vector_store_path)
        elif os.path.isdir(vector_store_path):
            logger.info(f"Removing existing vector store directory: {vector_store_path}")
            shutil.rmtree(vector_store_path)
        
        # Create parent directory if it doesn't exist
        parent_dir = os.path.dirname(vector_store_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
            
        logger.info("Existing vector store cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Error clearing vector store: {str(e)}")
        return False

def process_documents(data_dir, document_processor):
    """
    Process all documents in the data directory.
    
    Args:
        data_dir: Path to the directory containing documents
        document_processor: DocumentProcessor instance
        
    Returns:
        List of processed document chunks
    """
    all_chunks = []
    processed_files = []
    failed_files = []
    
    # Check if data directory exists
    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found: {data_dir}")
        return all_chunks, processed_files, failed_files
    
    # Method 1: Try to use process_from_directory if available
    if hasattr(document_processor, 'process_from_directory'):
        try:
            logger.info(f"Processing all documents in {data_dir} using process_from_directory")
            all_chunks = document_processor.process_from_directory(data_dir)
            logger.info(f"Successfully processed directory with {len(all_chunks)} chunks")
            return all_chunks, [data_dir], []
        except Exception as e:
            logger.error(f"Error processing directory: {str(e)}")
            # Fall back to processing individual files
    
    # Method 2: Process files individually
    # Get all files in the data directory
    files = []
    for root, _, filenames in os.walk(data_dir):
        for filename in filenames:
            # Filter for document file types
            if filename.lower().endswith(('.pdf', '.txt', '.docx', '.md', '.html')):
                files.append(os.path.join(root, filename))
    
    logger.info(f"Found {len(files)} documents in {data_dir}")
    
    # Process each file
    for file_path in files:
        try:
            logger.info(f"Processing: {file_path}")
            
            # Load the document first
            loaded_documents = document_processor.load_document(file_path)
            logger.info(f"Loaded {len(loaded_documents)} document(s) from {file_path}")
            
            # Process the loaded documents
            chunks = document_processor.process_documents(loaded_documents)
            
            all_chunks.extend(chunks)
            processed_files.append(file_path)
            logger.info(f"Successfully processed {file_path} - {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            failed_files.append(file_path)
    
    return all_chunks, processed_files, failed_files

def create_vector_store(chunks, vector_store_path, embeddings_generator):
    """
    Create a new vector store from document chunks.
    
    Args:
        chunks: List of document chunks
        vector_store_path: Path to save the vector store
        embeddings_generator: EmbeddingsGenerator instance
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Initialize vector store
        vector_store = LocalVectorStore()
        
        # Add documents to vector store
        logger.info(f"Adding {len(chunks)} chunks to vector store")
        
        # Extract texts and metadata
        texts = [chunk["content"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        
        # Generate embeddings
        embeddings = embeddings_generator.generate_embeddings(texts)
        
        # Add to vector store
        for i, (text, metadata, embedding) in enumerate(zip(texts, metadatas, embeddings)):
            vector_store.add_document(
                document_id=str(i),
                content=text,
                metadata=metadata,
                embedding=embedding
            )
        
        # Save vector store
        logger.info(f"Saving vector store to {vector_store_path}")
        vector_store.save(vector_store_path)
        
        return True
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        return False

def main():
    """Main function to rebuild the vector store."""
    # Get command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Rebuild vector store from documents")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory containing documents")
    parser.add_argument("--vector-store-path", type=str, default=VECTOR_DB_PATH, help="Path to save vector store")
    parser.add_argument("--model-name", type=str, default="all-MiniLM-L6-v2", help="Embedding model name")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="Chunk size for document processing")
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP, help="Chunk overlap for document processing")
    
    args = parser.parse_args()
    
    logger.info(f"Starting vector store rebuild process")
    logger.info(f"Data directory: {args.data_dir}")
    logger.info(f"Vector store path: {args.vector_store_path}")
    logger.info(f"Embedding model: {args.model_name}")
    
    # Clear existing vector store
    if not clear_vector_store(args.vector_store_path):
        logger.error("Failed to clear vector store. Aborting.")
        return
    
    # Initialize components
    doc_processor = DocumentProcessor(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap
    )
    
    embeddings_generator = EmbeddingsGenerator(model_name=args.model_name)
    
    # Process documents
    chunks, processed_files, failed_files = process_documents(args.data_dir, doc_processor)
    
    if not chunks:
        logger.error("No document chunks were generated. Aborting.")
        return
    
    # Create vector store
    if create_vector_store(chunks, args.vector_store_path, embeddings_generator):
        logger.info("Vector store rebuilt successfully!")
        logger.info(f"Processed {len(processed_files)} files, {len(failed_files)} failed")
        logger.info(f"Total chunks added to vector store: {len(chunks)}")
    else:
        logger.error("Failed to rebuild vector store")
        
    # Output summary
    if failed_files:
        logger.warning("The following files failed to process:")
        for file in failed_files:
            logger.warning(f" - {file}")

if __name__ == "__main__":
    main()