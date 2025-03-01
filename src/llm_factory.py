"""
Factory for creating LLM instances based on configuration.
"""
import os
import logging
from typing import Optional
from config import LLM_PROVIDER

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_llm(provider: Optional[str] = None, temperature: float = 0.7):
    """
    Create an LLM instance based on the configured provider.
    
    Args:
        provider: LLM provider to use, overriding config setting if provided
        temperature: Temperature setting for the LLM
        
    Returns:
        An instance of the appropriate LLM class
    """
    # Use provided provider or fall back to config
    llm_provider = provider or LLM_PROVIDER
    
    logger.info(f"Creating LLM instance using provider: {llm_provider}")
    
    if llm_provider == "azure_openai":
        try:
            from src.azure_openai_llm import AzureLLM
            return AzureLLM(temperature=temperature)
        except ImportError:
            logger.warning("azure_openai_llm.py not found, falling back to default LLM")
            from src.llm import AzureLLM
            return AzureLLM(temperature=temperature)
            
    elif llm_provider == "azure_ai_foundry":
        from src.llm import AzureLLM
        return AzureLLM(temperature=temperature)
        
    else:
        logger.warning(f"Unknown LLM provider: {llm_provider}, falling back to Azure AI Foundry")
        from src.llm import AzureLLM
        return AzureLLM(temperature=temperature)