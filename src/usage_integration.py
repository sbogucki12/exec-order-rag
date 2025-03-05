"""
usage_integration.py - Usage tracking integration for the Executive Orders RAG Chatbot
Provides functions for tracking and managing usage limits using MongoDB
"""

import logging
import os
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
from flask import request, has_request_context

# Import database functions
from src.database import (
    track_usage as db_track_usage,
    check_usage_limits as db_check_limits,
    get_usage_stats as db_get_usage_stats,
    is_admin_ip as db_is_admin_ip,
    add_admin_ip as db_add_admin_ip
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_client_ip() -> str:
    """
    Retrieve the client's IP address safely.
    Uses Flask's request object if in an active request context, 
    otherwise falls back to "unknown".
    
    Returns:
        str: Client IP address
    """
    if has_request_context():
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        return client_ip or "127.0.0.1"

    # If no request context, return unknown
    return "unknown"

def check_usage_limits() -> Tuple[bool, str]:
    """Check current usage limits for the current user."""
    client_ip = get_client_ip()
    logger.info(f"Checking usage limits for IP: {client_ip}")
    
    # Get limits from environment variables or use defaults
    prompt_limit = int(os.environ.get('PROMPT_LIMIT', '20'))
    token_limit = int(os.environ.get('TOKEN_LIMIT', '10000'))
    
    # Check if usage limiting is enabled
    if os.environ.get('USAGE_LIMITING_ENABLED', 'True').lower() != 'true':
        return True, "Usage limiting disabled"
    
    # Check if the IP is admin or unlimited
    unlimited_ips = os.environ.get('UNLIMITED_IPS', '').split(',')
    unlimited_ips = [ip.strip() for ip in unlimited_ips if ip.strip()]
    
    if client_ip in unlimited_ips or db_is_admin_ip(client_ip):
        return True, "Unlimited IP"
    
    # Check usage limits from database
    try:
        return db_check_limits(client_ip, prompt_limit, token_limit)
    except Exception as e:
        logger.error(f"Error checking usage limits: {e}")
        return True, f"Error checking usage limits: {e}"

def get_usage_data():
    """Get usage statistics data for the admin dashboard."""
    try:
        return db_get_usage_stats()
    except Exception as e:
        logger.error(f"Error getting usage data: {e}")
        return {
            "error": f"Failed to get usage data: {e}",
            "usage": {},
            "totals": {"total_requests": 0, "total_tokens": 0, "unique_users": 0}
        }
    
def track_query_usage(tokens: Optional[int] = None, query: Optional[str] = None, count_prompt: bool = True, **kwargs) -> Dict[str, Any]:
    """
    Track usage for the current query.

    Args:
        tokens: Number of tokens used in the query
        query: The query text (optional)
        count_prompt: Whether to increment the prompt counter (default: True)
        **kwargs: Additional tracking data

    Returns:
        dict: Updated usage data
    """
    client_ip = get_client_ip()
    
    # Estimate tokens if not provided
    if tokens is None and query is not None:
        # Very basic token estimation (approximately words)
        tokens = len(query.split())
    
    request_data = {"query": query[:100] + "..." if query and len(query) > 100 else query}
    request_data.update(kwargs)

    request_type = "prompt" if count_prompt else "token_update"

    # Track usage in database
    db_track_usage(client_ip, tokens or 0, request_type, request_data)
    
    # Return stats if admin
    if db_is_admin_ip(client_ip):
        return db_get_usage_stats()
    else:
        return {}
    
def check_admin_status(ip, is_admin=None):
    """
    Check if an IP is an admin or set its admin status.

    Args:
        ip (str): The IP address to check or modify.
        is_admin (bool, optional): If provided, sets the admin status for the IP.

    Returns:
        bool: True if the IP is an admin, False otherwise.
    """
    # If setting admin status
    if is_admin is not None:
        if is_admin:
            db_add_admin_ip(ip)
        else:
            # Remove admin status - not implemented in database module yet
            pass

    # Return admin status
    return db_is_admin_ip(ip)
