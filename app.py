"""
Streamlit web UI for RAG application.
Provides a web interface for interacting with the RAG system.
"""

import os
import streamlit as st
import json
import logging
from datetime import datetime

# Fix for PyTorch and Streamlit watcher conflict
os.environ['STREAMLIT_SERVER_WATCH_DIRS'] = 'false'

# Import our modules
from src.rag import LocalRAG
from src.embeddings import EmbeddingsGenerator
from src.azure_rag import AzureRAG
from src.simple_azure_rag import SimpleAzureRAG
from src.llm_factory import create_llm
from src.usage_limiter import UsageLimiter
from src.usage_integration import (
    initialize_usage_limiter,
    check_usage_limits,
    track_query_usage,
    render_usage_admin_ui
)
from config import AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, AZURE_SEARCH_INDEX_NAME, LLM_PROVIDER

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

# LLM settings
st.sidebar.subheader("LLM Settings")
use_llm = st.sidebar.checkbox("Use LLM for Response Generation", value=True)
llm_provider = st.sidebar.selectbox(
    "LLM Provider",
    options=["azure_ai_foundry", "azure_openai"],
    index=0 if LLM_PROVIDER == "azure_ai_foundry" else 1,
    help="Select which LLM provider to use"
)
temperature = st.sidebar.slider(
    "Temperature",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.1,
    help="Controls randomness in LLM responses. Lower is more deterministic."
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
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'llm' not in st.session_state:
    st.session_state.llm = None

# Initialize LLM if enabled
if use_llm and (st.session_state.llm is None or 'llm_provider' not in st.session_state or st.session_state.llm_provider != llm_provider):
    try:
        st.session_state.llm = create_llm(provider=llm_provider, temperature=temperature)
        st.session_state.llm_provider = llm_provider
        st.sidebar.success(f"✅ LLM initialized using {llm_provider}")
    except Exception as e:
        st.sidebar.error(f"❌ Error initializing LLM: {str(e)}")
        st.session_state.llm = None
        use_llm = False

# Initialize or update RAG system
if st.sidebar.button("Load Vector Store") or st.session_state.rag_system is None:
    try:
        if os.path.exists(index_file):
            # Initialize LLM if needed
            llm_instance = None
            if use_llm:
                try:
                    llm_instance = st.session_state.llm or create_llm(provider=llm_provider, temperature=temperature)
                    st.session_state.llm = llm_instance
                    st.session_state.llm_provider = llm_provider
                except Exception as e:
                    st.sidebar.error(f"❌ Error initializing LLM: {str(e)}")
            
            # Initialize RAG system
            st.session_state.rag_system = LocalRAG(
                vector_store_path=index_file,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                llm=llm_instance
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

# Render admin controls for usage limiting
render_usage_admin_ui()

# Main content
st.title("Executive Orders and Government Guidance Search")

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Query input (using chat input instead of text input)
if query := st.chat_input("Ask a question about executive orders or government guidance"):
    # Check usage limits before processing
    allowed, reason = check_usage_limits()
    
    if not allowed:
        # Display limit exceeded message
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
            
        with st.chat_message("assistant"):
            st.error(f"⚠️ Usage limit exceeded: {reason}")
            st.markdown("Please try again later when your usage limits reset.")
            
        st.session_state.messages.append({
            "role": "assistant", 
            "content": f"⚠️ Usage limit exceeded: {reason}\n\nPlease try again later when your usage limits reset."
        })
    else:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        
        # Add to history if it's a new query
        if query not in st.session_state.query_history:
            st.session_state.query_history.append(query)
        
        # Update last query
        st.session_state.last_query = query
        
        # Process query if RAG system is initialized
    if st.session_state.rag_system:
        with st.chat_message("assistant"):
            with st.spinner("Searching for information..."):
                if use_llm and st.session_state.llm:
                    try:
                        # Format chat history for the LLM
                        chat_history = []
                        for msg in st.session_state.messages[:-1]:  # Skip the latest message
                            chat_history.append({
                                "role": msg["role"],
                                "content": msg["content"]
                            })
                        
                        # Process query through full RAG pipeline
                        response, source_documents = st.session_state.rag_system.process_query(
                            query=query,
                            chat_history=chat_history
                        )
                        
                        # Format response with sources
                        full_response = st.session_state.rag_system.format_response_with_sources(
                            response=response,
                            source_documents=source_documents
                        )
                        
                        # Display response
                        st.markdown(full_response)
                        
                        # Add to chat history
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                        
                        # Store retrieved documents for display
                        st.session_state.results = st.session_state.rag_system.retrieve(query, top_k=top_k)
                        
                        # Track usage
                        track_query_usage(
                            query=query, 
                            response=full_response,
                            additional_data={
                                "documents_retrieved": len(source_documents),
                                "model": llm_provider,
                                "temperature": temperature
                            }
                        )
                        
                    except Exception as e:
                        error_message = f"Error generating response: {str(e)}"
                        st.markdown(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
                else:
                    try:
                        # Just retrieve documents
                        st.session_state.results = st.session_state.rag_system.retrieve(query, top_k=top_k)
                        
                        # Display placeholder message
                        result_summary = f"Found {len(st.session_state.results)} relevant documents. See detailed results below."
                        st.markdown(result_summary)
                        st.session_state.messages.append({"role": "assistant", "content": result_summary})
                        
                        # Track usage (search-only)
                        track_query_usage(
                            query=query, 
                            response=result_summary,
                            additional_data={
                                "documents_retrieved": len(st.session_state.results),
                                "search_only": True
                            }
                        )
                        
                    except Exception as e:
                        error_message = f"Error retrieving documents: {str(e)}"
                        st.markdown(error_message)
                        st.session_state.messages.append({"role": "assistant", "content": error_message})
    else:
        with st.chat_message("assistant"):
            st.markdown("Please load a vector store index first using the sidebar.")
            st.session_state.messages.append({"role": "assistant", "content": "Please load a vector store index first using the sidebar."})

# Clear results button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.results = []
    st.session_state.last_query = ""
    st.rerun()

# Display detailed results
if st.session_state.results:
    st.markdown("---")
    st.subheader("Detailed Search Results")
    
    # Display each result
    for i, doc in enumerate(st.session_state.results):
        with st.expander(f"Result {i+1} - Similarity: {doc.get('similarity_score', 0):.4f}", expanded=i==0):
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

# No RAG system warning
elif st.session_state.rag_system is None and not st.session_state.messages:
    st.warning("Please load a vector store index first using the sidebar.")

# Quick start guide
if not st.session_state.results and not st.session_state.messages:
    st.markdown("## Quick Start Guide")
    st.markdown("""
    1. Make sure you have a vector store index file containing embedded document chunks.
    2. Enter the path to the index file in the sidebar and click "Load Vector Store".
    3. Type your question in the chat box and press Enter.
    4. The system will retrieve relevant information from the executive orders and government guidance documents.
    5. If LLM is enabled, it will generate a detailed response based on the retrieved information.
    
    ### Example Questions:
    - What are the requirements for federal contractors?
    - How are climate change policies being implemented?
    - What recent executive orders address immigration?
    """)

# Footer
st.markdown("---")
st.caption(f"© 2025 Executive Orders RAG System | Last updated: {datetime.now().strftime('%Y-%m-%d')}")