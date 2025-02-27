"""
Azure RAG (Retrieval Augmented Generation) module.
Implements RAG functionality using Azure services.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Union

# Import our modules
from src.embeddings import EmbeddingsGenerator
from src.azure_search import AzureSearchVectorStore

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AzureRAG:
    """
    RAG implementation using Azure services.
    """
    
    def __init__(
        self,
        search_endpoint: str,
        search_key: str,
        index_name: str,
        model_name: str = "all-MiniLM-L6-v2",
        top_k: int = 4,
        use_local_embeddings: bool = True
    ):
        """
        Initialize the Azure RAG system.
        
        Args:
            search_endpoint: Azure AI Search endpoint
            search_key: Azure AI Search API key
            index_name: Name of the search index
            model_name: Name of the embedding model
            top_k: Number of documents to retrieve
            use_local_embeddings: Whether to use local embeddings model or Azure OpenAI
        """
        self.search_endpoint = search_endpoint
        self.search_key = search_key
        self.index_name = index_name
        self.model_name = model_name
        self.top_k = top_k
        self.use_local_embeddings = use_local_embeddings
        
        # Initialize components
        self.embeddings_generator = EmbeddingsGenerator(
            model_name=model_name,
            use_local=use_local_embeddings
        )
        
        self.vector_store = AzureSearchVectorStore(
            search_endpoint=search_endpoint,
            search_key=search_key,
            index_name=index_name
        )
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        content_filter: Optional[str] = None,
        metadata_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: User query
            top_k: Override for number of documents to retrieve
            content_filter: Optional filter for content text
            metadata_filter: Optional filter for metadata
            
        Returns:
            List of relevant documents
        """
        # Generate embedding for query
        query_embedding = self.embeddings_generator.generate_embeddings([query])[0]
        
        # Search for similar documents
        return self.vector_store.similarity_search(
            query_embedding=query_embedding,
            k=top_k or self.top_k,
            content_filter=content_filter,
            metadata_filter=metadata_filter
        )
    
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