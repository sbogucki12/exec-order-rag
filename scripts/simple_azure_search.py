"""
Simple Azure AI Search test script.
Tests keyword search against Azure AI Search.
"""

import os
import argparse
import logging
import json
import sys

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# Import configuration
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def search_azure(query: str, top_k: int = 3) -> list:
    """
    Perform a basic keyword search against Azure AI Search.
    
    Args:
        query: Search query
        top_k: Number of results to return
        
    Returns:
        List of search results
    """
    try:
        # Create search client
        credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX_NAME,
            credential=credential
        )
        
        # Execute search
        results = list(search_client.search(
            search_text=query,
            select="id,content,metadata,chunk_id,source_filename,title,eo_number",
            top=top_k
        ))
        
        # Process results
        processed_results = []
        for result in results:
            # Get fields, handling both attribute and dictionary access
            if isinstance(result, dict):
                # Dictionary access
                result_id = result.get('id', 'unknown')
                content = result.get('content', '')
                score = result.get('@search.score', 0.0)
                metadata = {}
                metadata_str = result.get('metadata', '{}')
                source_filename = result.get('source_filename', '')
                title = result.get('title', '')
                eo_number = result.get('eo_number', '')
            else:
                # Attribute access
                result_id = getattr(result, 'id', 'unknown')
                content = getattr(result, 'content', '')
                score = getattr(result, '@search.score', 0.0)
                metadata = {}
                metadata_str = getattr(result, 'metadata', '{}')
                source_filename = getattr(result, 'source_filename', '')
                title = getattr(result, 'title', '')
                eo_number = getattr(result, 'eo_number', '')
            
            # Parse metadata if it's a string
            if isinstance(metadata_str, str) and metadata_str:
                try:
                    metadata = json.loads(metadata_str)
                except:
                    pass
            
            # Add fields directly from the result
            if source_filename:
                metadata['source_filename'] = source_filename
            if title:
                metadata['title'] = title
            if eo_number:
                metadata['eo_number'] = eo_number
            
            # Create result object
            processed_result = {
                'id': result_id,
                'content': content,
                'metadata': metadata,
                'similarity_score': score
            }
            
            processed_results.append(processed_result)
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Error searching Azure AI Search: {str(e)}")
        return []

def format_results(results: list) -> str:
    """Format search results for display."""
    if not results:
        return "No results found."
    
    output = []
    for i, result in enumerate(results):
        output.append(f"Result {i+1} [Score: {result.get('similarity_score', 0):.4f}]")
        
        # Add metadata
        metadata = result.get('metadata', {})
        if metadata:
            output.append("Metadata:")
            for key, value in metadata.items():
                output.append(f"  {key}: {value}")
        
        # Add content snippet
        content = result.get('content', '')
        if len(content) > 200:
            snippet = content[:200] + "..."
        else:
            snippet = content
        
        output.append(f"Content: {snippet}")
        output.append("-" * 80)
    
    return "\n".join(output)

def main():
    """Main function to test Azure AI Search."""
    parser = argparse.ArgumentParser(description='Test Azure AI Search (simplified)')
    parser.add_argument('--query', '-q', required=True, help='Search query')
    parser.add_argument('--top', '-k', type=int, default=3, help='Number of results')
    
    args = parser.parse_args()
    
    # Validate Azure Search credentials
    if not AZURE_SEARCH_ENDPOINT or not AZURE_SEARCH_API_KEY or not AZURE_SEARCH_INDEX_NAME:
        logger.error("Azure Search credentials not found in environment variables")
        logger.error("Please set AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, and AZURE_SEARCH_INDEX_NAME")
        sys.exit(1)
    
    try:
        # Execute search
        logger.info(f"Searching for: {args.query}")
        results = search_azure(args.query, args.top)
        
        # Display results
        print(f"\nSearch Results for: {args.query}")
        print(f"Found {len(results)} results:\n")
        print(format_results(results))
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()