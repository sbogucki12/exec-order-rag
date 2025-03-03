"""
Streamlit web UI for RAG application.
Provides a web interface for interacting with the RAG system.
"""

import os
import streamlit as st
import logging
from datetime import datetime

# Fix for PyTorch and Streamlit watcher conflict
os.environ['STREAMLIT_SERVER_WATCH_DIRS'] = 'false'

# Import our modules
from src.usage_integration import (
    initialize_usage_limiter,
    check_usage_limits,
    track_query_usage,
    get_client_ip
)

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

# Get limiter and client IP
limiter = initialize_usage_limiter()
client_ip = get_client_ip()

# Sidebar configuration
st.sidebar.title("📜 Executive Orders RAG")
st.sidebar.markdown("---")

# Show current IP and usage status (only visible during development)
if st.sidebar.checkbox("Show Debug Info", value=False):
    client_ip = get_client_ip()
    limiter = initialize_usage_limiter()
    
    st.sidebar.markdown("### Debug Information")
    st.sidebar.markdown(f"**Your IP:** `{client_ip}`")
    
    is_admin = limiter.is_admin_ip(client_ip)
    is_unlimited = limiter.is_unlimited_ip(client_ip)
    
    st.sidebar.markdown(f"**Admin IP:** `{is_admin}`")
    st.sidebar.markdown(f"**Unlimited IP:** `{is_unlimited}`")
    
    # If not unlimited, show usage
    if not is_unlimited and client_ip in limiter.usage_data.get("usage", {}):
        usage = limiter.usage_data["usage"][client_ip]
        prompt_count = usage.get("prompt_count", 0)
        token_count = usage.get("token_count", 0)
        st.sidebar.markdown(f"**Prompt Usage:** `{prompt_count}/{limiter.prompt_limit}`")
        st.sidebar.markdown(f"**Token Usage:** `{token_count}`")
        
        # Time until reset
        last_reset = datetime.fromisoformat(usage.get("last_reset", datetime.now().isoformat()))
        next_reset = last_reset + limiter.reset_period
        time_left = next_reset - datetime.now()
        hours_left = max(0, time_left.total_seconds() / 3600)
        
        st.sidebar.markdown(f"**Reset in:** `{hours_left:.1f} hours`")

# Initialize RAG system if not already initialized
if 'rag_system' not in st.session_state or st.session_state.rag_system is None:
    # Default index file path
    default_index_path = "data/vector_store.json"
    default_top_k = 3
    default_threshold = 0.4
    
    # Initialize LLM if it's not initialized
    if 'llm_instance' not in st.session_state or st.session_state.llm_instance is None:
        try:
            import sys
            sys.path.append('.')  # Ensure imports work
            from src.llm_factory import create_llm
            from config import LLM_PROVIDER
            
            # Default settings
            st.session_state.use_llm = True
            st.session_state.llm_provider = LLM_PROVIDER
            st.session_state.temperature = 0.7
            
            # Create LLM
            st.session_state.llm_instance = create_llm(
                provider=st.session_state.llm_provider, 
                temperature=st.session_state.temperature
            )
        except Exception as e:
            logger.error(f"Error initializing default LLM: {e}")
            st.session_state.use_llm = False
            st.session_state.llm_instance = None
    
    # Initialize RAG with default settings
    try:
        # Only attempt to load if the file exists
        if os.path.exists(default_index_path):
            from src.rag import LocalRAG
            
            # Initialize RAG system
            st.session_state.rag_system = LocalRAG(
                vector_store_path=default_index_path,
                top_k=default_top_k,
                similarity_threshold=default_threshold,
                llm=st.session_state.llm_instance if st.session_state.use_llm else None
            )
            
            # Set default settings
            st.session_state.index_file = default_index_path
            st.session_state.top_k = default_top_k
            st.session_state.similarity_threshold = default_threshold
            
            logger.info(f"RAG system initialized with default settings")
    except Exception as e:
        logger.error(f"Error initializing RAG system: {e}")

# Admin link (only shown to admin IPs)
if limiter.is_admin_ip(client_ip):
    st.sidebar.subheader("🔒 Administration")
    
    if st.sidebar.button("Open Admin Dashboard"):
        st.switch_page("pages/01_Admin_Dashboard.py")

# About section
st.sidebar.markdown("---")
st.sidebar.subheader("About")
st.sidebar.markdown(
    "This application helps you find information in executive orders "
    "and government guidance documents using RAG (Retrieval Augmented Generation)."
)

