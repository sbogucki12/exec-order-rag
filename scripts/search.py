"""
Search script for RAG application.
Performs vector search on embedded documents.
"""

import os
import argparse
import logging
import json
import sys

# Import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.embeddings import EmbeddingsGenerator
from src.vector_store import LocalVectorStore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to run the search process."""
    parser = argparse.ArgumentParser(description='Search for similar documents')
    parser.add_argument('--index', '-i', required=True, help='Vector store file path')
    parser.add_argument('--query', '-q', required=True, help='Search query')
    parser.add_argument('--top', '-k', type=int, default=3, help='Number of results to return')
    parser.add_argument('--threshold', '-t', type=float, help='Similarity score threshold')
    parser.add_argument('--model', '-m', default="all-MiniLM-L6-v2", help='Embedding model name')
    
    args = parser.parse_args()
    
    try:
        # Initialize embeddings generator
        embeddings_generator = EmbeddingsGenerator(model_name=args.model)
        
        # Initialize vector store
        vector_store = LocalVectorStore()
        
        # Load vector store from file
        if not vector_store.load(args.index):
            logger.error(f"Failed to load vector store from {args.index}")
            sys.exit(1)
        
        # Generate embedding for query
        query_embedding = embeddings_generator.generate_embeddings([args.query])[0]
        
        # Search for similar documents
        results = vector_store.similarity_search(
            query_embedding=query_embedding,
            k=args.top,
            score_threshold=args.threshold
        )
        
        # Print results
        print(f"\nSearch Query: {args.query}")
        print(f"Found {len(results)} relevant documents:\n")
        
        for i, result in enumerate(results):
            print(f"Result {i+1} [Score: {result['similarity_score']:.4f}]")
            print(f"Content: {result['content'][:200]}..." if len(result['content']) > 200 else f"Content: {result['content']}")
            
            # Print metadata if available
            if 'metadata' in result and result['metadata']:
                print("Metadata:")
                for key, value in result['metadata'].items():
                    if key != 'chunk_id' and key != 'chunk_index':
                        print(f"  {key}: {value}")
            
            print("\n" + "-" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"Error in search process: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()