"""
Admin authentication for Streamlit dashboard
"""
import os
import streamlit as st

def authenticate_admin():
    """
    Authenticate an admin user with password
    Returns True if authenticated, False otherwise
    """
    # Get admin password from environment
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin-password-change-in-production')
    
    # Check if user is already authenticated in this session
    if 'admin_authenticated' in st.session_state and st.session_state.admin_authenticated:
        return True
    
    # Display login form
    st.title("🔒 Admin Authentication")
    st.markdown("Please enter the admin password to access the dashboard.")
    
    # Get password input
    password = st.text_input("Admin Password", type="password")
    
    # Check password when button is clicked
    if st.button("Login"):
        if password == admin_password:
            st.session_state.admin_authenticated = True
            st.success("✅ Authentication successful! Redirecting...")
            st.experimental_rerun()
            return True
        else:
            st.error("❌ Invalid password")
            return False
    
    return False

def logout_admin():
    """Log out admin by clearing authentication state"""
    if 'admin_authenticated' in st.session_state:
        del st.session_state.admin_authenticated
    st.success("Logged out successfully")
    st.experimental_rerun()