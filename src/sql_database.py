"""
sql_database.py - Azure SQL Database integration for Executive Orders RAG Chatbot
Provides functions for database operations using Azure SQL instead of MongoDB
"""

import os
import json
import logging
import uuid
import pyodbc
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Azure SQL connection settings
SQL_SERVER = os.getenv('SQL_SERVER')
SQL_DATABASE = os.getenv('SQL_DATABASE')
SQL_USERNAME = os.getenv('SQL_USERNAME')
SQL_PASSWORD = os.getenv('SQL_PASSWORD')
SQL_DRIVER = os.getenv('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')

def get_connection():
    """
    Get a connection to the Azure SQL database.
    
    Returns:
        pyodbc.Connection: Database connection
    """
    try:
        connection_string = (
            f"DRIVER={{{SQL_DRIVER}}};"
            f"SERVER={SQL_SERVER};"
            f"DATABASE={SQL_DATABASE};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD}"
        )
        conn = pyodbc.connect(connection_string)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Azure SQL: {e}")
        raise
def verify_tables_exist():
    """
    Verify that all required tables exist and create them if they don't.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from src.sql_database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if UsageStats table exists
        cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'UsageStats'")
        if cursor.fetchone()[0] == 0:
            logger.warning("UsageStats table doesn't exist! Creating now...")
            cursor.execute("""
            CREATE TABLE UsageStats (
                UsageID VARCHAR(50) PRIMARY KEY,
                UserID VARCHAR(50) NOT NULL,
                Timestamp DATETIME NOT NULL,
                Tokens INT NOT NULL DEFAULT 0,
                Type VARCHAR(50) NOT NULL,
                QueryData NVARCHAR(MAX) NULL
            )
            """)
            conn.commit()
            logger.info("UsageStats table created successfully")
        else:
            logger.info("UsageStats table exists")
        
        # Add similar checks for other tables
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error verifying tables: {e}", exc_info=True)
        return False
    
# User functions
def get_users() -> Dict[str, Dict[str, Any]]:
    """
    Get all users from the database.
    
    Returns:
        dict: Dictionary of user objects keyed by user ID
    """
    users = {}
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Users")
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            user = dict(zip(columns, row))
            user_id = user.get('UserID')
            if user_id:
                users[user_id] = user
        
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error getting users: {e}")
    
    return users

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID.
    
    Args:
        user_id (str): User ID
        
    Returns:
        dict or None: User object if found, None otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Users WHERE UserID = ?", user_id)
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if row:
            user = dict(zip(columns, row))
            # Convert SQL column names to match original MongoDB format
            return {
                'id': user.get('UserID'),
                'email': user.get('Email'),
                'password_hash': user.get('PasswordHash'),
                'plan': user.get('Plan'),
                'created_at': user.get('CreatedAt').isoformat() if user.get('CreatedAt') else None,
                'last_login': user.get('LastLogin').isoformat() if user.get('LastLogin') else None,
                'stripe_customer_id': user.get('StripeCustomerID'),
                'subscription_id': user.get('SubscriptionID')
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user by ID {user_id}: {e}")
        return None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by email.
    
    Args:
        email (str): User email
        
    Returns:
        dict or None: User object if found, None otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Users WHERE Email = ?", email)
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if row:
            user = dict(zip(columns, row))
            # Convert SQL column names to match original MongoDB format
            return {
                'id': user.get('UserID'),
                'email': user.get('Email'),
                'password_hash': user.get('PasswordHash'),
                'plan': user.get('Plan'),
                'created_at': user.get('CreatedAt').isoformat() if user.get('CreatedAt') else None,
                'last_login': user.get('LastLogin').isoformat() if user.get('LastLogin') else None,
                'stripe_customer_id': user.get('StripeCustomerID'),
                'subscription_id': user.get('SubscriptionID')
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user by email {email}: {e}")
        return None

def create_user(user_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new user.
    
    Args:
        user_data (dict): User data
        
    Returns:
        str or None: User ID if successful, None otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        user_id = user_data.get('id') or str(uuid.uuid4())
        email = user_data.get('email')
        password_hash = user_data.get('password_hash')
        plan = user_data.get('plan', 'free')
        
        # Parse dates
        created_at = user_data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not created_at:
            created_at = datetime.utcnow()
            
        last_login = user_data.get('last_login')
        if isinstance(last_login, str):
            last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
        
        cursor.execute("""
        INSERT INTO Users (
            UserID, Email, PasswordHash, [Plan], CreatedAt, LastLogin, 
            StripeCustomerID, SubscriptionID
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, 
        user_id, email, password_hash, plan, created_at, last_login, 
        user_data.get('stripe_customer_id'), user_data.get('subscription_id'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return user_id
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None

def update_user(user_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Update a user.
    
    Args:
        user_id (str): User ID
        update_data (dict): Data to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Construct SET clause for SQL update
        set_clauses = []
        params = []
        
        # Map dictionary keys to SQL column names
        column_mapping = {
            'email': 'Email',
            'password_hash': 'PasswordHash',
            'plan': '[Plan]',
            'created_at': 'CreatedAt',
            'last_login': 'LastLogin',
            'stripe_customer_id': 'StripeCustomerID',
            'subscription_id': 'SubscriptionID'
        }
        
        for key, value in update_data.items():
            if key in column_mapping:
                column_name = column_mapping[key]
                
                # Handle date fields
                if key in ['created_at', 'last_login'] and isinstance(value, str):
                    value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                
                set_clauses.append(f"{column_name} = ?")
                params.append(value)
        
        if not set_clauses:
            logger.warning(f"No valid fields to update for user {user_id}")
            return False
        
        sql = f"UPDATE Users SET {', '.join(set_clauses)} WHERE UserID = ?"
        params.append(user_id)
        
        cursor.execute(sql, params)
        conn.commit()
        
        success = cursor.rowcount > 0
        cursor.close()
        conn.close()
        
        return success
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        return False

def delete_user(user_id: str) -> bool:
    """
    Delete a user and all associated data.
    
    Args:
        user_id (str): User ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # First delete related data
        cursor.execute("DELETE FROM UsageStats WHERE UserID = ?", user_id)
        cursor.execute("DELETE FROM ChatMessages WHERE UserID = ?", user_id)
        
        # Then delete the user
        cursor.execute("DELETE FROM Users WHERE UserID = ?", user_id)
        
        conn.commit()
        success = cursor.rowcount > 0
        
        cursor.close()
        conn.close()
        
        return success
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False

# Chat message functions
def save_chat_message(user_id: str, conversation_id: str, message: Dict[str, Any]) -> bool:
    """
    Save a chat message.
    
    Args:
        user_id (str): User ID
        conversation_id (str): Conversation ID
        message (dict): Message object
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        message_id = message.get('id') or str(uuid.uuid4())
        sender = message.get('sender')
        text = message.get('text')
        
        # Parse timestamp
        timestamp = message.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif not timestamp:
            timestamp = datetime.utcnow()
        
        cursor.execute("""
        INSERT INTO ChatMessages (
            MessageID, UserID, ConversationID, Sender, Text, Timestamp
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, 
        message_id, user_id, conversation_id, sender, text, timestamp)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        return False

def get_chat_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the chat history for a user.
    
    Args:
        user_id (str): User ID
        limit (int): Maximum number of conversations to return
        
    Returns:
        list: List of conversations
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get distinct conversation IDs for this user
        cursor.execute("""
        SELECT DISTINCT TOP (?) ConversationID, MAX(Timestamp) as LastUpdated
        FROM ChatMessages
        WHERE UserID = ?
        GROUP BY ConversationID
        ORDER BY LastUpdated DESC
        """, limit, user_id)
        
        conversation_ids = [row.ConversationID for row in cursor.fetchall()]
        
        # Get the conversations
        conversations = []
        for conv_id in conversation_ids:
            # Get the first message to use as a title/preview
            cursor.execute("""
            SELECT TOP (1) *
            FROM ChatMessages
            WHERE UserID = ? AND ConversationID = ?
            ORDER BY Timestamp ASC
            """, user_id, conv_id)
            
            columns = [column[0] for column in cursor.description]
            first_message = cursor.fetchone()
            
            if first_message:
                first_msg_dict = dict(zip(columns, first_message))
                
                # Get message count
                cursor.execute("""
                SELECT COUNT(*) as MessageCount
                FROM ChatMessages
                WHERE UserID = ? AND ConversationID = ?
                """, user_id, conv_id)
                
                message_count = cursor.fetchone().MessageCount
                
                # Format the conversation
                conversations.append({
                    'id': conv_id,
                    'title': first_msg_dict.get('Text')[:50] + "..." if len(first_msg_dict.get('Text', '')) > 50 else first_msg_dict.get('Text', ''),
                    'message_count': message_count,
                    'last_updated': first_msg_dict.get('Timestamp').isoformat() if first_msg_dict.get('Timestamp') else None
                })
        
        cursor.close()
        conn.close()
        
        return conversations
    except Exception as e:
        logger.error(f"Error getting chat history for user {user_id}: {e}")
        return []

def get_conversation(user_id: str, conversation_id: str) -> Dict[str, Any]:
    """
    Get a specific conversation.
    
    Args:
        user_id (str): User ID
        conversation_id (str): Conversation ID
        
    Returns:
        dict: Conversation object with messages
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT *
        FROM ChatMessages
        WHERE UserID = ? AND ConversationID = ?
        ORDER BY Timestamp ASC
        """, user_id, conversation_id)
        
        columns = [column[0] for column in cursor.description]
        messages = []
        
        for row in cursor.fetchall():
            msg = dict(zip(columns, row))
            messages.append({
                'id': msg.get('MessageID'),
                'sender': msg.get('Sender'),
                'text': msg.get('Text'),
                'timestamp': msg.get('Timestamp').isoformat() if msg.get('Timestamp') else None
            })
        
        cursor.close()
        conn.close()
        
        return {
            'id': conversation_id,
            'messages': messages
        }
    except Exception as e:
        logger.error(f"Error getting conversation {conversation_id} for user {user_id}: {e}")
        return {'id': conversation_id, 'messages': []}

def delete_conversation(user_id: str, conversation_id: str) -> bool:
    """
    Delete a conversation.
    
    Args:
        user_id (str): User ID
        conversation_id (str): Conversation ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        DELETE FROM ChatMessages
        WHERE UserID = ? AND ConversationID = ?
        """, user_id, conversation_id)
        
        conn.commit()
        success = cursor.rowcount > 0
        
        cursor.close()
        conn.close()
        
        return success
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id} for user {user_id}: {e}")
        return False

# Usage tracking functions
def track_usage(user_id: str, tokens: int, request_type: str, request_data: Dict[str, Any] = None) -> bool:
    """
    Track usage for a user.
    
    Args:
        user_id (str): User ID
        tokens (int): Number of tokens used
        request_type (str): Type of request (prompt, token_update, etc.)
        request_data (dict): Additional data about the request
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        usage_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Convert request data to JSON string
        data_json = json.dumps(request_data) if request_data else None
        
        cursor.execute("""
        INSERT INTO UsageStats (
            UsageID, UserID, Timestamp, Tokens, Type, QueryData
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, 
        usage_id, user_id, timestamp, tokens, request_type, data_json)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error tracking usage for user {user_id}: {e}")
        return False

def check_usage_limits(user_id: str, prompt_limit: int = 5, token_limit: int = 2500) -> Tuple[bool, str]:
    """
    Check if a user has exceeded their usage limits.
    
    Args:
        user_id (str): User ID
        prompt_limit (int): Maximum number of prompts allowed
        token_limit (int): Maximum number of tokens allowed
        
    Returns:
        tuple: (is_allowed, reason)
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user information to check if they're premium
        cursor.execute("SELECT [Plan] FROM Users WHERE UserID = ?", user_id)
        user_row = cursor.fetchone()
        
        # If user is premium, they have no limits
        if user_row and user_row.Plan == 'premium':
            cursor.close()
            conn.close()
            return True, "Premium user"
        
        # Get the current month
        current_month = datetime.now().strftime("%Y-%m")
        month_start = f"{current_month}-01"
        
        # Count prompts for the current month
        cursor.execute("""
        SELECT COUNT(*) as PromptCount
        FROM UsageStats
        WHERE UserID = ? AND Type = 'prompt' AND Timestamp >= ?
        """, user_id, month_start)
        
        prompt_count = cursor.fetchone().PromptCount
        
        # Check if prompt limit is exceeded
        if prompt_count >= prompt_limit:
            cursor.close()
            conn.close()
            return False, f"Monthly prompt limit of {prompt_limit} reached"
        
        # Get total tokens for the current month
        cursor.execute("""
        SELECT SUM(Tokens) as TokenSum
        FROM UsageStats
        WHERE UserID = ? AND Timestamp >= ?
        """, user_id, month_start)
        
        token_sum_row = cursor.fetchone()
        token_sum = token_sum_row.TokenSum if token_sum_row.TokenSum is not None else 0
        
        # Check if token limit is exceeded
        if token_sum >= token_limit:
            cursor.close()
            conn.close()
            return False, f"Monthly token limit of {token_limit} reached"
        
        cursor.close()
        conn.close()
        
        # Both limits are within bounds
        return True, f"Within limits ({prompt_count}/{prompt_limit} prompts, {token_sum}/{token_limit} tokens)"
        
    except Exception as e:
        logger.error(f"Error checking usage limits for user {user_id}: {e}")
        # If there's an error checking limits, allow the request but log it
        return True, f"Error checking limits: {e}"

def get_usage_stats() -> Dict[str, Any]:
    """
    Get usage statistics for all users.
    
    Returns:
        dict: Usage statistics
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get total requests and tokens
        cursor.execute("""
        SELECT COUNT(*) as TotalRequests, SUM(Tokens) as TotalTokens
        FROM UsageStats
        """)
        
        totals_row = cursor.fetchone()
        total_requests = totals_row.TotalRequests
        total_tokens = totals_row.TotalTokens or 0
        
        # Get unique users
        cursor.execute("""
        SELECT COUNT(DISTINCT UserID) as UniqueUsers
        FROM UsageStats
        """)
        
        unique_users = cursor.fetchone().UniqueUsers
        
        # Get usage by date
        cursor.execute("""
        SELECT CAST(Timestamp as DATE) as UsageDate,
               COUNT(*) as RequestCount,
               SUM(Tokens) as TokenCount
        FROM UsageStats
        GROUP BY CAST(Timestamp as DATE)
        ORDER BY UsageDate DESC
        """)
        
        usage_by_date = {}
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            date_str = row_dict.get('UsageDate').isoformat()
            usage_by_date[date_str] = {
                'requests': row_dict.get('RequestCount'),
                'tokens': row_dict.get('TokenCount') or 0
            }
        
        # Get usage by user (top users)
        cursor.execute("""
        SELECT TOP 10 
               u.Email,
               u.[Plan],
               COUNT(*) as RequestCount,
               SUM(s.Tokens) as TokenCount
        FROM UsageStats s
        JOIN Users u ON s.UserID = u.UserID
        GROUP BY u.Email, u.[Plan]
        ORDER BY RequestCount DESC
        """)
        
        usage_by_user = {}
        columns = [column[0] for column in cursor.description]
        
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            email = row_dict.get('Email')
            usage_by_user[email] = {
                'plan': row_dict.get('Plan'),
                'requests': row_dict.get('RequestCount'),
                'tokens': row_dict.get('TokenCount') or 0
            }
        
        cursor.close()
        conn.close()
        
        return {
            'usage': {
                'by_date': usage_by_date,
                'by_user': usage_by_user
            },
            'totals': {
                'total_requests': total_requests,
                'total_tokens': total_tokens,
                'unique_users': unique_users
            }
        }
    except Exception as e:
        logger.error(f"Error getting usage statistics: {e}")
        return {
            'error': str(e),
            'usage': {},
            'totals': {'total_requests': 0, 'total_tokens': 0, 'unique_users': 0}
        }

# Admin functions
def is_admin_ip(ip_address: str) -> bool:
    """
    Check if an IP address is in the admin list.
    
    Args:
        ip_address (str): IP address to check
        
    Returns:
        bool: True if the IP is an admin, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM AdminIPs WHERE IPAddress = ?", ip_address)
        result = cursor.fetchone() is not None
        
        cursor.close()
        conn.close()
        
        return result
    except Exception as e:
        logger.error(f"Error checking admin IP {ip_address}: {e}")
        return False

def add_admin_ip(ip_address: str) -> bool:
    """
    Add an IP address to the admin list.
    
    Args:
        ip_address (str): IP address to add
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if already exists
        cursor.execute("SELECT 1 FROM AdminIPs WHERE IPAddress = ?", ip_address)
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return True  # Already an admin
        
        # Insert new admin IP
        ip_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        cursor.execute("""
        INSERT INTO AdminIPs (ID, IPAddress, AddedAt)
        VALUES (?, ?, ?)
        """, ip_id, ip_address, timestamp)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error adding admin IP {ip_address}: {e}")
        return False

def setup_admin_collection() -> bool:
    """
    Set up all required database tables if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create Users table if it doesn't exist
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Users')
        CREATE TABLE Users (
            UserID VARCHAR(50) PRIMARY KEY,
            Email VARCHAR(255) NOT NULL,
            PasswordHash VARCHAR(255) NOT NULL,
            [Plan] VARCHAR(50) DEFAULT 'free',
            CreatedAt DATETIME NOT NULL,
            LastLogin DATETIME NULL,
            StripeCustomerID VARCHAR(255) NULL,
            SubscriptionID VARCHAR(255) NULL
        )
        """)
        
        # Create ChatMessages table if it doesn't exist
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'ChatMessages')
        CREATE TABLE ChatMessages (
            MessageID VARCHAR(50) PRIMARY KEY,
            UserID VARCHAR(50) NOT NULL,
            ConversationID VARCHAR(50) NOT NULL,
            Sender VARCHAR(50) NOT NULL,
            Text NVARCHAR(MAX) NOT NULL,
            Timestamp DATETIME NOT NULL,
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )
        """)
        
        # Create UsageStats table if it doesn't exist
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'UsageStats')
        CREATE TABLE UsageStats (
            UsageID VARCHAR(50) PRIMARY KEY,
            UserID VARCHAR(50) NOT NULL,
            Timestamp DATETIME NOT NULL,
            Tokens INT NOT NULL DEFAULT 0,
            Type VARCHAR(50) NOT NULL,
            QueryData NVARCHAR(MAX) NULL,
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )
        """)
        
        # Create AdminIPs table if it doesn't exist
        cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'AdminIPs')
        CREATE TABLE AdminIPs (
            ID VARCHAR(50) PRIMARY KEY,
            IPAddress VARCHAR(50) NOT NULL,
            AddedAt DATETIME NOT NULL
        )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("All database tables have been set up successfully")
        return True
    except Exception as e:
        logger.error(f"Error setting up database tables: {e}")
        return False

# Migration helper
def migrate_from_json(json_file_path: str) -> bool:
    """
    Migrate users from a JSON file to the SQL database.
    
    Args:
        json_file_path (str): Path to the JSON file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(json_file_path, 'r') as f:
            users_data = json.load(f)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        for user_id, user_data in users_data.items():
            # Check if user already exists
            cursor.execute("SELECT 1 FROM Users WHERE UserID = ?", user_id)
            if cursor.fetchone():
                continue  # Skip existing users
            
            email = user_data.get('email')
            password_hash = user_data.get('password_hash')
            plan = user_data.get('plan', 'free')
            
            # Parse dates
            created_at = user_data.get('created_at')
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif not created_at:
                created_at = datetime.utcnow()
                
            last_login = user_data.get('last_login')
            if isinstance(last_login, str):
                last_login = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
            
            cursor.execute("""
            INSERT INTO Users (
                UserID, Email, PasswordHash, [Plan], CreatedAt, LastLogin, 
                StripeCustomerID, SubscriptionID
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, 
            user_id, email, password_hash, plan, created_at, last_login, 
            user_data.get('stripe_customer_id'), user_data.get('subscription_id'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error migrating from JSON: {e}")
        return False