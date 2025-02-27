"""
Document ingestion script for RAG application.
Processes documents and prepares them for indexing.
"""

import os
import argparse
import json
import logging
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings

# Import our document processor
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.document_processor import DocumentProcessor
from config import AZURE_STORAGE_CONNECTION_STRING, AZURE_STORAGE_CONTAINER_NAME

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def upload_to_blob_storage(chunks, container_name=AZURE_STORAGE_CONTAINER_NAME):
    """
    Upload processed document chunks to Azure Blob Storage.
    
    Args:
        chunks: List of processed document chunks
        container_name: Azure Blob Storage container name
    """
    if not AZURE_STORAGE_CONNECTION_STRING:
        logger.warning("Azure Storage connection string not found. Skipping upload.")
        return
    
    try:
        # Create the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        
        # Get the container client
        try:
            container_client = blob_service_client.get_container_client(container_name)
            # Check if container exists
            container_client.get_container_properties()
        except Exception:
            # Create container if it doesn't exist
            container_client = blob_service_client.create_container(container_name)
            logger.info(f"Created container: {container_name}")
        
        # Generate a timestamp for the upload batch
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Upload each chunk as a separate blob
        for chunk in chunks:
            chunk_id = chunk.get("id")
            blob_name = f"chunks/{timestamp}/{chunk_id}.json"
            
            # Convert chunk to JSON string
            chunk_json = json.dumps(chunk)
            
            # Upload the chunk
            blob_client = container_client.get_blob_client(blob_name)
            blob_client.upload_blob(
                chunk_json,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/json")
            )
        
        logger.info(f"Successfully uploaded {len(chunks)} chunks to blob storage")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading to blob storage: {str(e)}")
        return False

def main():
    """Main function to run the document ingestion process."""
    parser = argparse.ArgumentParser(description='Process documents for RAG application')
    parser.add_argument('--input', '-i', required=True, help='Input directory or file path')
    parser.add_argument('--output', '-o', help='Output JSON file path (optional)')
    parser.add_argument('--chunk-size', type=int, default=1000, help='Chunk size')
    parser.add_argument('--chunk-overlap', type=int, default=200, help='Chunk overlap')
    parser.add_argument('--upload', action='store_true', help='Upload to Azure Blob Storage')
    
    args = parser.parse_args()
    
    try:
        # Initialize document processor
        processor = DocumentProcessor(
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            metadata_extractor=DocumentProcessor.extract_executive_order_metadata
        )
        
        # Process documents
        if os.path.isdir(args.input):
            chunks = processor.process_from_directory(args.input)
        else:
            documents = processor.load_document(args.input)
            chunks = processor.process_documents(documents)
        
        logger.info(f"Processed {len(chunks)} total chunks")
        
        # Save to output file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(chunks, f, indent=2)
            logger.info(f"Saved processed chunks to {args.output}")
        
        # Upload to blob storage if requested
        if args.upload:
            upload_to_blob_storage(chunks)
        
    except Exception as e:
        logger.error(f"Error in document ingestion: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()