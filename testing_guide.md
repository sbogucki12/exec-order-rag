# Testing Guide for Executive Orders RAG Chatbot

This guide provides step-by-step instructions for testing the RAG chatbot locally without requiring Azure resources.

## End-to-End Testing Workflow

Follow these steps to test the entire RAG pipeline locally:

### 1. Set Up Sample Documents

Create a test directory and add some sample executive order documents:

```bash
mkdir -p test_docs
```

You can use executive orders from:
- [The White House Executive Orders](https://www.whitehouse.gov/briefing-room/presidential-actions/executive-orders/)
- [Federal Register Executive Orders](https://www.federalregister.gov/presidential-documents/executive-orders)

Download a few PDFs or text files of executive orders and save them to the `test_docs` directory.

### 2. Process Documents

Process the documents to extract content and split into chunks:

```bash
python scripts/ingest.py --input test_docs --output data/processed_chunks.json
```

Expected output:
- Log messages showing document loading and processing
- A `processed_chunks.json` file in the data directory

### 3. Generate Embeddings

Generate vector embeddings for the document chunks:

```bash
python scripts/embed.py --input data/processed_chunks.json --output data/embedded_chunks.json
```

Expected output:
- Log messages showing embedding generation
- An `embedded_chunks.json` file containing document chunks with embeddings

### 4. Create Vector Store Index

Create a vector store index from the embedded chunks:

```bash
python scripts/create_index.py --input data/embedded_chunks.json --output data/vector_store.json
```

Expected output:
- A `vector_store.json` file containing the vector store index

### 5. Test Vector Search

Test the vector search functionality:

```bash
python scripts/search.py --index data/vector_store.json --query "climate change initiatives"
```

Expected output:
- A list of relevant document chunks related to climate change

### 6. Test RAG CLI

Test the interactive RAG command-line interface:

```bash
python scripts/rag_cli.py --index data/vector_store.json
```

Expected output:
- An interactive CLI where you can enter questions
- Retrieved documents related to your questions

### 7. Test Web Interface

Test the Streamlit web interface:

```bash
streamlit run app.py
```

Expected output:
- A web interface running at http://localhost:8501
- Ability to load the vector store and search for information

## Testing Specific Components

### Document Processing

Test just the document processor component:

```bash
python -c "from src.document_processor import DocumentProcessor; processor = DocumentProcessor(); docs = processor.load_document('test_docs/example.pdf'); print(f'Loaded {len(docs)} document parts')"
```

### Embeddings Generation

Test just the embeddings generator component:

```bash
python -c "from src.embeddings import EmbeddingsGenerator; generator = EmbeddingsGenerator(); emb = generator.generate_embeddings(['This is a test document']); print(f'Generated embedding with dimension {len(emb[0])}')"
```

### Vector Store

Test just the vector store component:

```bash
python -c "from src.vector_store import LocalVectorStore; store = LocalVectorStore(); store.load('data/vector_store.json'); print(f'Loaded {len(store.documents)} documents')"
```

## Troubleshooting

### Common Issues

**Issue**: Missing dependencies
**Solution**: Run `pip install -r requirements.txt` to install all required packages

**Issue**: File not found errors
**Solution**: Make sure you've created the necessary directories (e.g., `data/`) and check file paths

**Issue**: Embedding model download issues
**Solution**: Check your internet connection; the first run will download the model

**Issue**: Out of memory errors
**Solution**: Reduce the number of documents or batch size for processing

### Generating Test Data

If you don't have real executive orders, you can create test documents with:

```bash
echo "Executive Order 12345\n\nTitle: Test Executive Order\n\nJanuary 1, 2025\n\nBy the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered as follows:\n\nSection 1. Policy. This is a test executive order for the RAG system." > test_docs/test_eo.txt
```

### Performance Testing

To test with a larger dataset, you can use a loop to generate multiple test documents:

```bash
for i in {1..10}; do
  echo "Executive Order $i\n\nTitle: Test Executive Order $i\n\nJanuary $i, 2025\n\nBy the authority vested in me as President by the Constitution and the laws of the United States of America, it is hereby ordered as follows:\n\nSection 1. Policy. This is test executive order number $i for the RAG system." > "test_docs/test_eo_$i.txt"
done
```