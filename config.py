import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Vector store settings
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "data/vector_store")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-ada-002")

# Document processing settings
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))

# Azure OpenAI configuration
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Azure AI Search configuration
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

# Azure AI Service configuration
AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT")
AZURE_AI_API_KEY = os.getenv("AZURE_AI_API_KEY")

# Azure Blob Storage configuration
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME")

# Azure AI Studio settings (open source models)
AZURE_AI_STUDIO_API_KEY = os.getenv("AZURE_AI_STUDIO_API_KEY")
AZURE_AI_STUDIO_ENDPOINT = os.getenv("AZURE_AI_STUDIO_ENDPOINT")
AZURE_AI_STUDIO_MODEL_NAME = os.getenv("AZURE_AI_STUDIO_MODEL_NAME", "llama-3-70b-instruct")

# LLM Provider Selection
# Options: "azure_openai", "azure_ai_studio"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "azure_ai_studio")

# Azure AI Foundry settings (open source models)
AZURE_AI_FOUNDRY_API_KEY = os.getenv("AZURE_AI_FOUNDRY_API_KEY")
AZURE_AI_FOUNDRY_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT", 
                                     "https://ai-stevebogucki129260ai375724862414.services.ai.azure.com/models/chat/completions?api-version=2024-05-01-preview")
AZURE_AI_FOUNDRY_MODEL_NAME = os.getenv("AZURE_AI_FOUNDRY_MODEL_NAME", "Meta-Llama-3.1-8B-Instruct")