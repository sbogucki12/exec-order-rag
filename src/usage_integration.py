"""
Integration module for the usage limiting system.
Provides functions to initialize and interact with the usage limiter from Streamlit.
"""
import streamlit as st
import json
import socket
import os
import logging
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

# Import the full-featured UsageLimiter from usage_limiter.py
from src.usage_limiter import UsageLimiter
from src.usage_config import get_usage_config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Singleton instance of UsageLimiter
_usage_limiter_instance = None

def initialize_usage_limiter() -> UsageLimiter:
    """
    Initialize and return a UsageLimiter instance.
    Uses a singleton pattern to ensure only one instance exists.
    
    Returns:
        UsageLimiter: The usage limiter instance
    """
    global _usage_limiter_instance
    
    # Return existing instance if already initialized
    if _usage_limiter_instance is not None:
        return _usage_limiter_instance
    
    # Get config from usage_config
    config = get_usage_config()
    
    # Try to load admin IPs from file if it exists (for backwards compatibility)
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'admin_ips.txt')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_admin_ips = [line.strip() for line in f.readlines() if line.strip()]
                
            # Add these IPs to the config
            config["admin_ips"] = list(set(config["admin_ips"] + config_admin_ips))
            config["unlimited_ips"] = list(set(config["unlimited_ips"] + config_admin_ips))
    except Exception as e:
        st.warning(f"Could not load admin_ips.txt: {e}")
    
    # Create the limiter instance
    _usage_limiter_instance = UsageLimiter(
        enabled=config["enabled"],
        usage_db_path=config["db_path"],
        prompt_limit=config["prompt_limit"],
        token_limit=config["token_limit"],
        reset_period_hours=config["reset_period_hours"],
        unlimited_ips=config["unlimited_ips"],
        admin_ips=config["admin_ips"]
    )
    
    return _usage_limiter_instance

def save_admin_ip(ip: str) -> bool:
    """
    Save admin IP to a configuration file.
    
    Args:
        ip: IP address to save
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Attempt to save to a config file in the src directory
        config_path = os.path.join(os.path.dirname(__file__), 'admin_ips.txt')
        
        # Read existing IPs
        existing_ips = []
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                existing_ips = [line.strip() for line in f.readlines() if line.strip()]
        
        # Add new IP if not already present
        normalized_ip = str(ip).lower().strip()
        if normalized_ip not in existing_ips:
            existing_ips.append(normalized_ip)
        
        # Write back to file
        with open(config_path, 'w') as f:
            for unique_ip in existing_ips:
                f.write(f"{unique_ip}\n")
                
        # Also update the limiter instance
        limiter = initialize_usage_limiter()
        limiter.add_admin_ip(normalized_ip)
        limiter.add_unlimited_ip(normalized_ip)
        
        return True
    except Exception as e:
        st.error(f"Could not save admin IP: {e}")
        return False

def get_client_ip() -> str:
    """
    Retrieve the client's IP address.
    
    Returns:
        str: Client IP address
    """
    # First, check Streamlit's runtime for client IP
    try:
        # This might change in future Streamlit versions
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and hasattr(ctx, 'session_client_state'):
            client_ip = ctx.session_client_state.client_ip
            if client_ip:
                return client_ip
    except Exception:
        pass
    
    # Additional fallback methods
    try:
        # Try to get host name and IP
        host_name = socket.gethostname()
        client_ip = socket.gethostbyname(host_name)
        return client_ip
    except Exception:
        # If all else fails, return localhost
        return "127.0.0.1"

def check_usage_limits() -> Tuple[bool, str]:
    """
    Check current usage limits for the current user.
    
    Returns:
        tuple: (boolean indicating if usage is allowed, reason for limitation)
    """
    # Get the limiter instance
    limiter = initialize_usage_limiter()
    
    # Skip if usage limiting is disabled
    if not limiter.enabled:
        return True, "Usage limiting disabled"
    
    # Get client IP
    try:
        client_ip = get_client_ip()
        # Debug log to troubleshoot
        logger.info(f"Checking usage limits for IP: {client_ip}")
    except Exception as e:
        # If unable to get IP, default to allowing access
        logger.error(f"Unable to determine client IP: {e}")
        return True, f"Unable to determine client IP: {e}"
    
    # Check if IP is unlimited
    if limiter.is_unlimited_ip(client_ip):
        logger.info(f"IP {client_ip} has unlimited access")
        return True, "Unlimited IP"
    
    # Get current usage
    try:
        # Track this request (which increments the counter)
        limiter.track_request(client_ip, tokens_used=0)
        
        # Get updated usage stats
        usage_data = limiter.usage_data["usage"].get(client_ip, {})
        prompt_count = usage_data.get("prompt_count", 0)
        
        # Check against limit
        if limiter.prompt_limit is not None and prompt_count > limiter.prompt_limit:
            reason = f"Prompt limit exceeded: {prompt_count-1}/{limiter.prompt_limit} prompts used"
            logger.warning(reason)
            return False, reason
            
        # Token limit check
        token_count = usage_data.get("token_count", 0)
        if limiter.token_limit is not None and token_count > limiter.token_limit:
            reason = f"Token limit exceeded: {token_count}/{limiter.token_limit} tokens used"
            logger.warning(reason)
            return False, reason
            
        logger.info(f"Usage within limits: {prompt_count-1}/{limiter.prompt_limit} prompts used")
        return True, f"Usage within limits: {prompt_count-1}/{limiter.prompt_limit} prompts used"
    except Exception as e:
        logger.error(f"Error checking usage limits: {e}")
        return True, f"Error checking usage limits: {e}"  # Default to allowing access in case of errors

def track_query_usage(tokens: Optional[int] = None, query: Optional[str] = None, count_prompt: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Track usage for the current query.
    
    Args:
        tokens: Number of tokens used in the query
        query: The query text (optional)
        count_prompt: Whether to increment the prompt counter (default: False, as it's already incremented in check_usage_limits)
        **kwargs: Additional tracking data
    
    Returns:
        dict: Updated usage data
    """
    limiter = initialize_usage_limiter()
    client_ip = get_client_ip()
    
    # Estimate tokens if not provided but query is
    if tokens is None and query is not None:
        tokens = limiter.estimate_tokens(query)
    
    # Create request data
    request_data = {"query": query[:100] + "..." if query and len(query) > 100 else query}
    request_data.update(kwargs)
    
    # Special request type that doesn't increment prompt count (since already done in check_usage_limits)
    request_type = "prompt" if count_prompt else "token_update"
    
    # Track the request (token usage only, don't increment prompt count again)
    if not count_prompt:
        # Get current data
        if client_ip in limiter.usage_data["usage"]:
            # Just update the tokens directly
            limiter.usage_data["usage"][client_ip]["token_count"] += (tokens or 0)
            limiter.usage_data["usage"][client_ip]["last_request"] = datetime.now().isoformat()
            
            # Add to history
            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": request_type,
                "tokens": tokens
            }
            
            if request_data:
                history_entry["data"] = request_data
                
            if "request_history" in limiter.usage_data["usage"][client_ip]:
                limiter.usage_data["usage"][client_ip]["request_history"].append(history_entry)
            
            # Save the data
            limiter._save_usage_data()
    else:
        # Normal tracking with prompt increment
        limiter.track_request(client_ip, tokens_used=tokens or 0, request_type=request_type, request_data=request_data)
    
    # Return stats (and pass the client_ip as the admin_ip if it's an admin)
    if limiter.is_admin_ip(client_ip):
        return limiter.get_usage_stats(ip=client_ip, admin_ip=client_ip)
    else:
        # Non-admins don't get stats
        return {}