"""
run_api.py - Script to run the API server for development
"""

import sys
sys.path.append('.')  # Add root directory to path
import os
from dotenv import load_dotenv
from api import app

# Load environment variables from .env file
load_dotenv()

# Set default environment variables if not present
if 'JWT_SECRET_KEY' not in os.environ:
    print("Warning: JWT_SECRET_KEY not set. Using development default.")
    os.environ['JWT_SECRET_KEY'] = 'dev-secret-key-change-in-production'

if 'ADMIN_PASSWORD' not in os.environ:
    print("Warning: ADMIN_PASSWORD not set. Using development default.")
    os.environ['ADMIN_PASSWORD'] = 'admin-password-change-in-production'

if __name__ == '__main__':
    print("Starting API server at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)