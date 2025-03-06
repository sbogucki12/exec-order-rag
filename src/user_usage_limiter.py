"""
user_usage_limiter.py - User-based usage limiting for Executive Orders RAG Chatbot
Handles tracking and enforcing usage limits based on user accounts
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UserUsageLimiter:
    """
    Handles user-based usage tracking and limiting for the chatbot.
    Enforces different limits for free vs premium users.
    """
    
    def __init__(self):
        """Initialize the usage limiter with configured limits"""
        # Get limits from environment variables or use defaults
        self.prompt_limit = int(os.environ.get('USER_PROMPT_LIMIT', '5'))  # Default is 5 for free
        self.token_limit = int(os.environ.get('USER_TOKEN_LIMIT', '2500'))
        self.reset_period_hours = int(os.environ.get('RESET_PERIOD_HOURS', '720'))  # 30 days default
        
        logger.info(f"Initialized UserUsageLimiter with limits: "
                   f"{self.prompt_limit} prompts, {self.token_limit} tokens, "
                   f"reset every {self.reset_period_hours} hours")
    
    def check_limits(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if a user has exceeded their usage limits.
        
        Args:
            user_id: User ID to check
            
        Returns:
            tuple: (is_allowed, reason)
        """
        try:
            from src.database import get_user_by_id, db
            
            # Get user information
            user = get_user_by_id(user_id)
            if not user:
                logger.warning(f"User not found: {user_id}")
                return False, "User not found"
            
            # Premium users have unlimited access
            if user.get('plan') == 'premium':
                return True, "Premium user"
            
            # For free users, check the usage stats
            current_month = datetime.now().strftime("%Y-%m")
            
            # Count prompts for the current month
            prompt_count = db.usage_stats.count_documents({
                "user_id": user_id,
                "timestamp": {"$regex": f"^{current_month}"},
                "type": "prompt"
            })
            
            # Check if limit is exceeded
            if prompt_count >= self.prompt_limit:
                logger.info(f"User {user_id} has reached prompt limit: {prompt_count}/{self.prompt_limit}")
                return False, f"Monthly prompt limit of {self.prompt_limit} reached"
            
            return True, f"Within limits ({prompt_count}/{self.prompt_limit} prompts used)"
            
        except Exception as e:
            logger.error(f"Error checking user limits: {e}")
            # If there's an error checking limits, allow the request but log it
            return True, f"Error checking limits: {e}"
    
    def track_request(self, user_id: str, tokens_used: int = 0, 
                     request_type: str = "prompt", request_data: Dict[str, Any] = None) -> None:
        """
        Track a user request in the database.
        
        Args:
            user_id: User ID
            tokens_used: Number of tokens used in this request
            request_type: Type of request (prompt, token_update, etc.)
            request_data: Additional data about the request
        """
        if request_data is None:
            request_data = {}
            
        try:
            from src.database import db
            
            # Create usage record
            usage_record = {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "tokens": tokens_used,
                "type": request_type,
                "data": request_data
            }
            
            # Insert into database
            db.usage_stats.insert_one(usage_record)
            logger.debug(f"Tracked usage for user {user_id}: {tokens_used} tokens")
            
        except Exception as e:
            logger.error(f"Error tracking user usage: {e}")
    
    def get_user_usage(self, user_id: str) -> Dict[str, Any]:
        """
        Get usage statistics for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            dict: Usage statistics
        """
        try:
            from src.database import db
            
            # Get usage records for this user
            records = list(db.usage_stats.find({"user_id": user_id}))
            
            # Calculate totals
            prompt_count = sum(1 for r in records if r.get('type') == 'prompt')
            token_count = sum(r.get('tokens', 0) for r in records)
            
            # Get last request and reset times
            last_request = None
            if records:
                last_record = max(records, key=lambda r: r.get('timestamp', ''))
                last_request = last_record.get('timestamp')
            
            # Format and return user usage data
            return {
                "prompt_count": prompt_count,
                "token_count": token_count,
                "last_request": last_request,
                "last_reset": None,  # This would need to be tracked separately
                "request_history": [
                    {
                        "timestamp": r.get('timestamp'),
                        "tokens": r.get('tokens', 0),
                        "type": r.get('type'),
                        "data": r.get('data', {})
                    }
                    for r in sorted(records, key=lambda x: x.get('timestamp', ''))[-20:]  # Last 20 requests
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting user usage: {e}")
            return {"error": str(e)}

def check_user_limit(user_id):
    """
    Check if user has reached their prompt limit (5 by default for free users).
    Debugs each step to identify issues.
    """
    from datetime import datetime
    import logging
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Checking limits for user: {user_id}")
    
    try:
        # Get user information
        from src.sql_database import get_user_by_id, get_connection
        
        # Debug user ID issue
        logger.info(f"Looking up user with ID: {user_id}")
        user = get_user_by_id(user_id)
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return {"allowed": False, "message": "User not found", "remaining": 0}
        
        logger.info(f"Found user: {user.get('email')} with plan: {user.get('plan')}")
        
        # Premium users have unlimited access
        if user.get("plan") == "premium":
            return {
                "allowed": True,
                "remaining": "unlimited",
                "message": "Premium user with unlimited access"
            }
        
        # For free users, enforce the 5 request limit
        # Calculate the current month
        current_month = datetime.now().strftime("%Y-%m")
        logger.info(f"Checking usage for month: {current_month}")
        
        # Count prompts used in current month - WITH DEBUGGING
        conn = get_connection()
        cursor = conn.cursor()
        
        # Debug the SQL query being executed
        sql_query = """
        SELECT COUNT(*) as prompt_count
        FROM UsageStats
        WHERE UserID = ? AND Type = 'prompt' AND SUBSTRING(CONVERT(varchar, Timestamp, 120), 1, 7) = ?
        """
        logger.info(f"Executing query: {sql_query} with params: {user_id}, {current_month}")
        
        cursor.execute(sql_query, (user_id, current_month))
        row = cursor.fetchone()
        
        # Debug the result
        if row:
            logger.info(f"Query returned: {row}")
            prompt_count = row[0]
        else:
            logger.warning("Query returned no results")
            prompt_count = 0
            
        cursor.close()
        conn.close()
        
        # Default limit is 5 for free users
        limit = 5
        remaining = max(0, limit - prompt_count)
        
        logger.info(f"User has used {prompt_count}/{limit} prompts this month, {remaining} remaining")
        
        return {
            "allowed": prompt_count < limit,
            "remaining": remaining,
            "message": f"You have {remaining} requests remaining this month" if remaining > 0 else "Monthly limit reached"
        }
    except Exception as e:
        logger.error(f"Error checking user limits: {e}", exc_info=True)
        # Allow the request if there's a database issue, to prevent blocking users
        return {"allowed": True, "message": f"Error checking limits: {e}", "remaining": 5}