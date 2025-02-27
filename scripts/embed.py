"""
Embedding generation script for RAG application.
Processes document chunks and generates embeddings.
"""

import os
import argparse
import logging
import sys

# Import our embeddings generator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.embeddings import EmbeddingsGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to run the embedding generation process."""
    parser = argparse.ArgumentParser(description='Generate embeddings for document chunks')
    parser.add_argument('--input', '-i', required=True, help='Input JSON file with document chunks')
    parser.add_argument('--output', '-o', required=True, help='Output JSON file path')
    parser.add_argument('--model', '-m', default="all-MiniLM-L6-v2", help='Embedding model name')
    parser.add_argument('--cloud', action='store_true', help='Use Azure OpenAI instead of local model')
    parser.add_argument('--cache-dir', help='Cache directory for embeddings')
    
    args = parser.parse_args()
    
    try:
        # Initialize embeddings generator
        generator = EmbeddingsGenerator(
            model_name=args.model,
            use_local=not args.cloud,
            cache_dir=args.cache_dir
        )
        
        # Load document chunks
        with open(args.input, 'r') as f:
            import json
            chunks = json.load(f)
        logger.info(f"Loaded {len(chunks)} chunks from {args.input}")
        
        # Generate embeddings
        chunks_with_embeddings = generator.process_document_chunks(chunks)
        
        # Save processed chunks
        generator.save_processed_chunks(chunks_with_embeddings, args.output)
        
    except Exception as e:
        logger.error(f"Error in embedding generation: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()