"""
Azure OpenAI LLM integration for RAG chatbot.
"""
import os
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
)

class AzureLLM:
    """Azure OpenAI LLM client for generating responses based on context."""
    
    def __init__(
        self,
        deployment_name: str = AZURE_OPENAI_DEPLOYMENT_NAME,
        api_version: str = AZURE_OPENAI_API_VERSION,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ):
        """Initialize the Azure OpenAI client."""
        self.client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=api_version,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
        )
        self.deployment_name = deployment_name
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate_response(
        self, 
        query: str, 
        context: List[str],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Generate a response based on the query and retrieved context.
        
        Args:
            query: User's question
            context: List of relevant text chunks from the retrieval step
            chat_history: Optional list of previous messages
            
        Returns:
            The LLM's response as a string
        """
        if chat_history is None:
            chat_history = []
            
        # Create system message with context
        context_text = "\n\n".join(context)
        system_message = f"""You are a helpful assistant that provides accurate information about executive orders and government guidance based on the context provided.
        
CONTEXT:
{context_text}

Based solely on the above context, answer the user's question. If the answer cannot be determined from the context, 
say "I don't have enough information to answer that question." Do not make up information.
"""
        
        # Prepare messages for the chat completion
        messages = [{"role": "system", "content": system_message}]
        
        # Add chat history if provided
        for message in chat_history:
            messages.append(message)
            
        # Add the current user query
        messages.append({"role": "user", "content": query})
        
        # Call the Azure OpenAI API
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.choices[0].message.content
    
    def format_source_documents(self, source_documents: List[Dict[Any, Any]]) -> str:
        """
        Format source documents for citation in the response.
        
        Args:
            source_documents: List of source document metadata
            
        Returns:
            Formatted source citations as a string
        """
        if not source_documents:
            return ""
            
        sources = []
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
                
            sources.append(source)
            
        return "\n".join(sources)