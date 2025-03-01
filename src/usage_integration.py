import streamlit as st
import json
import socket
import os
from datetime import timedelta, datetime

class UsageLimiter:
    """
    A comprehensive usage limiter class to track and manage user access limits.
    """
    def __init__(self, 
                 prompt_limit=None, 
                 token_limit=None, 
                 reset_period_hours=24,
                 admin_ips=None,
                 unlimited_ips=None):
        """
        Initialize the usage limiter with configurable settings.
        """
        self.prompt_limit = prompt_limit
        self.token_limit = token_limit
        self.reset_period = timedelta(hours=reset_period_hours)
        
        # Prefer unlimited_ips if provided, otherwise use admin_ips
        self.unlimited_ips = unlimited_ips or admin_ips or [
            "127.0.0.1",   # IPv4 localhost
            "::1",         # IPv6 localhost
            "localhost",   # Localhost hostname
            "0.0.0.0",     # All IPv4 interfaces
            "[::]"         # All IPv6 interfaces
        ]
        
        # Maintain admin_ips as an alias for compatibility
        self.admin_ips = self.unlimited_ips.copy()
        
        self.enabled = True
        self._usage_data = {}
        
    def track_usage(self, ip, tokens=None, **kwargs):
        """
        Track usage for a specific IP.
        
        Args:
            ip (str): IP address of the user.
            tokens (int, optional): Number of tokens used.
            **kwargs: Additional tracking information.
        
        Returns:
            dict: Updated usage data for the IP.
        """
        # Skip tracking for unlimited IPs
        if ip in self.unlimited_ips:
            return {}
        
        # Initialize usage data for IP if not exists
        if ip not in self._usage_data:
            self._usage_data[ip] = {
                'prompt_count': 0,
                'token_count': 0,
                'last_reset': datetime.now()
            }
        
        # Check if reset period has passed
        user_data = self._usage_data[ip]
        if datetime.now() - user_data['last_reset'] > self.reset_period:
            user_data['prompt_count'] = 0
            user_data['token_count'] = 0
            user_data['last_reset'] = datetime.now()
        
        # Increment usage
        user_data['prompt_count'] += 1
        
        # Track tokens if provided
        if tokens is not None:
            user_data['token_count'] += tokens
        
        return user_data
    
    def is_admin_ip(self, ip):
        """
        Check if the given IP is considered an admin IP.
        """
        # Normalize IP for comparison
        normalized_ip = str(ip).lower().strip()
        
        # Check for exact match or case-insensitive comparison
        for admin_ip in self.unlimited_ips:
            admin_ip = str(admin_ip).lower().strip()
            if normalized_ip == admin_ip:
                return True
        
        return False
    
    def add_admin_ip(self, ip):
        """
        Add a new admin IP.
        """
        normalized_ip = str(ip).lower().strip()
        if normalized_ip not in self.unlimited_ips:
            self.unlimited_ips.append(normalized_ip)
            self.admin_ips = self.unlimited_ips.copy()
        return True
    
    def update_limits(self, prompt_limit=None, token_limit=None, reset_period_hours=None):
        """
        Update usage limits.
        
        Args:
            prompt_limit (int, optional): New prompt limit.
            token_limit (int, optional): New token limit.
            reset_period_hours (int, optional): New reset period in hours.
        
        Returns:
            dict: Updated limit settings.
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
            "reset_period_hours": int(self.reset_period.total_seconds() / 3600)
        }

def initialize_usage_limiter():
    """
    Initialize and return a UsageLimiter instance.
    """
    # Try to load admin IPs from environment variable or configuration file
    try:
        # First, check if there's a config file
        config_path = os.path.join(os.path.dirname(__file__), 'admin_ips.txt')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_admin_ips = [line.strip() for line in f.readlines() if line.strip()]
        else:
            # Fallback to environment variable
            config_admin_ips = os.environ.get('ADMIN_IPS', '').split(',')
            config_admin_ips = [ip.strip() for ip in config_admin_ips if ip.strip()]
    except Exception:
        config_admin_ips = []
    
    # Combine default and configured admin IPs
    default_admin_ips = [
        "127.0.0.1", "::1", "localhost", 
        "0.0.0.0", "[::]"
    ]
    
    # Add any configured admin IPs to the default list
    admin_ips = list(set(default_admin_ips + config_admin_ips))
    
    return UsageLimiter(
        prompt_limit=20,  # Default 20 prompts per period
        token_limit=None,  # No token limit by default
        reset_period_hours=24,  # Reset every 24 hours
        unlimited_ips=admin_ips
    )

def save_admin_ip(ip):
    """
    Save admin IP to a configuration file or environment variable.
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
        if ip not in existing_ips:
            existing_ips.append(ip)
        
        # Write back to file
        with open(config_path, 'w') as f:
            for unique_ip in existing_ips:
                f.write(f"{unique_ip}\n")
        
        # Also update environment variable as a backup
        os.environ['ADMIN_IPS'] = ','.join(existing_ips)
        
        return True
    except Exception as e:
        st.error(f"Could not save admin IP: {e}")
        return False

def get_client_ip():
    """
    Retrieve the client's IP address.
    """
    # First, check Streamlit's runtime for client IP
    try:
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx:
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

