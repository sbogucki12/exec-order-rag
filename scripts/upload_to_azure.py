"""
Upload script for Azure AI Search.
Uploads processed document chunks with embeddings to Azure AI Search.
"""

import os
import argparse
import logging
import json
import sys

# Import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.azure_search import AzureSearchVectorStore
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to upload documents to Azure AI Search."""
    parser = argparse.ArgumentParser(description='Upload documents to Azure AI Search')
    parser.add_argument('--input', '-i', required=True, help='Input file with embedded documents')
    parser.add_argument('--recreate-index', action='store_true', help='Recreate index if it exists')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for uploading')
    parser.add_argument('--dimension', type=int, default=384, help='Embedding dimension')
    
    args = parser.parse_args()
    
    # Validate Azure Search credentials
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_API_KEY:
        logger.error("Azure Search credentials not found in environment variables")
        logger.error("Please set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY")
        sys.exit(1)
    
    try:
        # Load embedded documents
        with open(args.input, 'r') as f:
            documents = json.load(f)
        logger.info(f"Loaded {len(documents)} documents from {args.input}")
        
        # Check if documents have embeddings
        if not documents or 'embedding' not in documents[0]:
            logger.error("Documents don't have embeddings. Please run embed.py first.")
            sys.exit(1)
        
        # Initialize Azure Search vector store
        vector_store = AzureSearchVectorStore(
            search_endpoint=AZURE_SEARCH_ENDPOINT,
            search_key=AZURE_SEARCH_API_KEY,
            index_name=AZURE_SEARCH_INDEX_NAME,
            embedding_dimension=args.dimension
        )
        
        # Create index if needed
        logger.info("Creating or validating search index...")
        if not vector_store.create_index(recreate=args.recreate_index):
            logger.error("Failed to create or validate search index")
            sys.exit(1)
        
        # Upload documents
        logger.info(f"Uploading {len(documents)} documents to Azure AI Search...")
        added_count = vector_store.add_documents(documents, batch_size=args.batch_size)
        
        if added_count > 0:
            logger.info(f"Successfully uploaded {added_count} documents to Azure AI Search")
        else:
            logger.error("Failed to upload documents to Azure AI Search")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Error uploading to Azure AI Search: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()