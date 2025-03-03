"""
api_chatbot.py - Non-Streamlit version of the chatbot for API use
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
import requests
from azure.ai.inference import ChatCompletionsClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from dotenv import dotenv_values

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if Azure OpenAI/OpenAI is available
try:
    from openai import OpenAI, AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available. Using fallback responses.")

# RAG components (if available)
try:
    from langchain.chains import ConversationalRetrievalChain
    from langchain_community.retrievers import AzureCognitiveSearchRetriever
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("LangChain not available. Using fallback responses.")

class APIChatbot:
    """API-compatible version of the RAG chatbot"""
    
    def __init__(self):
        """Initialize the chatbot"""
        self.client = None
        self.retriever = None
        self.qa_chain = None
        self.initialized = False
        
        # Try to initialize
        try:
            self._initialize()
        except Exception as e:
            logger.error(f"Error initializing API chatbot: {e}")
    
    def _initialize(self):
        """Initialize the chatbot components using Azure AI Foundry."""
        # Use Azure AI Foundry instead of Azure OpenAI
        azure_foundry_endpoint = os.environ.get("AZURE_AI_FOUNDRY_ENDPOINT")
        azure_foundry_api_key = os.environ.get("AZURE_AI_FOUNDRY_API_KEY")
        azure_foundry_model = os.environ.get("AZURE_AI_FOUNDRY_MODEL_NAME")

        if not azure_foundry_endpoint or not azure_foundry_api_key or not azure_foundry_model:
            logger.warning("Azure AI Foundry environment variables are missing. Using fallback.")
            return

        # Store Foundry credentials in the class
        self.AZURE_API_KEY = azure_foundry_api_key
        self.AZURE_ENDPOINT = azure_foundry_endpoint
        self.MODEL_NAME = azure_foundry_model

        logger.info(f"✅ Initialized Azure AI Foundry model: {self.MODEL_NAME}")
        self.initialized = True
    
    def _initialize_rag(self):
        """Initialize the RAG components"""
        try:
            # Azure Cognitive Search configuration
            search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
            search_key = os.environ.get("AZURE_SEARCH_KEY")
            search_index = os.environ.get("AZURE_SEARCH_INDEX", "executive-orders")
            
            if not search_endpoint or not search_key:
                logger.warning("Azure Cognitive Search not configured. Skipping RAG initialization.")
                return
            
            # Initialize retriever
            self.retriever = AzureCognitiveSearchRetriever(
                service_name=search_endpoint,
                api_key=search_key,
                index_name=search_index,
                content_key="content",
                top_k=5
            )
            
            # Initialize the QA chain
            from langchain.chains import ConversationalRetrievalChain
            from langchain_openai import AzureChatOpenAI
            
            llm = AzureChatOpenAI(
                openai_api_version="2023-07-01-preview",
                deployment_name=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4"),
                temperature=0.5
            )
            
            self.qa_chain = ConversationalRetrievalChain.from_llm(
                llm=llm,
                retriever=self.retriever,
                return_source_documents=True
            )
            
            logger.info("RAG components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing RAG components: {e}")
    
    def process_query(self, query: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """
        Process a query and return a response using RAG first, with Azure AI Foundry as a fallback.

        Args:
            query: The query text
            chat_history: Optional chat history for context

        Returns:
            dict: Response with text and metadata
        """
        response = {
            "response": f"I'm sorry, I couldn't process your query about Executive Orders: {query}",
            "sources": [],
            "error": None
        }

        # Ensure chatbot is initialized
        if not self.initialized:
            response["error"] = "Chatbot not properly initialized"
            return response

        # Use RAG if available
        if RAG_AVAILABLE and self.qa_chain:
            try:
                formatted_history = []
                if chat_history:
                    for msg in chat_history:
                        if msg.get("role") == "user":
                            formatted_history.append((msg.get("content", ""), ""))
                        elif msg.get("role") == "assistant":
                            if formatted_history:
                                formatted_history[-1] = (formatted_history[-1][0], msg.get("content", ""))

                # Get RAG response
                rag_response = self.qa_chain({
                    "question": query,
                    "chat_history": formatted_history
                })

                # Extract answer and sources
                response["response"] = rag_response.get("answer", "No answer found")

                # Extract source documents
                source_docs = rag_response.get("source_documents", [])
                sources = [
                    {
                        "title": doc.metadata.get("title", "Unknown"),
                        "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                    }
                    for doc in source_docs
                ]

                response["sources"] = sources
                return response

            except Exception as e:
                logger.error(f"Error in RAG processing: {e}")
                response["error"] = "RAG processing failed, falling back to Azure AI Foundry."

        # If RAG fails, fallback to Azure AI Foundry
        logger.info("Falling back to Azure AI Foundry for response.")
        try:
            direct_response = self._direct_llm_query(query)
            if direct_response:
                response["response"] = direct_response
                response["error"] = "RAG failed, using Azure AI Foundry response"
        except Exception as direct_e:
            logger.error(f"Direct LLM fallback also failed: {direct_e}")
            response["error"] = f"Error in Azure AI Foundry processing: {str(direct_e)}"

        return response

    
    def _direct_llm_query(self, query: str) -> str:
        try:                 
            env_values = dotenv_values(".env")
            endpoint = env_values.get("AZURE_AI_FOUNDRY_ENDPOINT", "Not Found")
            api_key = os.getenv("AZURE_AI_FOUNDRY_API_KEY")
            model_name = os.getenv("AZURE_AI_FOUNDRY_MODEL_NAME")
            print(f"DEBUG: Retrieved endpoint -> {endpoint}")

            if not endpoint or not api_key or not model_name:
                return "Azure AI Foundry environment variables are missing."

            # Create the Azure AI Foundry Client
            client = ChatCompletionsClient(
                endpoint=endpoint,                
                credential=AzureKeyCredential(api_key)
            )

            # Send the request
            response = client.complete(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": query}
                ],
                max_tokens=500
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Azure AI Foundry request failed: {str(e)}"
        
# Create a singleton instance
chatbot = APIChatbot()

def process_query(query: str, chat_history: Optional[List] = None) -> str:
    """
    Process a query using RAG first, fallback to Azure AI Foundry if RAG fails.

    Args:
        query: The query text
        chat_history: Optional chat history

    Returns:
        str: Response text
    """
    try:
        response = chatbot.process_query(query, chat_history)

        # If RAG is successful, return the response
        if response and "response" in response:
            formatted_response = response["response"]

            # If there are sources, format them nicely
            if response["sources"]:
                formatted_response += "\n\nSources:\n"
                for i, source in enumerate(response["sources"], 1):
                    formatted_response += f"{i}. {source['title']}: {source['snippet']}\n"

            return formatted_response

    except Exception as e:
        logger.error(f"RAG processing failed: {e}")

    # If RAG fails, fallback to Azure AI Foundry
    logger.info("Falling back to Azure AI Foundry for response.")
    return chatbot._direct_llm_query(query)  # ❌ You had _direct_llm_query(query) without chatbot
