"""
Simple Azure AI Search upload script.
Creates a basic index without vector search capabilities.
"""

import os
import argparse
import logging
import json
import sys
import time
from typing import List, Dict, Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchFieldDataType
)

# Import configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_basic_index(index_name: str, recreate: bool = False) -> bool:
    """
    Create a basic search index without vector search.
    
    Args:
        index_name: Name of the index to create
        recreate: Whether to recreate the index if it exists
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Create clients
        credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
        index_client = SearchIndexClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            credential=credential
        )
        
        # Check if index exists
        existing_indexes = [index.name for index in index_client.list_indexes()]
        
        if index_name in existing_indexes:
            if recreate:
                logger.info(f"Deleting existing index: {index_name}")
                index_client.delete_index(index_name)
            else:
                logger.info(f"Index {index_name} already exists")
                return True
        
        # Define a basic index without vector search
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="metadata", type=SearchFieldDataType.String),
            SimpleField(name="chunk_id", type=SearchFieldDataType.String),
            SimpleField(name="source_filename", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="eo_number", type=SearchFieldDataType.String)
        ]
        
        # Create index definition
        index = SearchIndex(name=index_name, fields=fields)
        
        # Create the index
        logger.info(f"Creating basic index: {index_name}")
        index_client.create_index(index)
        logger.info(f"Index {index_name} created successfully")
        
        # Wait a moment for the index to be available
        time.sleep(2)
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")
        return False

def upload_documents(index_name: str, documents: List[Dict[str, Any]], batch_size: int = 100) -> int:
    """
    Upload documents to Azure AI Search.
    
    Args:
        index_name: Name of the index
        documents: List of documents to upload
        batch_size: Size of batches for upload
        
    Returns:
        Number of documents uploaded
    """
    try:
        # Create search client
        credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=index_name,
            credential=credential
        )
        
        # Prepare documents for indexing (without embeddings)
        search_documents = []
        for i, doc in enumerate(documents):
            if 'content' not in doc:
                logger.warning(f"Document missing content field, skipping")
                continue
            
            # Generate an ID if not present
            doc_id = doc.get('id', f"doc-{i}")
            
            # Extract metadata
            metadata = doc.get('metadata', {})
            metadata_str = json.dumps(metadata)
            
            # Create search document
            search_doc = {
                "id": doc_id,
                "content": doc['content'],
                "metadata": metadata_str,
                "chunk_id": metadata.get('chunk_id', doc_id),
                "source_filename": metadata.get('source_filename', ''),
                "title": metadata.get('title', ''),
                "eo_number": metadata.get('eo_number', '')
            }
            
            search_documents.append(search_doc)
        
        # Upload in batches
        total_uploaded = 0
        for i in range(0, len(search_documents), batch_size):
            batch = search_documents[i:i + batch_size]
            result = search_client.upload_documents(batch)
            
            # Count successful uploads
            successful = sum(1 for r in result if r.succeeded)
            total_uploaded += successful
            
            logger.info(f"Batch {i//batch_size + 1}: Uploaded {successful}/{len(batch)} documents")
        
        logger.info(f"Uploaded a total of {total_uploaded} documents to index {index_name}")
        return total_uploaded
        
    except Exception as e:
        logger.error(f"Error uploading documents: {str(e)}")
        return 0

def main():
    """Main function to upload documents to Azure AI Search."""
    parser = argparse.ArgumentParser(description='Upload documents to Azure AI Search (simplified)')
    parser.add_argument('--input', '-i', required=True, help='Input file with documents')
    parser.add_argument('--recreate-index', action='store_true', help='Recreate index if it exists')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for uploading')
    
    args = parser.parse_args()
    
    # Validate Azure Search credentials
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_API_KEY:
        logger.error("Azure Search credentials not found in environment variables")
        logger.error("Please set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY")
        sys.exit(1)
    
    try:
        # Load documents
        with open(args.input, 'r') as f:
            documents = json.load(f)
        logger.info(f"Loaded {len(documents)} documents from {args.input}")
        
        # Create basic index
        if not create_basic_index(AZURE_SEARCH_INDEX_NAME, args.recreate_index):
            logger.error("Failed to create index")
            sys.exit(1)
        
        # Upload documents
        uploaded_count = upload_documents(
            index_name=AZURE_SEARCH_INDEX_NAME,
            documents=documents,
            batch_size=args.batch_size
        )
        
        if uploaded_count > 0:
            logger.info(f"Successfully uploaded {uploaded_count} documents to Azure AI Search")
        else:
            logger.error("Failed to upload documents to Azure AI Search")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()