"""
Index creation script for RAG application.
Creates a vector store from embedded documents.
"""

import os
import argparse
import logging
import sys

# Import our vector store
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.vector_store import LocalVectorStore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to create a vector store index."""
    parser = argparse.ArgumentParser(description='Create a vector store index')
    parser.add_argument('--input', '-i', required=True, help='Input file with embedded documents')
    parser.add_argument('--output', '-o', required=True, help='Output file for vector store')
    parser.add_argument('--embeddings-field', default='embedding', help='Field name for embeddings')
    parser.add_argument('--content-field', default='content', help='Field name for content')
    parser.add_argument('--metadata-field', default='metadata', help='Field name for metadata')
    
    args = parser.parse_args()
    
    try:
        # Load embedded documents
        import json
        with open(args.input, 'r') as f:
            documents = json.load(f)
        logger.info(f"Loaded {len(documents)} documents from {args.input}")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Initialize vector store
        vector_store = LocalVectorStore(
            embeddings_field=args.embeddings_field,
            content_field=args.content_field,
            metadata_field=args.metadata_field
        )
        
        # Add documents
        vector_store.add_documents(documents)
        
        # Save vector store
        with open(args.output, 'w') as f:
            data = {
                "documents": vector_store.documents,
                "metadata": {
                    "count": len(vector_store.documents),
                    "created_at": "now",
                    "embeddings_field": vector_store.embeddings_field,
                    "content_field": vector_store.content_field,
                    "metadata_field": vector_store.metadata_field
                }
            }
            json.dump(data, f)
        
        logger.info(f"Saved vector store with {len(vector_store.documents)} documents to {args.output}")
        
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()