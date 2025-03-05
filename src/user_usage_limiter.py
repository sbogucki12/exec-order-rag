"""
user_usage_limiter.py - Module for tracking and limiting usage on a per-user basis
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional, Any
from src.database import get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UserUsageLimiter:
    """Class to track and limit user API usage based on user_id rather than IP"""
    
    def __init__(self):
        """Initialize the user usage limiter"""
        # Get settings from environment or use defaults
        self.enabled = os.environ.get('USAGE_LIMITING_ENABLED', 'True').lower() == 'true'
        self.prompt_limit = int(os.environ.get('USER_PROMPT_LIMIT', '50'))
        self.token_limit = int(os.environ.get('USER_TOKEN_LIMIT', '25000'))
        self.reset_period_hours = int(os.environ.get('RESET_PERIOD_HOURS', '24'))
        
        # Initialize database connection
        self.db = get_db()
        
        # Create index on user_id if it doesn't exist
        self.db.user_usage.create_index("user_id", unique=True)
        
        logger.info(f"User usage limiter initialized with limits: {self.prompt_limit} prompts, {self.token_limit} tokens")
    
    def check_limits(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if a user has exceeded usage limits
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Tuple[bool, str]: (is_allowed, reason)
        """
        if not self.enabled:
            return True, "Usage limiting disabled"
            
        if not user_id:
            # If no user_id provided, allow access but warn
            logger.warning("check_limits called without user_id")
            return True, "No user ID provided"
        
        # Get current usage data for user
        usage = self.db.user_usage.find_one({"user_id": user_id})
        
        # If no usage data found, user hasn't used the system yet
        if not usage:
            return True, "No previous usage"
        
        # Check if we should reset the counters based on time elapsed
        last_reset = usage.get("last_reset")
        if last_reset:
            last_reset_time = datetime.fromisoformat(last_reset) if isinstance(last_reset, str) else last_reset
            time_elapsed = datetime.utcnow() - last_reset_time
            
            if time_elapsed > timedelta(hours=self.reset_period_hours):
                # Reset the usage counters
                self.reset_usage(user_id)
                return True, f"Usage reset after {self.reset_period_hours} hours"
        
        # Check prompt limit
        prompt_count = usage.get("prompt_count", 0)
        if self.prompt_limit is not None and prompt_count >= self.prompt_limit:
            return False, f"Prompt limit exceeded: {prompt_count}/{self.prompt_limit} prompts used"
        
        # Check token limit
        token_count = usage.get("token_count", 0)
        if self.token_limit is not None and token_count >= self.token_limit:
            return False, f"Token limit exceeded: {token_count}/{self.token_limit} tokens used"
        
        # User is within limits
        return True, f"Usage within limits: {prompt_count}/{self.prompt_limit} prompts used"
    
    def track_request(self, user_id: str, tokens_used: int = 0, 
                     request_type: str = "prompt", request_data: Optional[Dict] = None) -> None:
        """
        Track a user request
        
        Args:
            user_id: Unique identifier for the user
            tokens_used: Number of tokens used in this request
            request_type: Type of request (e.g., 'prompt', 'token_update')
            request_data: Additional data about the request
        """
        if not self.enabled or not user_id:
            return
        
        # Create history entry
        history_entry = {
            "timestamp": datetime.utcnow(),
            "type": request_type,
            "tokens": tokens_used
        }
        if request_data:
            history_entry["data"] = request_data
        
        # Get current time
        now = datetime.utcnow()
        today = now.strftime("%Y-%m-%d")
        
        # Update usage data in database
        self.db.user_usage.update_one(
            {"user_id": user_id},
            {
                "$inc": {
                    "prompt_count": 1 if request_type == "prompt" else 0,
                    "token_count": tokens_used,
                    f"daily.{today}.prompt_count": 1 if request_type == "prompt" else 0,
                    f"daily.{today}.token_count": tokens_used
                },
                "$set": {
                    "last_request": now,
                    "last_reset": {"$cond": [{"$eq": ["$last_reset", None]}, now, "$last_reset"]}
                },
                "$push": {"request_history": history_entry}
            },
            upsert=True
        )
        
        logger.debug(f"Tracked usage for user {user_id}: {tokens_used} tokens, type={request_type}")
    
    def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a specific user
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dict with usage statistics
        """
        usage = self.db.user_usage.find_one({"user_id": user_id})
        
        if not usage:
            return {
                "user_id": user_id,
                "prompt_count": 0,
                "token_count": 0,
                "last_request": None,
                "last_reset": None,
                "daily": {},
                "request_history": []
            }
        
        # Format timestamps for JSON serialization
        if isinstance(usage.get("last_request"), datetime):
            usage["last_request"] = usage["last_request"].isoformat()
        if isinstance(usage.get("last_reset"), datetime):
            usage["last_reset"] = usage["last_reset"].isoformat()
            
        # Format history timestamps
        for entry in usage.get("request_history", []):
            if isinstance(entry.get("timestamp"), datetime):
                entry["timestamp"] = entry["timestamp"].isoformat()
        
        return usage
    
    def reset_usage(self, user_id: str) -> bool:
        """
        Reset usage counters for a user
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            now = datetime.utcnow()
            
            result = self.db.user_usage.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "prompt_count": 0,
                        "token_count": 0,
                        "last_reset": now,
                        "daily": {},
                        # Keep the history but add a reset marker
                        "$push": {
                            "request_history": {
                                "timestamp": now,
                                "type": "reset",
                                "tokens": 0
                            }
                        }
                    }
                }
            )
            
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error resetting usage for user {user_id}: {e}")
            return False
    
    def get_all_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for all users
        
        Returns:
            Dict with aggregated usage statistics
        """
        try:
            # Get all user usage records
            cursor = self.db.user_usage.find()
            
            usage_by_user = {}
            total_requests = 0
            total_tokens = 0
            active_users = 0
            
            for usage in cursor:
                user_id = usage.get("user_id")
                prompt_count = usage.get("prompt_count", 0)
                token_count = usage.get("token_count", 0)
                
                # Format for display
                usage_by_user[user_id] = {
                    "prompt_count": prompt_count,
                    "token_count": token_count,
                    "last_request": usage.get("last_request").isoformat() if isinstance(usage.get("last_request"), datetime) else usage.get("last_request"),
                    "last_reset": usage.get("last_reset").isoformat() if isinstance(usage.get("last_reset"), datetime) else usage.get("last_reset"),
                    "daily": usage.get("daily", {}),
                }
                
                # Update totals
                total_requests += prompt_count
                total_tokens += token_count
                active_users += 1
            
            return {
                "usage_by_user": usage_by_user,
                "totals": {
                    "total_requests": total_requests,
                    "total_tokens": total_tokens,
                    "active_users": active_users
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                "error": str(e),
                "usage_by_user": {},
                "totals": {
                    "total_requests": 0,
                    "total_tokens": 0,
                    "active_users": 0
                }
            }