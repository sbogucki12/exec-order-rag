# Executive Orders RAG Chatbot

A Retrieval Augmented Generation (RAG) system for accessing and querying information about executive orders and government guidance documents.

[![Day 4](https://img.youtube.com/vi/_MHlRiT9v1w/0.jpg)](https://youtu.be/_MHlRiT9v1w)


## Development Timeline 

### Day 3
- **Current functionality**: Enhanced admin capabilities, fixed prompt limitations, added usage statistics.
- **Accomplishments**:
  - Created a dedicated admin dashboard separate from the main UI
  - Successfully implemented prompt limitations to control usage
  - Added privacy-focused user statistics with masked IP display
  - Added usage data visualization with charts
  - Fixed various bugs in the usage tracking system
- **Next**:
  - Create a clean, simple custom UI
  - Add authentication for users who want unlimited access
  - Prepare for public deployment

### Day 2 
- **Current functionality**: Full chat functionality with executive orders
- **Currently missing**: Limit on number of prompts. 
- **Next**: 
  - Limit number of prompts. 
  - Move admin features to a separate protected admin console. 
  - Add authentication. 

### Day 1
- **Current functionality**: Runs locally, queries Executive Orders, provides relevant EO responsive to each prompt. 
- **Currently missing**: Chat functionality (isn't integrated with LLM).
- **Next**: 
  - Integrate LLM for chat functionality. 
  - Integrate with Azure AI. 
  - Add authentication. 


## Features

- **Document Processing**: Process executive orders and guidance documents in various formats (PDF, DOCX, TXT, HTML)
- **Vector Search**: Find relevant information using semantic similarity
- **Local Testing**: Develop and test locally before deploying to Azure
- **Command-line Interface**: Interactive CLI for testing the RAG system
- **Web Interface**: Streamlit-based web UI for user-friendly access
- **Admin Dashboard**: Separate admin panel for managing settings and viewing statistics
- **Usage Limits**: Control the number of prompts users can submit
- **Usage Analytics**: Track and visualize usage statistics with privacy protection

## Project Structure

```
azure-rag-chatbot/
├── .env                     # Environment variables (API keys, etc.)
├── app.py                   # Streamlit web application
├── config.py                # Configuration settings
├── requirements.txt         # Dependencies
├── README.md                # Project documentation
├── pages/                   # Streamlit multi-page app components
│   └── 01_Admin_Dashboard.py   # Admin dashboard interface
├── data/                    # Data storage
│   ├── vector_store.json    # Vector storage for embeddings
│   └── usage_tracking.json  # Usage statistics tracking
├── scripts/
│   ├── ingest.py                  # Document ingestion script
│   ├── embed.py                   # Embedding generation script
│   ├── create_index.py            # Index creation script
│   ├── search.py                  # Vector search script
│   ├── simple_azure_search.py     # Simplified Azure search implementation
│   ├── simple_azure_upload.py     # Simplified Azure upload implementation
│   ├── test_azure_foundry.py      # Test scripts for Azure AI Foundry
│   ├── test_azure_search.py       # Test scripts for Azure Search
│   ├── upload_to_azure.py         # Azure upload utilities
│   └── rag_cli.py                 # Command-line interface for RAG
└── src/
    ├── document_processor.py      # Document chunking and processing
    ├── embeddings.py              # Embedding generation
    ├── vector_store.py            # Vector search functionality
    ├── rag.py                     # Core RAG functionality
    ├── simple_azure_rag.py        # Simplified Azure RAG implementation
    ├── azure_rag.py               # Azure RAG implementation
    ├── azure_search.py            # Azure Search integration
    ├── azure_openai_llm.py        # Azure OpenAI integration
    ├── llm_factory.py             # Factory for creating LLM instances
    ├── llm.py                     # LLM integration
    ├── usage_config.py            # Configuration for usage limits
    ├── usage_integration.py       # Integration of usage limiting with UI
    ├── usage_limiter.py           # Core usage limiting functionality
    └── admin_ips.txt              # List of admin IP addresses
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- VS Code with Python extension
- Azure Subscription (for production deployment)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd azure-rag-chatbot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   copy .env.example .env
   # Edit .env with your API keys and configuration
   ```

### Document Processing Pipeline

Process documents in various formats:

```bash
python scripts/ingest.py --input test_docs --output processed_chunks.json
```

Generate embeddings for processed documents:

```bash
python scripts/embed.py --input processed_chunks.json --output embedded_chunks.json
```

Create a vector store index:

```bash
python scripts/create_index.py --input embedded_chunks.json --output data/vector_store.json
```

### Using the RAG System

Use the command-line interface for testing:

```bash
python scripts/rag_cli.py --index data/vector_store.json
```

Or run the Streamlit web application:

```bash
streamlit run app.py
```

### Accessing the Admin Dashboard

The admin dashboard provides access to:
- Usage limiting configuration
- User statistics and visualizations
- LLM settings
- RAG configuration

To access the admin dashboard:
1. Run the application with `streamlit run app.py`
2. If you're an admin user, you'll see an "Open Admin Dashboard" button in the sidebar
3. If not, you'll need to add your IP to the admin list using the IP Management section

## Azure Integration

### Required Azure Resources

For a production deployment, the following Azure resources are needed:

- **Azure AI Search**: For vector storage and search
- **Azure OpenAI Service**: For embeddings and text generation
- **Azure AI Foundry**: For AI model hosting and management
- **Azure Storage Account**: For document storage
- **Azure App Service**: For hosting the web application

### Deployment to Azure

Instructions for deploying to Azure will be added in a future update.

## Usage Examples

### Command-line Interface

```bash
# Interactive mode
python scripts/rag_cli.py --index data/vector_store.json

# Single query mode
python scripts/rag_cli.py --index data/vector_store.json --query "What are the requirements for federal contractors?"
```

### Web Interface

The Streamlit web interface provides a user-friendly way to search for information in executive orders and government guidance documents.

1. Run the web application:
   ```bash
   streamlit run app.py
   ```

2. Open your browser and navigate to http://localhost:8501

3. Ask questions about executive orders in the chat interface

## Future Enhancements

- **Custom UI**: Create a clean, modern interface beyond the default Streamlit appearance
- **Authentication System**: Implement user authentication for access control
- **Payment Integration**: Add payment functionality for subscription-based access
- **Advanced Search Features**: Filters, sorting, and faceted search
- **Document Management UI**: Interface for managing document sources

## Contact

[LinkedIn](https://www.linkedin.com/in/sbogucki12/)