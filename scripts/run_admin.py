"""
run_admin.py - Script to run the Admin Dashboard independently
Place this in your scripts directory
"""

import os
import sys
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure the JWT_SECRET_KEY and ADMIN_PASSWORD environment variables are set
if 'ADMIN_PASSWORD' not in os.environ:
    os.environ['ADMIN_PASSWORD'] = 'admin-password-change-in-production'
    print("Warning: ADMIN_PASSWORD not set. Using default (please change in production).")

if 'JWT_SECRET_KEY' not in os.environ:
    os.environ['JWT_SECRET_KEY'] = 'dev-secret-key-change-in-production'
    print("Warning: JWT_SECRET_KEY not set. Using default (please change in production).")

# Check for Stripe environment variables and warn if missing
stripe_vars = ['STRIPE_SECRET_KEY', 'STRIPE_PUBLIC_KEY', 'STRIPE_WEBHOOK_SECRET', 'STRIPE_PREMIUM_PRICE_ID']
missing_vars = [var for var in stripe_vars if var not in os.environ]
if missing_vars:
    print(f"Warning: Missing Stripe environment variables: {', '.join(missing_vars)}")
    print("Stripe integration will not be fully functional until these are set.")

if __name__ == '__main__':
    # This will be run using: streamlit run scripts/run_admin.py
    print("Starting Admin Dashboard...")
    
    # The actual running is handled by Streamlit, this is just for setup
    # When this script is run with streamlit run, it will import and execute 
    # scripts/admin_dashboard.py which contains the actual dashboard code
    
    # Set directly accessed flag to ensure password authentication
    # (This is checked in admin_dashboard.py)
    try:
        st.session_state['from_main_app'] = False
    except:
        pass