# Main content
st.title("Executive Orders and Government Guidance Search")

# Initialize session state
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""
if 'results' not in st.session_state:
    st.session_state.results = []
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Check if RAG system is initialized
if 'rag_system' not in st.session_state or st.session_state.rag_system is None:
    # Check if the default vector store file exists
    default_index_path = "data/vector_store.json"
    if not os.path.exists(default_index_path):
        # Admin user instructions
        if limiter.is_admin_ip(client_ip):
            st.warning(f"Vector store file not found at {default_index_path}. Please use the Admin Dashboard to configure the RAG system with a valid vector store path.")
        # Normal user message
        else:
            st.info("The system is currently under maintenance. Please check back later.")

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
        
        # Check if RAG system is initialized
        if 'rag_system' not in st.session_state or st.session_state.rag_system is None:
            with st.chat_message("assistant"):
                st.error("The RAG system has not been initialized. Please contact an administrator.")
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "The RAG system has not been initialized. Please contact an administrator."
                })
        else:
            # Process query with RAG system
            with st.chat_message("assistant"):
                with st.spinner("Searching for information..."):
                    if 'use_llm' in st.session_state and st.session_state.use_llm and 'llm_instance' in st.session_state and st.session_state.llm_instance:
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
                            st.session_state.results = st.session_state.rag_system.retrieve(query, top_k=st.session_state.top_k)
                            
                            # Track usage
                            track_query_usage(
                                query=query, 
                                tokens=len(query.split()) + len(full_response.split()),  # Simple token estimation
                                additional_data={
                                    "documents_retrieved": len(source_documents),
                                    "model": st.session_state.llm_provider,
                                    "temperature": st.session_state.temperature
                                }
                            )
                            
                        except Exception as e:
                            error_message = f"Error generating response: {str(e)}"
                            st.markdown(error_message)
                            st.session_state.messages.append({"role": "assistant", "content": error_message})
                    else:
                        try:
                            # Just retrieve documents
                            st.session_state.results = st.session_state.rag_system.retrieve(query, top_k=st.session_state.top_k)
                            
                            # Display placeholder message
                            result_summary = f"Found {len(st.session_state.results)} relevant documents. See detailed results below."
                            st.markdown(result_summary)
                            st.session_state.messages.append({"role": "assistant", "content": result_summary})
                            
                            # Track usage (search-only)
                            track_query_usage(
                                query=query, 
                                tokens=len(query.split()),  # Simple token estimation
                                additional_data={
                                    "documents_retrieved": len(st.session_state.results),
                                    "search_only": True
                                }
                            )
                            
                        except Exception as e:
                            error_message = f"Error retrieving documents: {str(e)}"
                            st.markdown(error_message)
                            st.session_state.messages.append({"role": "assistant", "content": error_message})

# Clear results button
if st.button("Clear Chat"):
    st.session_state.messages = []
    st.session_state.results = []
    st.session_state.last_query = ""
    st.rerun()

# Display detailed results
if 'results' in st.session_state and st.session_state.results:
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

# First-time user experience - only show if no results and no messages
if (('results' not in st.session_state or not st.session_state.results) and 
    ('messages' not in st.session_state or not st.session_state.messages)):
    
    st.markdown("## Welcome to the Executive Orders RAG System")
    st.markdown("""
    This application helps you find information about executive orders and government guidance documents using AI-powered search and retrieval.
    
    ### How to use this system:
    1. Type your question in the chat box at the bottom of the screen
    2. The system will search through a database of executive orders and government documents
    3. You'll receive relevant information with citations to the source documents
    
    ### Example Questions:
    - What are the requirements for federal contractors regarding climate change?
    - How do recent executive orders address immigration policy?
    - What guidance exists for government agencies on AI adoption?
    
    ### Features:
    - Natural language query processing
    - Context-aware responses that cite sources
    - Access to a comprehensive database of executive orders and guidance
    """)
    
    # Add a note for administrators
    if limiter.is_admin_ip(client_ip):
        st.info("📢 **Administrator Notice:** To configure the RAG system, click on 'Open Admin Dashboard' in the sidebar.")

# Footer
st.markdown("---")
st.caption(f"© 2025 Executive Orders RAG System | Last updated: {datetime.now().strftime('%Y-%m-%d')}")