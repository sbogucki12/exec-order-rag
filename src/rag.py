"""
RAG (Retrieval Augmented Generation) module.
Implements the core RAG functionality for the application.
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional, Union, Tuple

# Import our modules
from src.embeddings import EmbeddingsGenerator
from src.vector_store import LocalVectorStore
from src.llm import AzureLLM

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LocalRAG:
    """
    Local RAG implementation for testing without cloud services.
    """
    
    def __init__(
        self,
        vector_store_path: str,
        model_name: str = "all-MiniLM-L6-v2",
        top_k: int = 4,
        similarity_threshold: Optional[float] = 0.4,
        llm: Optional[AzureLLM] = None
    ):
        """
        Initialize the RAG system.
        
        Args:
            vector_store_path: Path to the vector store file
            model_name: Name of the embedding model
            top_k: Number of documents to retrieve
            similarity_threshold: Minimum similarity score threshold
            llm: Optional LLM instance for generation
        """
        self.vector_store_path = vector_store_path
        self.model_name = model_name
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        
        # Initialize components
        self.embeddings_generator = EmbeddingsGenerator(model_name=model_name)
        self.vector_store = LocalVectorStore()
        self.llm = llm if llm is not None else AzureLLM()
        
        # Load the vector store
        if not self.vector_store.load(vector_store_path):
            logger.error(f"Failed to load vector store from {vector_store_path}")
            raise ValueError(f"Could not load vector store from {vector_store_path}")
    
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: User query
            top_k: Override for number of documents to retrieve
            
        Returns:
            List of relevant documents
        """
        # Generate embedding for query
        query_embedding = self.embeddings_generator.generate_embeddings([query])[0]
        
        # Search for similar documents
        return self.vector_store.similarity_search(
            query_embedding=query_embedding,
            k=top_k or self.top_k,
            score_threshold=self.similarity_threshold
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
            "just say that you don't have enough information to answer.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            "ANSWER:"
        )
        
        return prompt
    
    def extract_source_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract source document metadata for citation.
        
        Args:
            documents: Retrieved documents
            
        Returns:
            List of source document metadata
        """
        sources = []
        for doc in documents:
            metadata = doc.get("metadata", {})
            source_info = {
                "title": metadata.get("title", metadata.get("source_filename", "Unknown Source"))
            }
            
            # Add executive order number if available
            if "eo_number" in metadata:
                source_info["eo_number"] = metadata["eo_number"]
                
            # Add page number if available
            if "page_number" in metadata:
                source_info["page"] = metadata["page_number"]
                
            # Add chunk ID for reference
            if "id" in doc:
                source_info["chunk_id"] = doc["id"]
                
            sources.append(source_info)
            
        return sources
    
    def query(self, query_text: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Process a query through the RAG pipeline (without LLM integration).
        
        Args:
            query_text: User query text
            chat_history: Optional conversation history
            
        Returns:
            Response containing retrieved documents and generated prompt
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
    
    def process_query(
        self, 
        query: str, 
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> Tuple[str, List[Dict[Any, Any]]]:
        """
        Process a query through the complete RAG pipeline with LLM integration.
        
        Args:
            query: User's question
            chat_history: Optional conversation history
            
        Returns:
            Tuple containing the generated response and source documents
        """
        # Retrieve relevant documents
        retrieved_docs = self.retrieve(query)
        
        if not retrieved_docs:
            return "I couldn't find any relevant information to answer your question.", []
        
        # Format context for the LLM
        context = self.format_context(retrieved_docs)
        context_chunks = [context]  # Convert to list for LLM
        
        # Generate response using the LLM
        response = self.llm.generate_response(
            query=query,
            context=context_chunks,
            chat_history=chat_history
        )
        
        # Extract source documents for citation
        source_documents = self.extract_source_documents(retrieved_docs)
        
        return response, source_documents
    
    def format_response_with_sources(
        self, 
        response: str, 
        source_documents: List[Dict[Any, Any]]
    ) -> str:
        """
        Format the final response with source citations.
        
        Args:
            response: The LLM generated response
            source_documents: List of source document metadata
            
        Returns:
            Response with source citations
        """
        if not source_documents:
            return response
        
        sources_formatted = []
        for i, doc in enumerate(source_documents, 1):
            source = f"{i}. "
            
            if "eo_number" in doc:
                source += f"Executive Order {doc['eo_number']}"
            elif "title" in doc:
                source += doc["title"]
            else:
                source += "Unknown Source"
                
            if "page" in doc:
                source += f", page {doc['page']}"
                
            sources_formatted.append(source)
        
        sources_text = "\n".join(sources_formatted)
        
        return f"{response}\n\nSources:\n{sources_text}"