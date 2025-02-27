"""
Streamlit web UI for RAG application.
Provides a web interface for interacting with the RAG system.
"""

import os
import streamlit as st
import json
import logging
from datetime import datetime

# Import our modules
from src.rag import LocalRAG
from src.embeddings import EmbeddingsGenerator
from src.rag import LocalRAG
from src.azure_rag import AzureRAG
from src.embeddings import EmbeddingsGenerator
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME
from src.simple_azure_rag import SimpleAzureRAG

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="Executive Orders RAG",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar configuration
st.sidebar.title("📜 Executive Orders RAG")
st.sidebar.markdown("---")

# Vector store selection
index_file = st.sidebar.text_input(
    "Vector Store Index Path",
    value="data/vector_store.json",
    help="Path to the vector store index file"
)

# RAG parameters
st.sidebar.subheader("RAG Parameters")
top_k = st.sidebar.slider(
    "Number of Results",
    min_value=1,
    max_value=10,
    value=3,
    help="Number of documents to retrieve"
)

similarity_threshold = st.sidebar.slider(
    "Similarity Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.4,
    step=0.05,
    help="Minimum similarity score for retrieved documents"
)

# Initialize session state
if 'rag_system' not in st.session_state:
    st.session_state.rag_system = None
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""
if 'results' not in st.session_state:
    st.session_state.results = []

# Initialize or update RAG system
if st.sidebar.button("Load Vector Store") or st.session_state.rag_system is None:
    try:
        if os.path.exists(index_file):
            st.session_state.rag_system = LocalRAG(
                vector_store_path=index_file,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            st.sidebar.success(f"✅ Loaded vector store with {len(st.session_state.rag_system.vector_store.documents)} documents")
        else:
            st.sidebar.error(f"❌ Vector store file not found: {index_file}")
            st.session_state.rag_system = None
    except Exception as e:
        st.sidebar.error(f"❌ Error loading vector store: {str(e)}")
        st.session_state.rag_system = None

# Query history
st.sidebar.subheader("Query History")
for i, query in enumerate(st.session_state.query_history[-5:]):
    if st.sidebar.button(f"{query[:30]}..." if len(query) > 30 else query, key=f"hist_{i}"):
        st.session_state.last_query = query

# About section
st.sidebar.markdown("---")
st.sidebar.subheader("About")
st.sidebar.markdown(
    "This application helps you find information in executive orders "
    "and government guidance documents using RAG (Retrieval Augmented Generation)."
)

# Main content
st.title("Executive Orders and Government Guidance Search")

# Query input
query = st.text_input(
    "Enter your question about executive orders or government guidance",
    value=st.session_state.last_query
)

col1, col2 = st.columns([1, 5])
search_button = col1.button("🔍 Search", use_container_width=True)
clear_button = col2.button("Clear Results", use_container_width=False)

# Clear results if requested
if clear_button:
    st.session_state.results = []
    st.session_state.last_query = ""
    query = ""

# Process query
if search_button and query and st.session_state.rag_system:
    with st.spinner("Searching for relevant information..."):
        try:
            # Add to history if it's a new query
            if query not in st.session_state.query_history:
                st.session_state.query_history.append(query)
            
            # Update last query
            st.session_state.last_query = query
            
            # Retrieve documents
            documents = st.session_state.rag_system.retrieve(query, top_k=top_k)
            
            # Store results
            st.session_state.results = documents
            
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")

# Display results
if st.session_state.results:
    st.subheader(f"Search Results for: {st.session_state.last_query}")
    
    # Summary
    st.info(f"Found {len(st.session_state.results)} relevant documents")
    
    # Display each result
    for i, doc in enumerate(st.session_state.results):
        with st.expander(f"Result {i+1} - Similarity: {doc['similarity_score']:.4f}", expanded=i==0):
            # Metadata section
            if 'metadata' in doc and doc['metadata']:
                metadata = doc['metadata']
                metadata_html = ""
                
                if 'source_filename' in metadata:
                    metadata_html += f"<b>Source:</b> {metadata['source_filename']}<br>"
                if 'title' in metadata:
                    metadata_html += f"<b>Title:</b> {metadata['title']}<br>"
                if 'eo_number' in metadata:
                    metadata_html += f"<b>Executive Order:</b> {metadata['eo_number']}<br>"
                if 'date' in metadata:
                    metadata_html += f"<b>Date:</b> {metadata['date']}<br>"
                
                if metadata_html:
                    st.markdown(metadata_html, unsafe_allow_html=True)
                    st.markdown("---")
            
            # Content section
            content = doc.get('content', '')
            st.markdown(content)
            
    # LLM Integration placeholder
    st.markdown("---")
    st.subheader("Generated Answer")
    st.info("LLM integration coming soon. Once connected to Azure OpenAI, this section will show a generated answer based on the retrieved content.")

# No RAG system warning
elif st.session_state.rag_system is None:
    st.warning("Please load a vector store index first using the sidebar.")

# Quick start guide
if not st.session_state.results and not query:
    st.markdown("## Quick Start Guide")
    st.markdown("""
    1. Make sure you have a vector store index file containing embedded document chunks.
    2. Enter the path to the index file in the sidebar and click "Load Vector Store".
    3. Type your question in the search box and click "Search".
    4. The system will retrieve relevant information from the executive orders and government guidance documents.
    
    ### Example Questions:
    - What are the requirements for federal contractors?
    - How are climate change policies being implemented?
    - What recent executive orders address immigration?
    """)

# Footer
st.markdown("---")
st.caption(f"© 2025 Executive Orders RAG System | Last updated: {datetime.now().strftime('%Y-%m-%d')}")