def check_usage_limits(limiter=None):
    """
    Check current usage limits for the current user.
    
    Returns:
        tuple: (boolean indicating if usage is allowed, reason for limitation)
    """
    # If no limiter is provided, create a default one
    if limiter is None:
        limiter = initialize_usage_limiter()
    
    # Skip if usage limiting is disabled
    if not limiter.enabled:
        return True, "Usage limiting disabled"
    
    # Get client IP
    try:
        client_ip = get_client_ip()
    except Exception:
        # If unable to get IP, default to allowing access
        return True, "Unable to determine client IP"
    
    # Check for unlimited IPs
    if client_ip in limiter.unlimited_ips:
        return True, "Unlimited IP"
    
    # Track and check usage
    try:
        user_usage = limiter.track_usage(client_ip)
        
        # Check prompt limit
        if (limiter.prompt_limit is not None and 
            user_usage.get('prompt_count', 0) > limiter.prompt_limit):
            reason = f"Prompt limit exceeded. Max {limiter.prompt_limit} prompts per period."
            st.error(reason)
            return False, reason
        
        # Check token limit
        if (limiter.token_limit is not None and 
            user_usage.get('token_count', 0) > limiter.token_limit):
            reason = f"Token limit exceeded. Max {limiter.token_limit} tokens per period."
            st.error(reason)
            return False, reason
        
        return True, "Usage within limits"
    
    except Exception as e:
        reason = f"Error checking usage limits: {e}"
        st.error(reason)
        return True, reason  # Default to allowing access in case of errors


def track_query_usage(tokens=None, query=None, **kwargs):
    """
    Track usage for the current query.
    
    Args:
        tokens (int, optional): Number of tokens used in the query.
        query (str, optional): The query being tracked (ignored).
        **kwargs: Additional tracking information.
    
    Returns:
        dict: Updated usage data for the current user.
    """
    limiter = initialize_usage_limiter()
    client_ip = get_client_ip()
    
    # Pass through tokens and any additional keyword arguments
    return limiter.track_usage(client_ip, tokens, **kwargs)

def render_usage_admin_ui():
    """Render the admin UI for managing usage limits."""
    # Get or initialize the usage limiter
    limiter = initialize_usage_limiter()
    
    # Get client IP
    client_ip = get_client_ip()
    
    # Verbose debugging information
    st.write(f"Current Client IP: {'*' * len(client_ip)}")
    
    # Check admin access
    if not limiter.is_admin_ip(client_ip):
        st.error("Access Denied: Administrator access required.")
        
        # IP Management Section
        st.markdown("## IP Management")
        
        # Option to add current IP as admin
        if st.button(f"Add {client_ip} to Admin List"):
            # Add the current IP to admin IPs
            limiter.add_admin_ip(client_ip)
            
            # Attempt to save the IP
            if save_admin_ip(client_ip):
                st.success(f"Added {client_ip} to admin list. Refresh to access admin dashboard.")
            else:
                st.error("Failed to save admin IP.")
        
        # Manual IP entry option
        st.markdown("### Manual IP Entry")
        manual_ip = st.text_input("Enter IP to add to admin list")
        if st.button("Add Manual IP"):
            if manual_ip:
                limiter.add_admin_ip(manual_ip)
                
                # Save to persistent storage
                if save_admin_ip(manual_ip):
                    st.success(f"Added {manual_ip} to admin list. Refresh to access admin dashboard.")
                else:
                    st.error("Failed to save admin IP.")
        
        return
    
    # Admin Dashboard
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔒 Admin Controls")
    
    # Toggle usage limiting
    current_state = "Enabled" if limiter.enabled else "Disabled"
    if st.sidebar.button(f"Usage Limiting: {current_state}"):
        new_state = limiter.toggle_enabled()
        st.sidebar.success(f"Usage limiting {'enabled' if new_state else 'disabled'}")
    
    # Limit settings
    st.sidebar.markdown("### Limit Settings")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        prompt_limit = st.number_input(
            "Prompt Limit", 
            min_value=1,
            max_value=1000,
            value=limiter.prompt_limit or 20,
            help="Max prompts per user per day (0 = no limit)"
        )
    
    with col2:
        token_limit = st.number_input(
            "Token Limit", 
            min_value=0,
            max_value=1000000,
            value=limiter.token_limit or 0,
            help="Max tokens per user per day (0 = no limit)"
        )
    
    reset_hours = st.sidebar.slider(
        "Reset Period (hours)",
        min_value=1,
        max_value=168,
        value=int(limiter.reset_period.total_seconds() / 3600),
        help="Hours before usage counters reset"
    )
    
    if st.sidebar.button("Update Limits"):
        # Convert 0 to None for no limit
        prompt_limit_val = None if prompt_limit == 0 else prompt_limit
        token_limit_val = None if token_limit == 0 else token_limit
        
        new_limits = limiter.update_limits(
            prompt_limit=prompt_limit_val,
            token_limit=token_limit_val,
            reset_period_hours=reset_hours
        )
        st.sidebar.success(f"Limits updated: {json.dumps(new_limits)}")
    
    # IP Management
    st.sidebar.markdown("### IP Management")
    new_admin_ip = st.sidebar.text_input("Add New Admin IP")
    if st.sidebar.button("Add Admin IP") and new_admin_ip:
        limiter.add_admin_ip(new_admin_ip)
        
        # Save to persistent storage
        if save_admin_ip(new_admin_ip):
            st.sidebar.success(f"Added {new_admin_ip} to admin list")
        else:
            st.sidebar.error("Failed to save admin IP.")
    
    # Display current admin IPs
    st.sidebar.markdown("#### Current Unlimited IPs")
    admin_ips_display = "\n".join(limiter.unlimited_ips)
    st.sidebar.code(admin_ips_display)
    
    # Usage Statistics
    if st.sidebar.checkbox("Show Usage Statistics"):
        stats = limiter.get_usage_stats(client_ip)
        st.sidebar.json(stats)