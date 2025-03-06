"""
db_config.py - Database configuration for Executive Orders RAG Chatbot
Centralized configuration for database connections
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Database type configuration
# Set to either "mongodb" or "sql" to determine which database module to use
DB_TYPE = os.getenv('DB_TYPE', 'sql').lower()

# MongoDB/Cosmos DB configuration
MONGODB_CONNECTION_STRING = os.getenv('MONGODB_CONNECTION_STRING', '')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'eobot')

# Azure SQL Database configuration
SQL_SERVER = os.getenv('SQL_SERVER', '')
SQL_DATABASE = os.getenv('SQL_DATABASE', 'eobot')
SQL_USERNAME = os.getenv('SQL_USERNAME', '')
SQL_PASSWORD = os.getenv('SQL_PASSWORD', '')
SQL_DRIVER = os.getenv('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')

# Connection pool configuration
CONNECTION_POOL_SIZE = int(os.getenv('CONNECTION_POOL_SIZE', '5'))
CONNECTION_TIMEOUT = int(os.getenv('CONNECTION_TIMEOUT', '30'))

# Usage limits configuration
DEFAULT_PROMPT_LIMIT = int(os.getenv('DEFAULT_PROMPT_LIMIT', '5'))
DEFAULT_TOKEN_LIMIT = int(os.getenv('DEFAULT_TOKEN_LIMIT', '2500'))
PREMIUM_PROMPT_LIMIT = int(os.getenv('PREMIUM_PROMPT_LIMIT', '100'))
PREMIUM_TOKEN_LIMIT = int(os.getenv('PREMIUM_TOKEN_LIMIT', '50000'))

# Admin configuration
ADMIN_IPS = os.getenv('ADMIN_IPS', '').split(',')
ADMIN_IPS = [ip.strip() for ip in ADMIN_IPS if ip.strip()]

def get_db_module():
    """
    Import and return the appropriate database module based on configuration.
    
    Returns:
        module: The database module to use
    """
    if DB_TYPE == 'mongodb':
        # Legacy MongoDB database module
        try:
            from src.database import db as mongo_db
            return mongo_db
        except ImportError:
            print("WARNING: Failed to import MongoDB module, falling back to SQL")
            DB_TYPE = 'sql'
    
    # Default to SQL module
    try:
        from src.sql_database import db as sql_db
        return sql_db
    except ImportError:
        raise ImportError("Failed to import database module. Ensure sql_database.py is in the src directory.")

def get_connection_string():
    """
    Get the appropriate connection string based on the database type.
    
    Returns:
        str: Connection string for the configured database
    """
    if DB_TYPE == 'mongodb':
        return MONGODB_CONNECTION_STRING
    else:
        return (
            f"DRIVER={{{SQL_DRIVER}}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD}"
        )