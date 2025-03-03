"""
integration.py - Connect existing Streamlit app with the new API-based frontend
"""

import os
import sys
import threading
from subprocess import Popen
import streamlit as st

# Add the current directory to path
sys.path.append('.')

# Import your existing Streamlit app components
from app import initialize_app_state, process_query
from src.usage_limiter import UsageLimiter
from src.usage_integration import check_admin_status

# Import the Flask API
from api import app as flask_app

def run_flask_api():
    """Run the Flask API in a separate process"""
    # Set environment variables
    os.environ['FLASK_ENV'] = 'development'
    os.environ['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
    os.environ['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'change-this-in-production')
    
    # Run the Flask app
    flask_app.run(debug=True, port=5000)

def run_streamlit_admin():
    """Run the Streamlit admin interface on a different port"""
    # Run the Streamlit admin dashboard
    Popen(["streamlit", "run", "pages/01_Admin_Dashboard.py", "--server.port", "8501"])

def main():
    """Main function that runs both interfaces"""
    st.set_page_config(
        page_title="Executive Orders RAG Chatbot",
        page_icon="📚",
        layout="wide"
    )
    
    # Add explanation about the new interface
    st.sidebar.title("📢 New Interface Available!")
    st.sidebar.info(
        "We've launched a new modern interface for the Executive Orders RAG Chatbot! "
        "Visit http://localhost:5000 to try it out. This Streamlit interface will "
        "eventually be for admin-only use."
    )
    
    # Authentication management for admin users
    st.sidebar.title("Admin Access")
    admin_password = st.sidebar.text_input("Admin Password", type="password")
    
    if admin_password:
        if admin_password == os.environ.get('ADMIN_PASSWORD', 'change-this-in-production'):
            st.sidebar.success("Admin access granted!")
            client_ip = "admin"  # Mark as admin for unlimited usage
            check_admin_status(client_ip, True)  # Add to admin IPs
            
            # Show admin options
            if st.sidebar.button("Open Admin Dashboard"):
                run_streamlit_admin()
                st.sidebar.info("Admin dashboard should be opening at port 8501")
        else:
            st.sidebar.error("Incorrect admin password")
    
    # Initialize app
    initialize_app_state()
    
    # Main app title
    st.title("Executive Orders RAG Chatbot")
    st.write("""
    This is the legacy interface for the Executive Orders RAG Chatbot. 
    Ask questions about U.S. Executive Orders.
    """)
    
    # Chat interface - reusing your existing functionality
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # User input
    prompt = st.chat_input("Ask about Executive Orders...")
    
    if prompt:
        # Use your existing processing logic
        client_ip = "streamlit-user"  # Could be improved to get actual IP
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Check usage limits (reusing your existing code)
        usage_limiter = UsageLimiter()
        if not usage_limiter.check_limit(client_ip):
            with st.chat_message("assistant"):
                st.markdown("You have reached your daily usage limit. Please try again tomorrow or log in as a premium user.")
            st.session_state.messages.append({"role": "assistant", "content": "You have reached your daily usage limit. Please try again tomorrow or log in as a premium user."})
            return
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = process_query(prompt)
                st.markdown(response)
        
        # Add response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Log usage
        usage_limiter.log_usage(client_ip)

if __name__ == "__main__":
    # Start the Flask API in a separate thread
    flask_thread = threading.Thread(target=run_flask_api, daemon=True)
    flask_thread.start()
    
    # Run the Streamlit interface
    main()