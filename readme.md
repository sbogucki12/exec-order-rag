# Executive Orders RAG Chatbot

A Retrieval Augmented Generation (RAG) system for accessing and querying information about executive orders and government guidance documents.

[![Day 0](https://img.youtube.com/vi/0U-SMbpEHbg/0.jpg)](https://youtu.be/0U-SMbpEHbg)

Current functionality: Runs locally, queries Executive Orders, provides relevant EO responsive to each prompt. 
Currently lacks chat functionality (isn't integrated with LLM).
Next: Integrate LLM for chat functionality. 
Integrate with Azure AI. 
Add authentication. 


## Features

- **Document Processing**: Process executive orders and guidance documents in various formats (PDF, DOCX, TXT, HTML)
- **Vector Search**: Find relevant information using semantic similarity
- **Local Testing**: Develop and test locally before deploying to Azure
- **Command-line Interface**: Interactive CLI for testing the RAG system
- **Web Interface**: Streamlit-based web UI for user-friendly access

## Project Structure

```
azure-rag-chatbot/
├── .env                  # Environment variables (API keys, etc.)
├── app.py                # Streamlit web application
├── config.py             # Configuration settings
├── requirements.txt      # Dependencies
├── README.md             # Project documentation
├── scripts/
│   ├── ingest.py         # Document ingestion script
│   ├── embed.py          # Embedding generation script
│   ├── create_index.py   # Index creation script
│   ├── search.py         # Vector search script
│   └── rag_cli.py        # Command-line interface for RAG
└── src/
    ├── document_processor.py  # Document chunking and processing
    ├── embeddings.py          # Embedding generation
    ├── vector_store.py        # Vector search functionality
    ├── rag.py                 # Core RAG functionality
    └── llm.py                 # LLM integration (to be implemented)
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

## Azure Integration

### Required Azure Resources

For a production deployment, the following Azure resources are needed:

- **Azure AI Search**: For vector storage and search
- **Azure OpenAI Service**: For embeddings and text generation
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

3. Enter the path to your vector store index file and click "Load Vector Store"

4. Enter your question and click "Search"

## Future Enhancements

- **Azure OpenAI Integration**: Connect to Azure OpenAI for advanced language model capabilities
- **Authentication System**: Implement user authentication for access control
- **Usage Tracking**: Track and limit user queries
- **Payment Integration**: Add payment functionality for subscription-based access
- **Advanced Search Features**: Filters, sorting, and faceted search
- **Document Management UI**: Interface for managing document sources

## License

[License information]

## Contact

[Contact information]