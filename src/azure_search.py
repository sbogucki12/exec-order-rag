"""
Azure AI Search integration for RAG application.
Handles vector search using Azure AI Search.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Union
import time

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchAlgorithmConfiguration,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind
)

# Import configuration
from config import (
    AZURE_SEARCH_ENDPOINT,
    AZURE_SEARCH_API_KEY,
    AZURE_SEARCH_INDEX_NAME
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AzureSearchVectorStore:
    """Azure AI Search vector store for RAG applications."""
    
    def __init__(
        self,
        search_endpoint: str = AZURE_SEARCH_ENDPOINT,
        search_key: str = AZURE_SEARCH_API_KEY,
        index_name: str = AZURE_SEARCH_INDEX_NAME,
        embedding_dimension: int = 384,  # Default for all-MiniLM-L6-v2
        vector_field_name: str = "embedding",
        content_field_name: str = "content",
        metadata_field_name: str = "metadata"
    ):
        """
        Initialize the Azure Search vector store.
        
        Args:
            search_endpoint: Azure AI Search endpoint
            search_key: Azure AI Search API key
            index_name: Name of the search index
            embedding_dimension: Dimension of embedding vectors
            vector_field_name: Name of the field containing vector embeddings
            content_field_name: Name of the field containing document content
            metadata_field_name: Name of the field containing metadata
        """
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.index_name = index_name
        self.embedding_dimension = embedding_dimension
        self.vector_field_name = vector_field_name
        self.content_field_name = content_field_name
        self.metadata_field_name = metadata_field_name
        
        # Validate required credentials
        if not search_endpoint or not search_key:
            logger.error("Azure Search credentials not found")
            raise ValueError("Azure Search endpoint and API key are required")
        
        # Initialize clients
        self.search_credential = AzureKeyCredential(search_key)
        self.index_client = SearchIndexClient(
            endpoint=search_endpoint,
            credential=self.search_credential
        )
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=self.search_credential
        )
    
    def create_index(self, recreate: bool = False) -> bool:
        """
        Create the search index if it doesn't exist.
        
        Args:
            recreate: Whether to recreate the index if it already exists
            
        Returns:
            True if index was created or already exists, False on error
        """
        try:
            # Check if index exists
            existing_indexes = [index.name for index in self.index_client.list_indexes()]
            
            if self.index_name in existing_indexes:
                if recreate:
                    logger.info(f"Deleting existing index: {self.index_name}")
                    self.index_client.delete_index(self.index_name)
                else:
                    logger.info(f"Index {self.index_name} already exists")
                    return True
            
            # First, define the fields without vector search to check compatibility
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name=self.content_field_name, type=SearchFieldDataType.String),
                SimpleField(name=self.metadata_field_name, type=SearchFieldDataType.String),
                SimpleField(name="chunk_id", type=SearchFieldDataType.String),
                SimpleField(name="source_filename", type=SearchFieldDataType.String),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchableField(name="eo_number", type=SearchFieldDataType.String)
            ]
            
            # Try to create a VectorSearch configuration and add the vector field
            try:
                # Add vector search configuration
                vector_search = VectorSearch(
                    algorithms=[
                        VectorSearchAlgorithmConfiguration(
                            name="my-algorithm",
                            kind="hnsw",
                            hnsw_parameters=HnswAlgorithmConfiguration(
                                name="my-hnswParameters",
                                m=4,
                                ef_construction=400,
                                ef_search=500,
                                metric="cosine"
                            )
                        )
                    ],
                    profiles=[
                        VectorSearchProfile(
                            name="my-profile",
                            algorithm_configuration_name="my-algorithm"
                        )
                    ]
                )
                
                # Add the vector field with correct configuration
                vector_field = SearchField(
                    name=self.vector_field_name,
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=self.embedding_dimension,
                    vector_search_profile_name="my-profile"
                )
                
                # Add vector field to the fields list
                fields.append(vector_field)
                
                # Create index with vector search
                index = SearchIndex(
                    name=self.index_name,
                    fields=fields,
                    vector_search=vector_search
                )
                
            except Exception as vector_error:
                logger.warning(f"Could not create vector search configuration: {str(vector_error)}")
                logger.warning("Creating index without vector search capabilities")
                
                # Create basic index without vector search
                index = SearchIndex(name=self.index_name, fields=fields)
            
            # Create the index
            logger.info(f"Creating index: {self.index_name}")
            self.index_client.create_index(index)
            logger.info(f"Index {self.index_name} created successfully")
            
            # Wait a moment for the index to be available
            time.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            return False
    
    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """
        Add documents to the Azure Search index.
        
        Args:
            documents: List of document dictionaries with embeddings
            batch_size: Size of batches for uploading
            
        Returns:
            Number of documents added
        """
        if not documents:
            logger.warning("No documents to add")
            return 0
        
        try:
            # Ensure index exists
            existing_indexes = [index.name for index in self.index_client.list_indexes()]
            if self.index_name not in existing_indexes:
                logger.info(f"Index {self.index_name} does not exist, creating...")
                if not self.create_index():
                    logger.error("Could not create index")
                    return 0
            
            # Prepare documents for indexing
            search_documents = []
            for doc in documents:
                if 'content' not in doc:
                    logger.warning(f"Document missing content field, skipping")
                    continue
                
                if 'id' not in doc:
                    # Use chunk_id as id if available, otherwise generate a new id
                    if 'metadata' in doc and 'chunk_id' in doc['metadata']:
                        doc_id = doc['metadata']['chunk_id']
                    else:
                        doc_id = f"doc-{len(search_documents)}"
                else:
                    doc_id = doc['id']
                
                # Extract metadata
                metadata = doc.get('metadata', {})
                metadata_str = json.dumps(metadata)
                
                # Create search document
                search_doc = {
                    "id": doc_id,
                    self.content_field_name: doc['content'],
                    self.metadata_field_name: metadata_str,
                    "chunk_id": metadata.get('chunk_id', doc_id),
                    "source_filename": metadata.get('source_filename', ''),
                    "title": metadata.get('title', ''),
                    "eo_number": metadata.get('eo_number', '')
                }
                
                # Add embedding if available and field exists in index
                if 'embedding' in doc:
                    try:
                        search_doc[self.vector_field_name] = doc['embedding']
                    except Exception as e:
                        logger.warning(f"Could not add embedding: {str(e)}")
                
                search_documents.append(search_doc)
            
            # Upload in batches
            total_uploaded = 0
            for i in range(0, len(search_documents), batch_size):
                batch = search_documents[i:i + batch_size]
                result = self.search_client.upload_documents(batch)
                
                # Count successful uploads
                successful = sum(1 for r in result if r.succeeded)
                total_uploaded += successful
                
                logger.info(f"Batch {i//batch_size + 1}: Uploaded {successful}/{len(batch)} documents")
            
            logger.info(f"Uploaded a total of {total_uploaded} documents to index {self.index_name}")
            return total_uploaded
            
        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return 0
    
    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 4,
        content_filter: Optional[str] = None,
        metadata_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents by embedding.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            content_filter: Optional filter for content text
            metadata_filter: Optional filter for metadata
            
        Returns:
            List of similar documents with similarity scores
        """
        try:
            # First, check if the index supports vector search
            has_vector_search = False
            try:
                index = self.index_client.get_index(self.index_name)
                fields = index.fields
                for field in fields:
                    if field.name == self.vector_field_name and hasattr(field, 'vector_search_dimensions'):
                        has_vector_search = True
                        break
            except Exception as e:
                logger.warning(f"Could not determine if index supports vector search: {str(e)}")
            
            search_results = []
            
            if has_vector_search:
                logger.info("Using vector search")
                # Prepare search options
                vector_query = {
                    "vector": query_embedding,
                    "fields": self.vector_field_name,
                    "k": k
                }
                
                # Prepare filter if needed
                filter_expression = None
                if content_filter or metadata_filter:
                    filter_parts = []
                    if content_filter:
                        filter_parts.append(f"search.ismatch('{content_filter}', '{self.content_field_name}')")
                    if metadata_filter:
                        filter_parts.append(metadata_filter)
                    
                    filter_expression = " and ".join(filter_parts)
                
                # Execute search
                search_results = list(self.search_client.search(
                    search_text=None,
                    vector_queries=[vector_query],
                    filter=filter_expression,
                    select=f"id,{self.content_field_name},{self.metadata_field_name},chunk_id,source_filename,title,eo_number",
                    top=k
                ))
            else:
                logger.info("Vector search not available, using keyword search")
                # Extract keywords from the query for text search
                # This is a fallback when vector search isn't available
                search_text = "executive orders" # Default fallback search
                
                search_results = list(self.search_client.search(
                    search_text=search_text,
                    select=f"id,{self.content_field_name},{self.metadata_field_name},chunk_id,source_filename,title,eo_number",
                    top=k
                ))
            
            # Process results
            results = []
            for result in search_results:
                # Parse metadata from string
                metadata = {}
                if hasattr(result, self.metadata_field_name) and getattr(result, self.metadata_field_name):
                    try:
                        metadata = json.loads(getattr(result, self.metadata_field_name))
                    except:
                        logger.warning(f"Could not parse metadata JSON for document {result.id}")
                
                # Extract specific metadata fields
                if not metadata:
                    metadata = {}
                    if hasattr(result, 'source_filename') and getattr(result, 'source_filename'):
                        metadata['source_filename'] = getattr(result, 'source_filename')
                    if hasattr(result, 'title') and getattr(result, 'title'):
                        metadata['title'] = getattr(result, 'title')
                    if hasattr(result, 'eo_number') and getattr(result, 'eo_number'):
                        metadata['eo_number'] = getattr(result, 'eo_number')
                
                # Get content
                content = getattr(result, self.content_field_name, "")
                
                # Get score
                score = getattr(result, "@search.score", 0.0)
                
                # Add to results
                results.append({
                    "id": result.id,
                    "content": content,
                    "metadata": metadata,
                    "similarity_score": score
                })
            
            logger.info(f"Retrieved {len(results)} documents from search")
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []
    
    def delete_documents(self, doc_ids: List[str]) -> int:
        """
        Delete documents from the index.
        
        Args:
            doc_ids: List of document IDs to delete
            
        Returns:
            Number of documents successfully deleted
        """
        try:
            # Prepare documents for deletion
            documents = [{"id": doc_id} for doc_id in doc_ids]
            
            # Delete documents
            result = self.search_client.delete_documents(documents)
            
            # Count successful deletions
            successful = sum(1 for r in result if r.succeeded)
            
            logger.info(f"Deleted {successful}/{len(doc_ids)} documents from index {self.index_name}")
            return successful
            
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            return 0