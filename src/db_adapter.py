"""
db_adapter.py - Adapts database calls to the currently configured database
Provides a consistent interface regardless of the database backend
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple

# Import configuration
from src.db_config import DB_TYPE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the appropriate database module
if DB_TYPE == 'mongodb':
    logger.info("Using MongoDB database adapter")
    try:
        from src.database import (
            get_users as mongo_get_users,
            get_user_by_id as mongo_get_user_by_id,
            get_user_by_email as mongo_get_user_by_email,
            create_user as mongo_create_user,
            update_user as mongo_update_user,
            delete_user as mongo_delete_user,
            save_chat_message as mongo_save_chat_message,
            get_chat_history as mongo_get_chat_history,
            get_conversation as mongo_get_conversation,
            delete_conversation as mongo_delete_conversation,
            track_usage as mongo_track_usage,
            check_usage_limits as mongo_check_usage_limits,
            get_usage_stats as mongo_get_usage_stats,
            is_admin_ip as mongo_is_admin_ip,
            add_admin_ip as mongo_add_admin_ip,
            setup_admin_collection as mongo_setup_admin_collection,
            migrate_from_json as mongo_migrate_from_json
        )
    except ImportError as e:
        logger.error(f"Failed to import MongoDB module: {e}")
        raise
else:
    logger.info("Using SQL database adapter")
    try:
        from src.sql_database import (
            get_users as sql_get_users,
            get_user_by_id as sql_get_user_by_id,
            get_user_by_email as sql_get_user_by_email,
            create_user as sql_create_user,
            update_user as sql_update_user,
            delete_user as sql_delete_user,
            save_chat_message as sql_save_chat_message,
            get_chat_history as sql_get_chat_history,
            get_conversation as sql_get_conversation,
            delete_conversation as sql_delete_conversation,
            track_usage as sql_track_usage,
            check_usage_limits as sql_check_usage_limits,
            get_usage_stats as sql_get_usage_stats,
            is_admin_ip as sql_is_admin_ip,
            add_admin_ip as sql_add_admin_ip,
            setup_admin_collection as sql_setup_admin_collection,
            migrate_from_json as sql_migrate_from_json
        )
    except ImportError as e:
        logger.error(f"Failed to import SQL module: {e}")
        raise

# Create adapter functions that call the appropriate implementation
def get_users() -> Dict[str, Dict[str, Any]]:
    """Get all users from the database"""
    if DB_TYPE == 'mongodb':
        return mongo_get_users()
    else:
        return sql_get_users()

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get a user by ID"""
    if DB_TYPE == 'mongodb':
        return mongo_get_user_by_id(user_id)
    else:
        return sql_get_user_by_id(user_id)

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get a user by email"""
    if DB_TYPE == 'mongodb':
        return mongo_get_user_by_email(email)
    else:
        return sql_get_user_by_email(email)

def create_user(user_data: Dict[str, Any]) -> Optional[str]:
    """Create a new user"""
    if DB_TYPE == 'mongodb':
        return mongo_create_user(user_data)
    else:
        return sql_create_user(user_data)

def update_user(user_id: str, update_data: Dict[str, Any]) -> bool:
    """Update a user"""
    if DB_TYPE == 'mongodb':
        return mongo_update_user(user_id, update_data)
    else:
        return sql_update_user(user_id, update_data)

def delete_user(user_id: str) -> bool:
    """Delete a user and all associated data"""
    if DB_TYPE == 'mongodb':
        return mongo_delete_user(user_id)
    else:
        return sql_delete_user(user_id)

def save_chat_message(user_id: str, conversation_id: str, message: Dict[str, Any]) -> bool:
    """Save a chat message"""
    if DB_TYPE == 'mongodb':
        return mongo_save_chat_message(user_id, conversation_id, message)
    else:
        return sql_save_chat_message(user_id, conversation_id, message)

def get_chat_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get the chat history for a user"""
    if DB_TYPE == 'mongodb':
        return mongo_get_chat_history(user_id, limit)
    else:
        return sql_get_chat_history(user_id, limit)

def get_conversation(user_id: str, conversation_id: str) -> Dict[str, Any]:
    """Get a specific conversation"""
    if DB_TYPE == 'mongodb':
        return mongo_get_conversation(user_id, conversation_id)
    else:
        return sql_get_conversation(user_id, conversation_id)

def delete_conversation(user_id: str, conversation_id: str) -> bool:
    """Delete a conversation"""
    if DB_TYPE == 'mongodb':
        return mongo_delete_conversation(user_id, conversation_id)
    else:
        return sql_delete_conversation(user_id, conversation_id)

def track_usage(user_id: str, tokens: int, request_type: str, request_data: Dict[str, Any] = None) -> bool:
    """Track usage for a user"""
    if DB_TYPE == 'mongodb':
        return mongo_track_usage(user_id, tokens, request_type, request_data)
    else:
        return sql_track_usage(user_id, tokens, request_type, request_data)

def check_usage_limits(user_id: str, prompt_limit: int = 5, token_limit: int = 2500) -> Tuple[bool, str]:
    """Check if a user has exceeded their usage limits"""
    if DB_TYPE == 'mongodb':
        return mongo_check_usage_limits(user_id, prompt_limit, token_limit)
    else:
        return sql_check_usage_limits(user_id, prompt_limit, token_limit)

def get_usage_stats() -> Dict[str, Any]:
    """Get usage statistics for all users"""
    if DB_TYPE == 'mongodb':
        return mongo_get_usage_stats()
    else:
        return sql_get_usage_stats()

def is_admin_ip(ip_address: str) -> bool:
    """Check if an IP address is in the admin list"""
    if DB_TYPE == 'mongodb':
        return mongo_is_admin_ip(ip_address)
    else:
        return sql_is_admin_ip(ip_address)

def add_admin_ip(ip_address: str) -> bool:
    """Add an IP address to the admin list"""
    if DB_TYPE == 'mongodb':
        return mongo_add_admin_ip(ip_address)
    else:
        return sql_add_admin_ip(ip_address)

def setup_admin_collection() -> bool:
    """Set up the admin collection/table"""
    if DB_TYPE == 'mongodb':
        return mongo_setup_admin_collection()
    else:
        return sql_setup_admin_collection()

def migrate_from_json(json_file_path: str) -> bool:
    """Migrate users from a JSON file to the database"""
    if DB_TYPE == 'mongodb':
        return mongo_migrate_from_json(json_file_path)
    else:
        return sql_migrate_from_json(json_file_path)