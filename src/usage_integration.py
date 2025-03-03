import json
import socket
import os
import logging
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
from src.usage_limiter import UsageLimiter
from src.usage_config import get_usage_config
from flask import request, has_request_context

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Singleton instance of UsageLimiter
_usage_limiter_instance = None

def initialize_usage_limiter() -> UsageLimiter:
    """Initialize and return a UsageLimiter instance."""
    global _usage_limiter_instance
    
    if _usage_limiter_instance is not None:
        return _usage_limiter_instance
    
    config = get_usage_config()
    
    # Try to load admin IPs from file if it exists
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'admin_ips.txt')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_admin_ips = [line.strip() for line in f.readlines() if line.strip()]
            config["admin_ips"] = list(set(config["admin_ips"] + config_admin_ips))
            config["unlimited_ips"] = list(set(config["unlimited_ips"] + config_admin_ips))
    except Exception as e:
        logger.warning(f"Could not load admin_ips.txt: {e}")
    
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
    """Save admin IP to a configuration file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'admin_ips.txt')
        
        existing_ips = []
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                existing_ips = [line.strip() for line in f.readlines() if line.strip()]
        
        normalized_ip = str(ip).lower().strip()
        if normalized_ip not in existing_ips:
            existing_ips.append(normalized_ip)

        with open(config_path, 'w') as f:
            for unique_ip in existing_ips:
                f.write(f"{unique_ip}\n")
        
        limiter = initialize_usage_limiter()
        limiter.add_admin_ip(normalized_ip)
        limiter.add_unlimited_ip(normalized_ip)
        
        return True
    except Exception as e:
        logger.error(f"Could not save admin IP: {e}")
        return False
    
def get_client_ip() -> str:
    """
    Retrieve the client's IP address safely.
    Uses Flask's request object if in an active request context, 
    otherwise falls back to socket-based detection.
    
    Returns:
        str: Client IP address
    """
    if has_request_context():
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        return client_ip or "127.0.0.1"

    # If no request context, fallback to socket
    try:
        host_name = socket.gethostname()
        return socket.gethostbyname(host_name)
    except Exception:
        return "127.0.0.1"

def check_usage_limits() -> Tuple[bool, str]:
    """Check current usage limits for the current user."""
    limiter = initialize_usage_limiter()
    
    if not limiter.enabled:
        return True, "Usage limiting disabled"
    
    try:
        client_ip = get_client_ip()
        logger.info(f"Checking usage limits for IP: {client_ip}")
    except Exception as e:
        logger.error(f"Unable to determine client IP: {e}")
        return True, f"Unable to determine client IP: {e}"
    
    if limiter.is_unlimited_ip(client_ip):
        return True, "Unlimited IP"

    try:
        limiter.track_request(client_ip, tokens_used=0)
        usage_data = limiter.usage_data["usage"].get(client_ip, {})
        prompt_count = usage_data.get("prompt_count", 0)

        if limiter.prompt_limit is not None and prompt_count > limiter.prompt_limit:
            reason = f"Prompt limit exceeded: {prompt_count}/{limiter.prompt_limit} prompts used"
            logger.warning(reason)
            return False, reason

        token_count = usage_data.get("token_count", 0)
        if limiter.token_limit is not None and token_count > limiter.token_limit:
            reason = f"Token limit exceeded: {token_count}/{limiter.token_limit} tokens used"
            logger.warning(reason)
            return False, reason

        return True, f"Usage within limits: {prompt_count}/{limiter.prompt_limit} prompts used"
    except Exception as e:
        logger.error(f"Error checking usage limits: {e}")
        return True, f"Error checking usage limits: {e}"

def get_usage_data():
    """Get usage statistics data for the admin dashboard."""
    limiter = initialize_usage_limiter()
    
    admin_ips = limiter.admin_ips.copy() if hasattr(limiter, 'admin_ips') else []
    admin_ip = admin_ips[0] if admin_ips else "admin"
    
    try:
        stats = limiter.get_usage_stats(ip=admin_ip, admin_ip=admin_ip)
        return stats
    except Exception as e:
        logger.error(f"Error getting usage data: {e}")
        return {
            "error": f"Failed to get usage data: {e}",
            "usage": {},
            "totals": {"total_requests": 0, "total_tokens": 0, "unique_users": 0}
        }
    
def track_query_usage(tokens: Optional[int] = None, query: Optional[str] = None, count_prompt: bool = False, **kwargs) -> Dict[str, Any]:
    """
    Track usage for the current query.

    Args:
        tokens: Number of tokens used in the query
        query: The query text (optional)
        count_prompt: Whether to increment the prompt counter (default: False)
        **kwargs: Additional tracking data

    Returns:
        dict: Updated usage data
    """
    limiter = initialize_usage_limiter()
    client_ip = get_client_ip()
    
    if tokens is None and query is not None:
        tokens = limiter.estimate_tokens(query)

    request_data = {"query": query[:100] + "..." if query and len(query) > 100 else query}
    request_data.update(kwargs)

    request_type = "prompt" if count_prompt else "token_update"

    # Track token usage
    if not count_prompt:
        if client_ip in limiter.usage_data["usage"]:
            limiter.usage_data["usage"][client_ip]["token_count"] += (tokens or 0)
            limiter.usage_data["usage"][client_ip]["last_request"] = datetime.now().isoformat()

            history_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": request_type,
                "tokens": tokens
            }
            if request_data:
                history_entry["data"] = request_data

            if "request_history" in limiter.usage_data["usage"][client_ip]:
                limiter.usage_data["usage"][client_ip]["request_history"].append(history_entry)

            limiter._save_usage_data()
    else:
        limiter.track_request(client_ip, tokens_used=tokens or 0, request_type=request_type, request_data=request_data)

    # Return stats if admin, otherwise return empty dict
    if limiter.is_admin_ip(client_ip):
        return limiter.get_usage_stats(ip=client_ip, admin_ip=client_ip)
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
    limiter = initialize_usage_limiter()

    # If setting admin status
    if is_admin is not None:
        if is_admin:
            limiter.add_admin_ip(ip)
            limiter.add_unlimited_ip(ip)
            save_admin_ip(ip)
        else:
            # Remove from admin list
            if hasattr(limiter, 'admin_ips') and ip in limiter.admin_ips:
                limiter.admin_ips.remove(ip)
            if hasattr(limiter, 'unlimited_ips') and ip in limiter.unlimited_ips:
                limiter.unlimited_ips.remove(ip)

            # Update config file
            try:
                config_path = os.path.join(os.path.dirname(__file__), 'admin_ips.txt')
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        existing_ips = [line.strip() for line in f.readlines() if line.strip()]

                    if ip in existing_ips:
                        existing_ips.remove(ip)

                    with open(config_path, 'w') as f:
                        for unique_ip in existing_ips:
                            f.write(f"{unique_ip}\n")
            except Exception as e:
                logger.error(f"Error updating admin_ips.txt: {e}")

    # Return True if the IP is in the admin list
    return limiter.is_admin_ip(ip)
