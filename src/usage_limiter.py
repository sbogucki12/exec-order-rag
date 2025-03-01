"""
Usage limiting system for the RAG application.
Tracks and limits API usage by IP address.
"""
import os
import json
import time
import logging
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UsageLimiter:
    """
    Tracks and limits API usage by IP address.
    Can limit by number of prompts or total tokens.
    """
    
    def __init__(
        self,
        enabled: bool = True,
        usage_db_path: str = "data/usage_tracking.json",
        prompt_limit: Optional[int] = 20,  # 20 prompts per day per IP
        token_limit: Optional[int] = None,  # Token limit is disabled by default
        reset_period_hours: int = 24,  # Reset limits every 24 hours
        unlimited_ips: Optional[List[str]] = None,  # IPs with unlimited access
        admin_ips: Optional[List[str]] = None,  # Admin IPs - can see usage statistics
    ):
        """
        Initialize the usage limiter.
        
        Args:
            enabled: Whether the usage limiting is enabled
            usage_db_path: Path to store usage data
            prompt_limit: Maximum number of prompts per IP per reset period (None = no limit)
            token_limit: Maximum number of tokens per IP per reset period (None = no limit)
            reset_period_hours: Hours before usage counters reset
            unlimited_ips: List of IP addresses with unlimited access
            admin_ips: List of IP addresses with admin privileges
        """
        self.enabled = enabled
        self.usage_db_path = usage_db_path
        self.prompt_limit = prompt_limit
        self.token_limit = token_limit
        self.reset_period = timedelta(hours=reset_period_hours)
        self.unlimited_ips = unlimited_ips or ["127.0.0.1", "::1", "localhost"]
        self.admin_ips = admin_ips or ["127.0.0.1", "::1", "localhost"]
        
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(usage_db_path), exist_ok=True)
        
        # Initialize usage database if it doesn't exist
        if not os.path.exists(usage_db_path):
            self._initialize_db()
        else:
            # Load existing data
            self.usage_data = self._load_usage_data()
    
    def _initialize_db(self) -> None:
        """Initialize the usage database with default structure."""
        usage_data = {
            "metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            },
            "usage": {}
        }
        
        # Save to file
        with open(self.usage_db_path, 'w') as f:
            json.dump(usage_data, f, indent=2)
        
        self.usage_data = usage_data
    
    def _load_usage_data(self) -> Dict[str, Any]:
        """Load usage data from file."""
        try:
            with open(self.usage_db_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading usage data: {str(e)}")
            return self._initialize_db()
    
    def _save_usage_data(self) -> None:
        """Save usage data to file."""
        # Update last_updated timestamp
        self.usage_data["metadata"]["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.usage_db_path, 'w') as f:
                json.dump(self.usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving usage data: {str(e)}")
    
    def _is_ip_in_list(self, ip: str, ip_list: List[str]) -> bool:
        """
        Check if an IP address is in a list of IPs or networks.
        Handles both individual IPs and CIDR notation.
        """
        if ip in ip_list:
            return True
            
        try:
            # Convert string IP to an IP address object
            ip_obj = ipaddress.ip_address(ip)
            
            # Check if the IP is in any of the networks
            for network_str in ip_list:
                if '/' in network_str:  # CIDR notation
                    try:
                        network = ipaddress.ip_network(network_str, strict=False)
                        if ip_obj in network:
                            return True
                    except ValueError:
                        pass
            
            return False
        except ValueError:
            # If the IP can't be parsed, just do a string comparison
            return ip in ip_list
    
    def is_unlimited_ip(self, ip: str) -> bool:
        """Check if an IP has unlimited access."""
        return self._is_ip_in_list(ip, self.unlimited_ips)
    
    def is_admin_ip(self, ip: str) -> bool:
        """Check if an IP has admin privileges."""
        return self._is_ip_in_list(ip, self.admin_ips)
    
    def _reset_usage_if_needed(self, ip: str) -> None:
        """Reset usage counters if the reset period has passed."""
        if ip not in self.usage_data["usage"]:
            # Initialize new IP
            self.usage_data["usage"][ip] = {
                "first_request": datetime.now().isoformat(),
                "last_request": datetime.now().isoformat(),
                "last_reset": datetime.now().isoformat(),
                "prompt_count": 0,
                "token_count": 0,
                "request_history": []
            }
            return
            
        # Check if reset is needed
        last_reset = datetime.fromisoformat(self.usage_data["usage"][ip]["last_reset"])
        if datetime.now() - last_reset > self.reset_period:
            # Reset counters
            self.usage_data["usage"][ip]["last_reset"] = datetime.now().isoformat()
            self.usage_data["usage"][ip]["prompt_count"] = 0
            self.usage_data["usage"][ip]["token_count"] = 0
            
            # Keep history but mark the reset
            self.usage_data["usage"][ip]["request_history"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "counter_reset",
                "details": "Usage counters reset due to reset period"
            })
    
    def check_limits(self, ip: str) -> Tuple[bool, str]:
        """
        Check if an IP has exceeded its usage limits.
        
        Args:
            ip: The IP address to check
            
        Returns:
            Tuple of (allowed, reason)
        """
        # If limiting is disabled, always allow
        if not self.enabled:
            return True, ""
            
        # Unlimited IPs are always allowed
        if self.is_unlimited_ip(ip):
            return True, ""
            
        # Reset usage if needed
        self._reset_usage_if_needed(ip)
        
        # Check prompt limit
        if self.prompt_limit is not None:
            current_prompts = self.usage_data["usage"][ip]["prompt_count"]
            if current_prompts >= self.prompt_limit:
                return False, f"Prompt limit exceeded ({current_prompts}/{self.prompt_limit})"
                
        # Check token limit
        if self.token_limit is not None:
            current_tokens = self.usage_data["usage"][ip]["token_count"]
            if current_tokens >= self.token_limit:
                return False, f"Token limit exceeded ({current_tokens}/{self.token_limit})"
                
        # All checks passed
        return True, ""
    
    def track_request(
        self, 
        ip: str, 
        tokens_used: Optional[int] = 0, 
        request_type: str = "prompt",
        request_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track a new request from an IP.
        
        Args:
            ip: The IP address making the request
            tokens_used: Number of tokens used in the request
            request_type: Type of request (prompt, search, etc.)
            request_data: Additional data about the request
        """
        if not self.enabled:
            return
            
        # Reset usage if needed
        self._reset_usage_if_needed(ip)
        
        # Update usage data
        self.usage_data["usage"][ip]["last_request"] = datetime.now().isoformat()
        self.usage_data["usage"][ip]["prompt_count"] += 1
        self.usage_data["usage"][ip]["token_count"] += tokens_used
        
        # Add to history (limit history to last 100 entries)
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": request_type,
            "tokens": tokens_used
        }
        
        if request_data:
            history_entry["data"] = request_data
            
        self.usage_data["usage"][ip]["request_history"] = (
            self.usage_data["usage"][ip]["request_history"][-99:] + [history_entry]
        )
        
        # Save updated data
        self._save_usage_data()
    
    def get_usage_stats(self, ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Get usage statistics.
        
        Args:
            ip: Optional IP to get stats for. If None, returns all stats.
            
        Returns:
            Dictionary of usage statistics
        """
        # Only admin IPs can see all stats
        if ip is None or not self.is_admin_ip(ip):
            return {"error": "Unauthorized access to usage statistics"}
            
        if ip and ip in self.usage_data["usage"]:
            return {
                "ip": ip,
                "status": "active" if self.enabled else "disabled",
                "limits": {
                    "prompt_limit": self.prompt_limit,
                    "token_limit": self.token_limit,
                    "reset_period_hours": self.reset_period.total_seconds() / 3600
                },
                "usage": self.usage_data["usage"][ip],
                "is_unlimited": self.is_unlimited_ip(ip),
                "is_admin": self.is_admin_ip(ip)
            }
        elif ip is None:
            # Return summary stats for all IPs
            return {
                "status": "active" if self.enabled else "disabled",
                "limits": {
                    "prompt_limit": self.prompt_limit,
                    "token_limit": self.token_limit,
                    "reset_period_hours": self.reset_period.total_seconds() / 3600
                },
                "total_ips": len(self.usage_data["usage"]),
                "total_prompts": sum(data["prompt_count"] for data in self.usage_data["usage"].values()),
                "total_tokens": sum(data["token_count"] for data in self.usage_data["usage"].values()),
                "ips": list(self.usage_data["usage"].keys())
            }
        else:
            return {"error": "IP not found in usage data"}
    
    def toggle_enabled(self, enabled: Optional[bool] = None) -> bool:
        """
        Toggle or set the enabled state.
        
        Args:
            enabled: If provided, sets to this value. If None, toggles current state.
            
        Returns:
            New enabled state
        """
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = not self.enabled
            
        return self.enabled
    
    def update_limits(
        self, 
        prompt_limit: Optional[int] = None, 
        token_limit: Optional[int] = None,
        reset_period_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Update the limits for all users.
        
        Args:
            prompt_limit: New prompt limit (None = no change)
            token_limit: New token limit (None = no change)
            reset_period_hours: New reset period in hours (None = no change)
            
        Returns:
            Dictionary with the new limits
        """
        if prompt_limit is not None:
            self.prompt_limit = prompt_limit
            
        if token_limit is not None:
            self.token_limit = token_limit
            
        if reset_period_hours is not None:
            self.reset_period = timedelta(hours=reset_period_hours)
            
        return {
            "prompt_limit": self.prompt_limit,
            "token_limit": self.token_limit,
            "reset_period_hours": self.reset_period.total_seconds() / 3600
        }
    
    def add_unlimited_ip(self, ip: str) -> List[str]:
        """
        Add an IP to the unlimited list.
        
        Args:
            ip: IP address to add
            
        Returns:
            Updated list of unlimited IPs
        """
        if ip not in self.unlimited_ips:
            self.unlimited_ips.append(ip)
        return self.unlimited_ips
    
    def remove_unlimited_ip(self, ip: str) -> List[str]:
        """
        Remove an IP from the unlimited list.
        
        Args:
            ip: IP address to remove
            
        Returns:
            Updated list of unlimited IPs
        """
        if ip in self.unlimited_ips:
            self.unlimited_ips.remove(ip)
        return self.unlimited_ips
    
    def add_admin_ip(self, ip: str) -> List[str]:
        """
        Add an IP to the admin list.
        
        Args:
            ip: IP address to add
            
        Returns:
            Updated list of admin IPs
        """
        if ip not in self.admin_ips:
            self.admin_ips.append(ip)
        return self.admin_ips
    
    def remove_admin_ip(self, ip: str) -> List[str]:
        """
        Remove an IP from the admin list.
        
        Args:
            ip: IP address to remove
            
        Returns:
            Updated list of admin IPs
        """
        if ip in self.admin_ips:
            self.admin_ips.remove(ip)
        return self.admin_ips
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        This is a simple approximation - about 4 chars per token for English.
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // 4  # Simple approximation
    
    def reset_ip_usage(self, ip: str) -> bool:
        """
        Manually reset usage for a specific IP.
        
        Args:
            ip: IP address to reset
            
        Returns:
            True if reset was successful, False otherwise
        """
        if ip in self.usage_data["usage"]:
            self.usage_data["usage"][ip]["last_reset"] = datetime.now().isoformat()
            self.usage_data["usage"][ip]["prompt_count"] = 0
            self.usage_data["usage"][ip]["token_count"] = 0
            
            # Add reset event to history
            self.usage_data["usage"][ip]["request_history"].append({
                "timestamp": datetime.now().isoformat(),
                "type": "manual_reset",
                "details": "Usage counters manually reset"
            })
            
            self._save_usage_data()
            return True
        return False