"""
api.py - Flask API for Executive Orders RAG Chatbot
Provides endpoints for authentication, chat, and user management
"""

import os
import json
import uuid
import datetime
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import re

# Import your existing RAG chatbot logic
import sys
sys.path.append('.')  # Add the current directory to path
from src.usage_limiter import UsageLimiter
from src.usage_integration import get_usage_data, check_admin_status
""" from src.database import (
    get_users, get_user_by_id, get_user_by_email, create_user, update_user,
    save_chat_message, get_chat_history, get_conversation,
    track_usage, check_usage_limits, migrate_from_json, setup_admin_collection,
    is_admin_ip, add_admin_ip
) """
# Import database configuration
from src.db_config import DB_TYPE

# Import the appropriate database module based on configuration
if DB_TYPE == 'mongodb':
    from src.database import (
        get_users, get_user_by_id, get_user_by_email, create_user, update_user,
        save_chat_message, get_chat_history, get_conversation, delete_conversation,
        track_usage, check_usage_limits, migrate_from_json, setup_admin_collection,
        is_admin_ip, add_admin_ip, delete_user
    )
else:
    from src.sql_database import (
        get_users, get_user_by_id, get_user_by_email, create_user, update_user,
        save_chat_message, get_chat_history, get_conversation, delete_conversation,
        track_usage, check_usage_limits, migrate_from_json, setup_admin_collection,
        is_admin_ip, add_admin_ip, delete_user, verify_tables_exist
    )

# Import non-Streamlit chatbot processing function
try:
    from api_chatbot import process_query
    print("Successfully imported API chatbot")
except ImportError:
    # Fallback function if the API chatbot isn't available
    def process_query(query, chat_history=None):
        return f"This is a placeholder response for: {query}"
    print("Using fallback chatbot")

# Try to import your chatbot processing function
# Define a fallback function that doesn't rely on Streamlit
def process_query_fallback(query):
    """Fallback function for processing queries without Streamlit"""
    return f"This is a placeholder response for: {query}"

# Use the fallback function to avoid Streamlit session state issues
# process_query = process_query_fallback

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-dev-secret-key-change-in-production')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin-password-change-in-production')
USER_DB_FILE = 'data/users.json'
TOKEN_EXPIRY = datetime.timedelta(days=1)
api_key = os.getenv("AZURE_AI_FOUNDRY_API_KEY")
endpoint = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
model_name = os.getenv("AZURE_AI_FOUNDRY_MODEL_NAME")

if not api_key or not endpoint or not model_name:
    print("Error: Missing Azure AI Foundry environment variables!")

# Initialize the usage limiter with error handling
try:
    usage_limiter = UsageLimiter()
except Exception as e:
    print(f"Warning: Failed to initialize UsageLimiter: {e}")
    # Create a dummy limiter that always allows usage
    class DummyLimiter:
        def check_limits(self, ip):
            return True, "Dummy limiter always allows usage"
        def log_usage(self, ip):
            pass
        def track_request(self, ip, tokens_used=0, request_type="api", request_data=None):
            pass
    usage_limiter = DummyLimiter()

# Set up the admin collection/table for storing configuration
setup_admin_collection()
verify_tables_exist() 

# Migrate existing user data from JSON if file exists
if os.path.exists(USER_DB_FILE):
    try:
        print(f"Attempting to migrate users from {USER_DB_FILE} to database...")
        migrate_from_json(USER_DB_FILE)
        print("Migration completed successfully.")
        # Rename the old file to avoid future migrations
        os.rename(USER_DB_FILE, f"{USER_DB_FILE}.migrated")
    except Exception as e:
        print(f"Error during migration: {e}")

