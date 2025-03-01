"""
Azure AI Foundry LLM integration for RAG chatbot.
Uses open source models hosted on Azure AI Foundry.
"""
import os
from typing import List, Dict, Any, Optional
import requests
import json
import logging
from config import (
    AZURE_AI_FOUNDRY_API_KEY,
    AZURE_AI_FOUNDRY_ENDPOINT,
    AZURE_AI_FOUNDRY_MODEL_NAME,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AzureLLM:
    """Azure AI Foundry LLM client for generating responses based on context."""
    
    def __init__(
        self,
        model_name: str = AZURE_AI_FOUNDRY_MODEL_NAME,
        endpoint: str = AZURE_AI_FOUNDRY_ENDPOINT,
        api_key: str = AZURE_AI_FOUNDRY_API_KEY,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ):
        """Initialize the Azure AI Foundry client."""
        self.endpoint = endpoint
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Set request headers
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key
        }
        
        logger.info(f"Initialized Azure AI Foundry LLM with endpoint: {self.endpoint}")
    
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
        
        # Prepare request body for Azure AI Foundry
        request_body = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        # Make API call to Azure AI Foundry
        try:
            # Use the full endpoint URL provided
            response = requests.post(
                url=self.endpoint,
                headers=self.headers,
                json=request_body,
                timeout=60
            )
            
            # Log status code for debugging
            logger.info(f"API response status code: {response.status_code}")
            
            # Check for errors
            if response.status_code != 200:
                logger.error(f"API error response: {response.text}")
                
            response.raise_for_status()
            
            response_data = response.json()
            logger.debug(f"API response data structure: {list(response_data.keys())}")
            
            # Extract the response content
            return response_data["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Error calling Azure AI Foundry API: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f"\nResponse: {e.response.text}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
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