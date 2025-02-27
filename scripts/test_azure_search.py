"""
Test script for Azure AI Search integration.
Performs a test query against Azure AI Search.
"""

import os
import argparse
import logging
import sys

# Import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.azure_rag import AzureRAG
from src.embeddings import EmbeddingsGenerator
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to test Azure AI Search integration."""
    parser = argparse.ArgumentParser(description='Test Azure AI Search integration')
    parser.add_argument('--query', '-q', required=True, help='Query to test')
    parser.add_argument('--top', '-k', type=int, default=3, help='Number of results to return')
    
    args = parser.parse_args()
    
    # Validate Azure Search credentials
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_API_KEY or not AZURE_SEARCH_INDEX_NAME:
        logger.error("Azure Search credentials not found in environment variables")
        logger.error("Please set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, and AZURE_SEARCH_INDEX_NAME")
        sys.exit(1)
    
    try:
        # Initialize RAG system
        rag = AzureRAG(
            search_endpoint=AZURE_SEARCH_ENDPOINT,
            search_key=AZURE_SEARCH_API_KEY,
            index_name=AZURE_SEARCH_INDEX_NAME,
            top_k=args.top,
            use_local_embeddings=True
        )
        
        # Generate embeddings for query
        embeddings_generator = EmbeddingsGenerator(use_local=True)
        query_embedding = embeddings_generator.generate_embeddings([args.query])[0]
        
        # Test similarity search
        logger.info(f"Testing similarity search with query: {args.query}")
        logger.info(f"Generated query embedding of dimension {len(query_embedding)}")
        
        results = rag.retrieve(args.query)
        
        # Print results
        print(f"\nSearch Results for: {args.query}")
        print(f"Found {len(results)} relevant documents:\n")
        
        for i, result in enumerate(results):
            print(f"Result {i+1} [Score: {result['similarity_score']:.4f}]")
            
            # Print metadata if available
            metadata = result.get('metadata', {})
            if metadata:
                if isinstance(metadata, str):
                    # Try to parse JSON string
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except:
                        pass
                        
                if isinstance(metadata, dict):
                    print("Metadata:")
                    for key, value in metadata.items():
                        if key not in ('chunk_id', 'chunk_index'):
                            print(f"  {key}: {value}")
            
            # Print content
            content = result.get('content', '')
            print(f"Content: {content[:200]}..." if len(content) > 200 else f"Content: {content}")
            print("\n" + "-" * 80 + "\n")
        
        # Print the generated prompt
        print("\nGenerated Prompt for LLM:")
        print("-" * 80)
        prompt = rag.generate_prompt(args.query, results)
        print(prompt)
        
    except Exception as e:
        logger.error(f"Error testing Azure AI Search: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()