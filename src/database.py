"""
database.py - MongoDB Atlas Database Integration for Executive Orders RAG Chatbot
Provides functions for user management, chat history storage, and usage tracking
"""

import os
import json
import datetime
from typing import Dict, List, Any, Optional, Union
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection settings
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "eo_chatbot")

# Initialize MongoDB client
client = None
db = None

def get_db():
    """Get MongoDB database connection"""
    global client, db
    
    if db is not None:
        return db
    
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI environment variable not set")
    
    # Initialize MongoDB client
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DATABASE]
    
    # Create indexes for better performance
    db.users.create_index("email", unique=True)
    db.chat_history.create_index("user_id")
    db.usage.create_index("ip")
    
    return db

def close_db():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        client = None

# User management functions
def get_users() -> Dict[str, Dict]:
    """Get all users from the database"""
    try:
        db = get_db()
        users = {}
        for user in db.users.find():
            user_id = str(user.pop("_id"))
            users[user_id] = {"id": user_id, **user}
        return users
    except Exception as e:
        print(f"Error getting users: {e}")
        return {}

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID"""
    try:
        db = get_db()
        user = db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            user_id = str(user.pop("_id"))
            return {"id": user_id, **user}
        return None
    except Exception as e:
        print(f"Error getting user by ID: {e}")
        return None

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    try:
        db = get_db()
        user = db.users.find_one({"email": email.lower()})
        if user:
            user_id = str(user.pop("_id"))
            return {"id": user_id, **user}
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None

def create_user(user_data: Dict) -> Optional[str]:
    """Create a new user"""
    try:
        db = get_db()
        
        # Check if email already exists
        existing_user = db.users.find_one({"email": user_data["email"].lower()})
        if existing_user:
            return None
        
        # Prepare user data with MongoDB _id
        user_to_insert = user_data.copy()
        if "id" in user_to_insert:
            del user_to_insert["id"]
        
        # Insert user
        result = db.users.insert_one(user_to_insert)
        return str(result.inserted_id)
    except Exception as e:
        print(f"Error creating user: {e}")
        return None

def update_user(user_id: str, update_data: Dict) -> bool:
    """Update user data"""
    try:
        db = get_db()
        
        # Remove id field if present
        update_data = update_data.copy()
        if "id" in update_data:
            del update_data["id"]
        
        # Update user
        result = db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating user: {e}")
        return False

"""
Add this function to your src/database.py file
"""

def delete_user(user_id: str) -> bool:
    """
    Permanently delete a user from the database.
    
    Args:
        user_id (str): The ID of the user to delete
        
    Returns:
        bool: True if the user was successfully deleted, False otherwise
    """
    try:
        result = db.users.delete_one({"_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return False

# Chat history functions
def save_chat_message(user_id: str, conversation_id: str, message: Dict) -> bool:
    """Save a chat message to the database"""
    try:
        db = get_db()
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.datetime.utcnow()
        
        # Find conversation or create if it doesn't exist
        conversation = db.chat_history.find_one({
            "user_id": user_id,
            "conversation_id": conversation_id
        })
        
        if conversation:
            # Update existing conversation
            result = db.chat_history.update_one(
                {"user_id": user_id, "conversation_id": conversation_id},
                {"$push": {"messages": message}}
            )
            return result.modified_count > 0
        else:
            # Create new conversation
            result = db.chat_history.insert_one({
                "user_id": user_id,
                "conversation_id": conversation_id,
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
                "messages": [message]
            })
            return bool(result.inserted_id)
    except Exception as e:
        print(f"Error saving chat message: {e}")
        return False

def get_chat_history(user_id: str, limit: int = 10) -> List[Dict]:
    """Get chat history for a user"""
    try:
        db = get_db()
        
        # Get all conversations for user, sorted by most recent
        conversations = list(db.chat_history.find(
            {"user_id": user_id}
        ).sort("updated_at", -1).limit(limit))
        
        # Format conversations
        formatted_conversations = []
        for conv in conversations:
            conv_id = str(conv.pop("_id"))
            formatted_conversations.append({
                "id": conv_id,
                "conversation_id": conv.get("conversation_id"),
                "created_at": conv.get("created_at").isoformat() if isinstance(conv.get("created_at"), datetime.datetime) else conv.get("created_at"),
                "updated_at": conv.get("updated_at").isoformat() if isinstance(conv.get("updated_at"), datetime.datetime) else conv.get("updated_at"),
                "messages": conv.get("messages", [])
            })
            
        return formatted_conversations
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

def get_conversation(user_id: str, conversation_id: str) -> Optional[Dict]:
    """Get a specific conversation"""
    try:
        db = get_db()
        
        conversation = db.chat_history.find_one({
            "user_id": user_id,
            "conversation_id": conversation_id
        })
        
        if conversation:
            conv_id = str(conversation.pop("_id"))
            return {
                "id": conv_id,
                "conversation_id": conversation.get("conversation_id"),
                "created_at": conversation.get("created_at").isoformat() if isinstance(conversation.get("created_at"), datetime.datetime) else conversation.get("created_at"),
                "updated_at": conversation.get("updated_at").isoformat() if isinstance(conversation.get("updated_at"), datetime.datetime) else conversation.get("updated_at"),
                "messages": conversation.get("messages", [])
            }
        
        return None
    except Exception as e:
        print(f"Error getting conversation: {e}")
        return None

def delete_conversation(user_id: str, conversation_id: str) -> bool:
    """Delete a conversation"""
    try:
        db = get_db()
        result = db.chat_history.delete_one({
            "user_id": user_id,
            "conversation_id": conversation_id
        })
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return False

# Usage tracking functions
def track_usage(ip: str, tokens_used: int = 0, request_type: str = "api", request_data: Dict = None) -> bool:
    """Track usage for an IP address"""
    try:
        db = get_db()
        
        # Get current date (for daily tracking)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Create request history entry
        history_entry = {
            "timestamp": datetime.datetime.utcnow(),
            "type": request_type,
            "tokens": tokens_used
        }
        if request_data:
            history_entry["data"] = request_data
        
        # Update usage data
        result = db.usage.update_one(
            {"ip": ip},
            {
                "$inc": {
                    "prompt_count": 1 if request_type == "prompt" else 0,
                    "token_count": tokens_used,
                    f"daily.{today}.prompt_count": 1 if request_type == "prompt" else 0,
                    f"daily.{today}.token_count": tokens_used
                },
                "$set": {"last_request": datetime.datetime.utcnow()},
                "$push": {"request_history": history_entry}
            },
            upsert=True
        )
        
        return result.acknowledged
    except Exception as e:
        print(f"Error tracking usage: {e}")
        return False

def get_usage_stats() -> Dict:
    """Get usage statistics"""
    try:
        db = get_db()
        
        # Get all usage data
        usage_data = list(db.usage.find())
        
        # Format for display
        formatted_usage = {}
        for usage in usage_data:
            ip = usage.get("ip")
            masked_ip = mask_ip(ip)
            
            formatted_usage[ip] = {
                "masked_ip": masked_ip,
                "prompt_count": usage.get("prompt_count", 0),
                "token_count": usage.get("token_count", 0),
                "last_request": usage.get("last_request").isoformat() if isinstance(usage.get("last_request"), datetime.datetime) else usage.get("last_request"),
                "daily": usage.get("daily", {}),
                # Limit history to last 20 entries
                "request_history": usage.get("request_history", [])[-20:]
            }
        
        # Calculate totals
        total_requests = sum(u.get("prompt_count", 0) for u in usage_data)
        total_tokens = sum(u.get("token_count", 0) for u in usage_data)
        unique_users = len(usage_data)
        
        return {
            "usage": formatted_usage,
            "totals": {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "unique_users": unique_users
            }
        }
    except Exception as e:
        print(f"Error getting usage stats: {e}")
        return {
            "usage": {},
            "totals": {"total_requests": 0, "total_tokens": 0, "unique_users": 0}
        }

def check_usage_limits(ip: str, prompt_limit: int = None, token_limit: int = None) -> (bool, str):
    """Check if an IP has exceeded usage limits"""
    try:
        db = get_db()
        
        # Get usage data for IP
        usage = db.usage.find_one({"ip": ip})
        
        if not usage:
            return True, "No usage data found"
        
        prompt_count = usage.get("prompt_count", 0)
        token_count = usage.get("token_count", 0)
        
        # Check prompt limit
        if prompt_limit is not None and prompt_count >= prompt_limit:
            return False, f"Prompt limit exceeded: {prompt_count}/{prompt_limit}"
        
        # Check token limit
        if token_limit is not None and token_count >= token_limit:
            return False, f"Token limit exceeded: {token_count}/{token_limit}"
        
        return True, f"Usage within limits: {prompt_count}/{prompt_limit} prompts used"
    except Exception as e:
        print(f"Error checking usage limits: {e}")
        return True, f"Error checking usage limits: {e}"

def reset_usage(ip: str = None) -> bool:
    """Reset usage data for an IP or all IPs"""
    try:
        db = get_db()
        
        if ip:
            # Reset for specific IP
            result = db.usage.update_one(
                {"ip": ip},
                {
                    "$set": {
                        "prompt_count": 0,
                        "token_count": 0,
                        "daily": {},
                        "request_history": []
                    }
                }
            )
            return result.modified_count > 0
        else:
            # Reset for all IPs
            result = db.usage.update_many(
                {},
                {
                    "$set": {
                        "prompt_count": 0,
                        "token_count": 0,
                        "daily": {},
                        "request_history": []
                    }
                }
            )
            return result.modified_count > 0
    except Exception as e:
        print(f"Error resetting usage: {e}")
        return False

# Helper functions
def mask_ip(ip: str) -> str:
    """Mask IP address for privacy (only show first octet)"""
    if not ip:
        return "unknown"
    
    parts = ip.split(".")
    if len(parts) == 4:  # IPv4
        return f"{parts[0]}.*.*.*"
    return "masked-ip"

# Migration function to move data from JSON to MongoDB
def migrate_from_json(users_file: str = "data/users.json", usage_file: str = None) -> bool:
    """Migrate data from JSON files to MongoDB"""
    try:
        # Migrate users
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                users = json.load(f)
                
            db = get_db()
            
            for user_id, user_data in users.items():
                # Check if user already exists
                existing_user = db.users.find_one({"email": user_data["email"].lower()})
                if not existing_user:
                    # Prepare user data
                    user_to_insert = user_data.copy()
                    if "id" in user_to_insert:
                        del user_to_insert["id"]
                    
                    # Insert user
                    db.users.insert_one(user_to_insert)
        
        # Migrate usage data if file provided
        if usage_file and os.path.exists(usage_file):
            with open(usage_file, 'r') as f:
                usage_data = json.load(f)
                
            db = get_db()
            
            # Process usage data
            if "usage" in usage_data:
                for ip, ip_data in usage_data["usage"].items():
                    # Convert to MongoDB document
                    usage_doc = {
                        "ip": ip,
                        "prompt_count": ip_data.get("prompt_count", 0),
                        "token_count": ip_data.get("token_count", 0),
                        "last_request": ip_data.get("last_request"),
                        "request_history": ip_data.get("request_history", [])
                    }
                    
                    # Insert or update usage
                    db.usage.update_one(
                        {"ip": ip},
                        {"$set": usage_doc},
                        upsert=True
                    )
        
        return True
    except Exception as e:
        print(f"Error migrating data: {e}")
        return False

# Function to create admin collections
def setup_admin_collection() -> bool:
    """Set up admin collection with configuration data"""
    try:
        db = get_db()
        
        # Add admin IPs collection if it doesn't exist
        if "admin_ips" not in db.list_collection_names():
            # Get admin IPs from environment
            admin_ips_str = os.getenv("ADMIN_IPS", "")
            admin_ips = [ip.strip() for ip in admin_ips_str.split(",") if ip.strip()]
            
            # Add each admin IP
            for ip in admin_ips:
                db.admin_ips.update_one(
                    {"ip": ip},
                    {"$set": {"ip": ip, "unlimited": True, "added_at": datetime.datetime.utcnow()}},
                    upsert=True
                )
        
        # Add configuration collection
        db.config.update_one(
            {"name": "usage_limits"},
            {"$set": {
                "prompt_limit": int(os.getenv("PROMPT_LIMIT", "20")),
                "token_limit": int(os.getenv("TOKEN_LIMIT", "10000")),
                "reset_period_hours": int(os.getenv("RESET_PERIOD_HOURS", "24"))
            }},
            upsert=True
        )
        
        return True
    except Exception as e:
        print(f"Error setting up admin collection: {e}")
        return False

def is_admin_ip(ip: str) -> bool:
    """Check if an IP is an admin IP"""
    try:
        db = get_db()
        admin_ip = db.admin_ips.find_one({"ip": ip})
        return bool(admin_ip)
    except Exception as e:
        print(f"Error checking admin IP: {e}")
        return False

def add_admin_ip(ip: str) -> bool:
    """Add an IP as an admin IP"""
    try:
        db = get_db()
        db.admin_ips.update_one(
            {"ip": ip},
            {"$set": {"ip": ip, "unlimited": True, "added_at": datetime.datetime.utcnow()}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"Error adding admin IP: {e}")
        return False