# Helper functions
def get_client_ip():
    """Get the client's IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

def token_required(f):
    """Decorator for JWT token authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode token
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = get_user_by_id(payload['user_id'])
            
            if not current_user:
                return jsonify({'error': 'Invalid token'}), 401
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Authentication routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.json
    
    # Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    email = data['email'].lower()
    
    # Check if user already exists
    existing_user = get_user_by_email(email)
    if existing_user:
        return jsonify({'error': 'User already exists'}), 409
    
    # Create new user
    user_data = {
        'email': email,
        'password_hash': generate_password_hash(data['password']),
        'plan': data.get('plan', 'free'),
        'created_at': datetime.datetime.utcnow().isoformat(),
        'last_login': None,
        'stripe_customer_id': None,
        'subscription_id': None
    }
    
    user_id = create_user(user_data)
    
    if not user_id:
        return jsonify({'error': 'Failed to create user'}), 500
    
    # Generate token
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + TOKEN_EXPIRY
    }, JWT_SECRET_KEY)
    
    return jsonify({
        'token': token,
        'user': {
            'id': user_id,
            'email': email,
            'plan': user_data['plan']
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Log in an existing user"""
    data = request.json
    
    # Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    email = data['email'].lower()
    
    # Find user by email
    user = get_user_by_email(email)
    
    # Check if user exists and password is correct
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Update last login time
    update_user(user['id'], {'last_login': datetime.datetime.utcnow().isoformat()})
    
    # Generate token
    token = jwt.encode({
        'user_id': user['id'],
        'exp': datetime.datetime.utcnow() + TOKEN_EXPIRY
    }, JWT_SECRET_KEY)
    
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'plan': user['plan']
        }
    }), 200

# Chat API routes
@app.route('/api/chat', methods=['POST'])
def chat():
    """Process a chat message and return a response"""
    data = request.json
    client_ip = get_client_ip()
    
    if not data or not data.get('message'):
        return jsonify({'error': 'No message provided'}), 400
    
    message = data.get('message')
    conversation_id = data.get('conversation_id', str(uuid.uuid4()))
    chat_history = data.get('history', [])
    
    # Check if the user is authenticated
    auth_header = request.headers.get('Authorization')
    user = None
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            user = get_user_by_id(payload['user_id'])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            # Token is invalid, but we'll still process as anonymous
            pass
    
    # For authenticated users
    if user:
        # Check if user is premium
        if user['plan'] != 'premium':
            try:
                # Use the enhanced check_user_limit function that returns more detailed information
                from src.user_usage_limiter import check_user_limit
                
                limit_check = check_user_limit(user['id'])
                if not limit_check['allowed']:
                    return jsonify({
                        'error': f'You have reached your usage limit. {limit_check["message"]}',
                        'remaining': limit_check.get('remaining', 0)
                    }), 429
            except Exception as e:
                print(f"Warning: Error checking user usage limits: {str(e)}")
                # Continue processing even if limit checking fails
    else:
        # Fall back to IP-based limiting for anonymous users
        try:
            # Get limits from environment or use defaults
            prompt_limit = int(os.environ.get('PROMPT_LIMIT', 5))  # Reduced default to 5
            token_limit = int(os.environ.get('TOKEN_LIMIT', 2500))
            
            is_allowed, reason = check_usage_limits(client_ip, prompt_limit, token_limit)
            if not is_allowed:
                return jsonify({
                    'error': f'You have reached your usage limit. {reason}'
                }), 429
        except Exception as e:
            print(f"Warning: Error checking usage limits: {str(e)}")
            # Continue processing even if limit checking fails
    
    # Process the request through your RAG chatbot
    try:
        # Look for EO number in the query for formatting context
        eo_context = {}
        eo_match = re.search(r'executive order (\d+)', message, re.IGNORECASE)
        if eo_match:
            eo_context['eo_number'] = eo_match.group(1)
        
        # Handle the case where process_query might not accept chat_history
        response_text = None
        try:
            # Try calling with both arguments
            response_text = process_query(message, chat_history)
        except TypeError as e:
            # If the function doesn't accept the chat_history parameter, call it without it
            if "positional argument" in str(e):
                response_text = process_query(message)
            else:
                raise
        
        # Ensure we have a valid response
        if response_text is None:
            response_text = f"Sorry, I couldn't process your question about: {message}"
        
        # Format the response for better readability
        
        from src.response_formatter import format_response
        
        if response_text:
        # Log before formatting
            print("BEFORE FORMATTING:")
            print(response_text[:200] + "...")
            
            # Apply formatting
            try:
                formatted_response = format_response(response_text, eo_context)
                print("AFTER FORMATTING:")
                print(formatted_response[:200] + "...")
            except Exception as e:
                print(f"Formatting error: {e}")
                formatted_response = response_text  # Fall back to unformatted response
        formatted_response = format_response(response_text, eo_context)

        # Log usage
        try:
            # Estimate token usage - this is a very basic estimation
            token_estimate = len(message.split()) + len(response_text.split())
            
            # Track in database based on user or IP
            if user:
                # Track user-based usage
                user_limiter.track_request(
                    user['id'], 
                    token_estimate, 
                    "prompt", 
                    {"query": message[:100]}
                )
            else:
                # Fall back to IP-based tracking
                track_usage(client_ip, token_estimate, "prompt", {"query": message[:100]})
                
        except Exception as e:
            print(f"Warning: Failed to log usage: {e}")
        
        # Save to chat history if user is authenticated
        if user:
            user_message = {
                "sender": "user",
                "text": message,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            bot_message = {
                "sender": "bot",
                "text": formatted_response,  # Store the formatted response
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
            
            # Save both messages
            save_chat_message(user["id"], conversation_id, user_message)
            save_chat_message(user["id"], conversation_id, bot_message)
        
        # Always return a valid response - now with formatting
        return jsonify({
            'response': formatted_response,
            'conversation_id': conversation_id
        }), 200
        
    except Exception as e:
        # Handle any errors during processing
        error_message = f"Error processing request: {str(e)}"
        print(f"Error in chat endpoint: {error_message}")
        return jsonify({'error': error_message}), 500
    
# User routes
@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get user profile information"""
    return jsonify({
        'id': current_user['id'],
        'email': current_user['email'],
        'plan': current_user['plan'],
        'created_at': current_user['created_at'],
        'last_login': current_user['last_login']
    }), 200

@app.route('/api/user/history', methods=['GET'])
@token_required
def get_user_chat_history(current_user):
    """Get user's chat history"""
    # Get actual chat history from database
    limit = request.args.get('limit', 10, type=int)
    history = get_chat_history(current_user['id'], limit)
    
    return jsonify({'history': history}), 200

@app.route('/api/user/history/<conversation_id>', methods=['GET'])
@token_required
def get_specific_conversation(current_user, conversation_id):
    """Get a specific conversation"""
    conversation = get_conversation(current_user['id'], conversation_id)
    
    if not conversation:
        return jsonify({'error': 'Conversation not found'}), 404
    
    return jsonify(conversation), 200

@app.route('/api/user/history/<conversation_id>', methods=['DELETE'])
@token_required
def delete_specific_conversation(current_user, conversation_id):
    """Delete a specific conversation"""
    from src.database import delete_conversation
    
    success = delete_conversation(current_user['id'], conversation_id)
    
    if not success:
        return jsonify({'error': 'Failed to delete conversation'}), 500
    
    return jsonify({'message': 'Conversation deleted successfully'}), 200

# Admin routes
@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    """Get usage statistics - secured by admin password"""
    admin_password = request.headers.get('X-Admin-Password')
    client_ip = get_client_ip()
    
    if not admin_password or admin_password != ADMIN_PASSWORD:
        if not is_admin_ip(client_ip):
            return jsonify({'error': 'Unauthorized access'}), 401
    
    # Get usage data from database
    from src.database import get_usage_stats
    usage_data = get_usage_stats()
    
    return jsonify(usage_data), 200

@app.route('/api/admin/set-admin', methods=['POST'])
def set_admin_status():
    """Set admin status for an IP"""
    admin_password = request.headers.get('X-Admin-Password')
    data = request.json
    
    if not admin_password or admin_password != ADMIN_PASSWORD:
        return jsonify({'error': 'Unauthorized access'}), 401
    
    if not data or 'ip' not in data:
        return jsonify({'error': 'IP address is required'}), 400
    
    ip = data['ip']
    is_admin = data.get('is_admin', True)
    
    if is_admin:
        add_admin_ip(ip)
    else:
        # Remove admin status - not implemented yet
        pass
    
    return jsonify({'message': f"Admin status for {ip} set to {is_admin}"}), 200

# Import the payment module
try:
    from src.payment_integration import create_subscription_for_user, verify_subscription_status
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    print("Stripe payment integration not available")

# Payment routes
@app.route('/api/payment/create-checkout', methods=['POST'])
@token_required
def create_checkout_session(current_user):
    """Create a checkout session for subscription"""
    if not STRIPE_AVAILABLE:
        return jsonify({'error': 'Payment system not available'}), 503
    
    try:
        # Get the success and cancel URLs
        data = request.json or {}
        success_url = data.get('success_url')
        cancel_url = data.get('cancel_url')
        
        # Create subscription
        result = create_subscription_for_user(
            email=current_user['email'],
            name=data.get('name'),
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        # Save the Stripe customer ID to the user record
        if 'customer_id' in result:
            update_user(current_user['id'], {'stripe_customer_id': result['customer_id']})
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': f'Error creating checkout session: {str(e)}'}), 500

@app.route('/api/payment/subscription-status', methods=['GET'])
@token_required
def check_subscription_status(current_user):
    """Check the status of a user's subscription"""
    if not STRIPE_AVAILABLE:
        return jsonify({'error': 'Payment system not available'}), 503
    
    try:
        # Get the Stripe customer ID
        customer_id = current_user.get('stripe_customer_id')
        
        if not customer_id:
            return jsonify({
                'has_active_subscription': False,
                'message': 'No subscription information found'
            }), 200
        
        # Verify subscription status
        status = verify_subscription_status(customer_id)
        
        # If the user has an active subscription, make sure their plan is set to premium
        if status.get('has_active_subscription', False):
            if current_user['plan'] != 'premium':
                update_user(current_user['id'], {'plan': 'premium'})
        
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'error': f'Error checking subscription: {str(e)}'}), 500

@app.route('/api/payment/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events"""
    if not STRIPE_AVAILABLE:
        return jsonify({'error': 'Payment system not available'}), 503
    
    try:
        from src.payment_integration import PaymentHandler
        
        # Get webhook secret from environment
        endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
        
        if not endpoint_secret:
            return jsonify({'error': 'Webhook secret not configured'}), 500
        
        # Get the payload and signature
        payload = request.data
        signature = request.headers.get('Stripe-Signature')
        
        # Handle the webhook
        event_type, event_data = PaymentHandler.handle_webhook(
            payload=payload,
            signature=signature,
            endpoint_secret=endpoint_secret
        )
        
        # Process different event types
        if event_type == 'checkout.session.completed':
            # Payment was successful
            customer_id = event_data.get('customer')
            subscription_id = event_data.get('subscription')
            
            if customer_id:
                # Find user with this customer ID
                users = get_users()
                for user_id, user in users.items():
                    if user.get('stripe_customer_id') == customer_id:
                        # Update user plan to premium
                        update_user(user_id, {
                            'plan': 'premium',
                            'subscription_id': subscription_id
                        })
                        break
        
        elif event_type == 'customer.subscription.deleted':
            # Subscription was cancelled
            customer_id = event_data.get('customer')
            
            if customer_id:
                # Find user with this customer ID
                users = get_users()
                for user_id, user in users.items():
                    if user.get('stripe_customer_id') == customer_id:
                        # Downgrade user to free plan
                        update_user(user_id, {
                            'plan': 'free',
                            'subscription_id': None
                        })
                        break
        
        # Acknowledge receipt of the event
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error processing webhook: {str(e)}'}), 400

# Update the existing upgrade endpoint to use Stripe
@app.route('/api/user/upgrade', methods=['POST'])
@token_required
def upgrade_plan(current_user):
    """Upgrade user to premium plan"""
    if STRIPE_AVAILABLE:
        # If Stripe is available, create a checkout session
        try:
            data = request.json or {}
            
            # Create subscription
            result = create_subscription_for_user(
                email=current_user['email'],
                success_url=data.get('success_url'),
                cancel_url=data.get('cancel_url')
            )
            
            # Save the Stripe customer ID to the user record
            if 'customer_id' in result:
                update_user(current_user['id'], {'stripe_customer_id': result['customer_id']})
            
            return jsonify({
                'message': 'Please complete the checkout process',
                'checkout_url': result['checkout_url'],
                'session_id': result['session_id']
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Error creating checkout session: {str(e)}'}), 500
    else:
        # If Stripe is not available, use the simulated payment
        if current_user['plan'] == 'premium':
            return jsonify({'message': 'User already has premium plan'}), 400
        
        # Update user plan
        update_user(current_user['id'], {'plan': 'premium'})
        
        return jsonify({
            'message': 'Plan upgraded successfully',
            'plan': 'premium'
        }), 200
    
@app.route('/api/user/delete-account', methods=['DELETE'])
@token_required
def delete_user_account(current_user):
    user_id = current_user['id']
    
    try:
        # First, check if this is a premium user with an active subscription
        if current_user.get('plan') == 'premium' and current_user.get('stripe_customer_id'):
            # If Stripe integration is available, we should cancel their subscription
            if STRIPE_AVAILABLE and current_user.get('subscription_id'):
                try:
                    from src.payment_integration import cancel_subscription
                    cancel_subscription(current_user['subscription_id'])
                    print(f"Cancelled subscription for user {user_id}")
                except Exception as e:
                    print(f"Failed to cancel subscription: {e}")
                    # Continue with deletion even if subscription cancellation fails
        
        # Delete the user account (this will delete all associated data)
        success = delete_user(user_id)
        
        if not success:
            return jsonify({"error": "Failed to delete user account"}), 500
        
        print(f"Successfully deleted user account {user_id}")
        return jsonify({"message": "Account successfully deleted"}), 200
        
    except Exception as e:
        print(f"Error deleting user account {user_id}: {e}")
        return jsonify({"error": f"Failed to delete account: {str(e)}"}), 500

@app.route('/api/user/usage', methods=['GET'])
@token_required
def get_user_usage_stats(current_user):
    """Get usage statistics for the current user"""
    # Import user limiter
    from src.user_usage_limiter import UserUsageLimiter
    user_limiter = UserUsageLimiter()
    
    # Get user's usage data
    usage_data = user_limiter.get_user_usage(current_user['id'])
    
    # Get the limits for context
    prompt_limit = int(os.environ.get('USER_PROMPT_LIMIT', '50'))
    token_limit = int(os.environ.get('USER_TOKEN_LIMIT', '25000'))
    reset_period_hours = int(os.environ.get('RESET_PERIOD_HOURS', '24'))
    
    # Calculate time until reset if last_reset is available
    time_until_reset = None
    if usage_data.get('last_reset'):
        try:
            last_reset_time = datetime.datetime.fromisoformat(usage_data['last_reset'])
            next_reset_time = last_reset_time + datetime.timedelta(hours=reset_period_hours)
            time_until_reset = (next_reset_time - datetime.datetime.utcnow()).total_seconds()
            
            # Format as hours and minutes
            if time_until_reset > 0:
                hours = int(time_until_reset // 3600)
                minutes = int((time_until_reset % 3600) // 60)
                time_until_reset = f"{hours}h {minutes}m"
            else:
                time_until_reset = "Reset pending"
        except Exception as e:
            print(f"Error calculating reset time: {e}")
            time_until_reset = "Unknown"
    
    # Return usage data with context
    return jsonify({
        'usage': {
            'prompt_count': usage_data.get('prompt_count', 0),
            'token_count': usage_data.get('token_count', 0),
            'last_request': usage_data.get('last_request'),
            'last_reset': usage_data.get('last_reset')
        },
        'limits': {
            'prompt_limit': prompt_limit,
            'token_limit': token_limit,
            'reset_period_hours': reset_period_hours,
            'time_until_reset': time_until_reset
        },
        'remaining': {
            'prompts': max(0, prompt_limit - usage_data.get('prompt_count', 0)),
            'tokens': max(0, token_limit - usage_data.get('token_count', 0))
        },
        # Include the most recent 10 requests for historical context
        'recent_requests': usage_data.get('request_history', [])[-10:]
    }), 200
   
if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, port=5000)