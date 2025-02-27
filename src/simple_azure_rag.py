"""
Simplified Azure RAG module without vector search.
Uses keyword search against Azure AI Search.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleAzureRAG:
    """
    Simple RAG implementation using Azure AI Search with keyword search.
    """
    
    def __init__(
        self,
        search_endpoint: str,
        search_key: str,
        index_name: str,
        top_k: int = 4
    ):
        """
        Initialize the simplified Azure RAG system.
        
        Args:
            search_endpoint: Azure AI Search endpoint
            search_key: Azure AI Search API key
            index_name: Name of the search index
            top_k: Number of documents to retrieve
        """
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.index_name = index_name
        self.top_k = top_k
        
        # Initialize search client
        self.search_credential = AzureKeyCredential(search_key)
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=self.search_credential
        )
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query using keyword search.
        
        Args:
            query: User query text
            top_k: Number of results to return (overrides default)
            filter_expr: Optional filter expression
            
        Returns:
            List of relevant documents
        """
        try:
            # Execute search
            results = list(self.search_client.search(
                search_text=query,
                select="id,content,metadata,chunk_id,source_filename,title,eo_number",
                filter=filter_expr,
                top=top_k or self.top_k
            ))
            
            # Process results
            processed_results = []
            for result in results:
                # Handle results that might be dictionaries or objects
                if isinstance(result, dict):
                    # Dictionary access
                    result_id = result.get('id', 'unknown')
                    content = result.get('content', '')
                    score = result.get('@search.score', 0.0)
                    metadata_str = result.get('metadata', '{}')
                else:
                    # Attribute access
                    result_id = getattr(result, 'id', 'unknown')
                    content = getattr(result, 'content', '')
                    score = getattr(result, '@search.score', 0.0)
                    metadata_str = getattr(result, 'metadata', '{}')
                
                # Parse metadata
                metadata = {}
                if isinstance(metadata_str, str) and metadata_str:
                    try:
                        metadata = json.loads(metadata_str)
                    except:
                        logger.warning(f"Could not parse metadata JSON for document {result_id}")
                
                # Extract metadata fields directly if available
                for field in ['source_filename', 'title', 'eo_number']:
                    if isinstance(result, dict) and field in result and result[field]:
                        metadata[field] = result[field]
                    elif hasattr(result, field) and getattr(result, field):
                        metadata[field] = getattr(result, field)
                
                # Create processed result
                processed_results.append({
                    "id": result_id,
                    "content": content,
                    "metadata": metadata,
                    "similarity_score": score
                })
            
            logger.info(f"Retrieved {len(processed_results)} documents from Azure AI Search")
            return processed_results
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return []
    
    def format_context(self, documents: List[Dict[str, Any]]) -> str:
        """
        Format retrieved documents into context for the LLM.
        
        Args:
            documents: List of relevant documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(documents):
            # Extract content and metadata
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            
            # Format metadata if available
            metadata_str = ""
            if metadata:
                source = metadata.get("source_filename", "Unknown source")
                if "title" in metadata:
                    metadata_str = f"Title: {metadata['title']}\nSource: {source}"
                elif "eo_number" in metadata:
                    metadata_str = f"Executive Order: {metadata['eo_number']}\nSource: {source}"
                else:
                    metadata_str = f"Source: {source}"
            
            # Add formatted document to context
            context_parts.append(
                f"[Document {i+1}]:\n"
                f"{metadata_str}\n\n"
                f"{content}\n"
            )
        
        # Join all context parts
        return "\n----\n".join(context_parts)
    
    def generate_prompt(
        self,
        query: str,
        documents: List[Dict[str, Any]]
    ) -> str:
        """
        Generate a prompt for the LLM with retrieved context.
        
        Args:
            query: User query
            documents: Retrieved relevant documents
            
        Returns:
            Complete prompt for the LLM
        """
        # Format context from documents
        context = self.format_context(documents)
        
        # Create prompt with instructions, context, and query
        prompt = (
            "You are an AI assistant helping with questions about executive orders and government guidance.\n"
            "Use the following context to answer the question. If the information is not in the context, "
            "just say that you don't have enough information to answer and explain why, being specific about "
            "what the question is asking for and what's missing from the provided context. In your answer, "
            "refer to specific executive orders or guidance documents by their correct titles or numbers.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            "ANSWER:"
        )
        
        return prompt
    
    def query(self, query_text: str) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline.
        
        Args:
            query_text: User query text
            
        Returns:
            Response containing retrieved documents and generated answer
        """
        # Retrieve relevant documents
        retrieved_docs = self.retrieve(query_text)
        
        # Generate prompt with context
        prompt = self.generate_prompt(query_text, retrieved_docs)
        
        # For now, just return the prompt and documents
        # (LLM integration will be added later)
        return {
            "query": query_text,
            "documents": retrieved_docs,
            "prompt": prompt,
            "answer": "LLM integration coming soon..."
        }