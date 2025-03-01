"""
Configuration settings for the usage limiting system.
"""
import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Usage limiting settings
USAGE_LIMITING_ENABLED = os.getenv("USAGE_LIMITING_ENABLED", "true").lower() == "true"
USAGE_DB_PATH = os.getenv("USAGE_DB_PATH", "data/usage_tracking.json")

# Limit settings
PROMPT_LIMIT = int(os.getenv("PROMPT_LIMIT", "20"))
TOKEN_LIMIT = int(os.getenv("TOKEN_LIMIT", "0"))  # 0 means no limit
RESET_PERIOD_HOURS = int(os.getenv("RESET_PERIOD_HOURS", "24"))

# IP allowlists
UNLIMITED_IPS = os.getenv("UNLIMITED_IPS", "127.0.0.1,::1,localhost").split(",")
ADMIN_IPS = os.getenv("ADMIN_IPS", "127.0.0.1,::1,localhost").split(",")

def get_usage_config():
    """
    Get a dictionary of all usage limiting configuration.
    
    Returns:
        Dictionary with all usage limiting settings
    """
    return {
        "enabled": USAGE_LIMITING_ENABLED,
        "db_path": USAGE_DB_PATH,
        "prompt_limit": PROMPT_LIMIT if PROMPT_LIMIT > 0 else None,
        "token_limit": TOKEN_LIMIT if TOKEN_LIMIT > 0 else None,
        "reset_period_hours": RESET_PERIOD_HOURS,
        "unlimited_ips": UNLIMITED_IPS,
        "admin_ips": ADMIN_IPS
    }