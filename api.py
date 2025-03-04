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

# Import your existing RAG chatbot logic
import sys
sys.path.append('.')  # Add the current directory to path
from src.usage_limiter import UsageLimiter
from src.usage_integration import get_usage_data, check_admin_status

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

# Helper functions
def load_users():
    """Load users from JSON file"""
    try:
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, return empty dict
        return {}

def save_users(users):
    """Save users to JSON file"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(USER_DB_FILE), exist_ok=True)
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def update_user_schema():
    """Update existing users to include Stripe fields if they don't exist"""
    users = load_users()
    updated = False
    
    for user_id, user in users.items():
        if 'stripe_customer_id' not in user:
            user['stripe_customer_id'] = None
            updated = True
        if 'subscription_id' not in user:
            user['subscription_id'] = None
            updated = True
    
    if updated:
        save_users(users)
        print("Updated user schema with Stripe fields")

# Call this function during application startup
update_user_schema()

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
            current_user = load_users().get(payload['user_id'])
            
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
    users = load_users()
    
    # Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    email = data['email'].lower()
    
    # Check if user already exists
    for user_id, user in users.items():
        if user['email'] == email:
            return jsonify({'error': 'User already exists'}), 409
    
    # Create new user
    user_id = str(uuid.uuid4())
    users[user_id] = {
        'id': user_id,
        'email': email,
        'password_hash': generate_password_hash(data['password']),
        'plan': data.get('plan', 'free'),
        'created_at': datetime.datetime.utcnow().isoformat(),
        'last_login': None,
        'stripe_customer_id': None,  # Added field for Stripe customer ID
        'subscription_id': None      # Added field for Stripe subscription ID
    }
    
    save_users(users)
    
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
            'plan': users[user_id]['plan']
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Log in an existing user"""
    data = request.json
    users = load_users()
    
    # Validate input
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing email or password'}), 400
    
    email = data['email'].lower()
    
    # Find user by email
    user_id = None
    user = None
    
    for uid, u in users.items():
        if u['email'] == email:
            user_id = uid
            user = u
            break
    
    # Check if user exists and password is correct
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Update last login time
    users[user_id]['last_login'] = datetime.datetime.utcnow().isoformat()
    save_users(users)
    
    # Generate token
    token = jwt.encode({
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + TOKEN_EXPIRY
    }, JWT_SECRET_KEY)
    
    return jsonify({
        'token': token,
        'user': {
            'id': user_id,
            'email': user['email'],
            'plan': user['plan']
        }
    }), 200

# Chat API routes
@app.route('/api/chat', methods=['POST'])
def chat():
    """Process a chat message and return a response"""
    data = request.json
    client_ip = request.remote_addr
    
    if not data or not data.get('message'):
        return jsonify({'error': 'No message provided'}), 400
    
    message = data.get('message')
    user_id = data.get('user_id', 'anonymous')
    chat_history = data.get('history', [])
    
    # Check if the user is authenticated
    auth_header = request.headers.get('Authorization')
    user = None
    
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            users = load_users()
            user = users.get(payload['user_id'])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            # Token is invalid, but we'll still process as anonymous
            pass
    
    # Check usage limits if not a premium user
    if not user or user['plan'] != 'premium':
        try:
            is_allowed, reason = usage_limiter.check_limits(client_ip)
            if not is_allowed:
                return jsonify({
                    'error': f'You have reached your daily usage limit. {reason}'
                }), 429
        except Exception as e:
            print(f"Warning: Error checking usage limits: {str(e)}")
            # Continue processing even if limit checking fails
    
    # Process the request through your RAG chatbot
    try:
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
                
        # Log usage if not premium
        if not user or user['plan'] != 'premium':
            try:
                # Try track_request first (the method in your actual implementation)
                if hasattr(usage_limiter, 'track_request'):
                    usage_limiter.track_request(client_ip, tokens_used=0, request_type="api", request_data={"query": message[:100]})
                # Fall back to log_usage if track_request is not available
                elif hasattr(usage_limiter, 'log_usage'):
                    usage_limiter.log_usage(client_ip)
            except Exception as e:
                print(f"Warning: Failed to log usage: {e}")
                # Continue without logging usage
        
        # Always return a valid response
        return jsonify({'response': response_text}), 200
        
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

""" @app.route('/api/user/upgrade', methods=['POST'])
@token_required
def upgrade_plan(current_user):
    Upgrade user to premium plan
    # This would integrate with your payment processor (e.g., Stripe)
    # For now, we'll simulate a successful payment
    
    users = load_users()
    user_id = current_user['id']
    
    if users[user_id]['plan'] == 'premium':
        return jsonify({'message': 'User already has premium plan'}), 400
    
    # Update user plan
    users[user_id]['plan'] = 'premium'
    save_users(users)
    
    return jsonify({
        'message': 'Plan upgraded successfully',
        'plan': 'premium'
    }), 200 """

@app.route('/api/user/history', methods=['GET'])
@token_required
def get_chat_history(current_user):
    """Get user's chat history"""
    # This would require implementing chat history storage
    # For now, we'll return a placeholder
    return jsonify({
        'history': [
            {
                'id': '1',
                'timestamp': (datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat(),
                'messages': [
                    {'sender': 'user', 'text': 'What is Executive Order 13984?'},
                    {'sender': 'bot', 'text': 'Executive Order 13984 was issued on January 19, 2021, and...'} 
                ]
            }
        ]
    }), 200

# Admin routes
@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    """Get usage statistics - secured by admin password"""
    admin_password = request.headers.get('X-Admin-Password')
    
    if not admin_password or admin_password != ADMIN_PASSWORD:
        return jsonify({'error': 'Unauthorized access'}), 401
    
    # Get usage data from your existing module
    usage_data = get_usage_data()
    
    return jsonify(usage_data), 200
# Import the payment module
try:
    from src.payment_integration import create_subscription_for_user, verify_subscription_status
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    print("Stripe payment integration not available")

# Add these new routes to your api.py file:

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
            users = load_users()
            user_id = current_user['id']
            
            if user_id in users:
                users[user_id]['stripe_customer_id'] = result['customer_id']
                save_users(users)
        
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
            users = load_users()
            user_id = current_user['id']
            
            if user_id in users and users[user_id]['plan'] != 'premium':
                users[user_id]['plan'] = 'premium'
                save_users(users)
        
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
                users = load_users()
                for user_id, user in users.items():
                    if user.get('stripe_customer_id') == customer_id:
                        # Update user plan to premium
                        users[user_id]['plan'] = 'premium'
                        users[user_id]['subscription_id'] = subscription_id
                        save_users(users)
                        break
        
        elif event_type == 'customer.subscription.deleted':
            # Subscription was cancelled
            customer_id = event_data.get('customer')
            
            if customer_id:
                # Find user with this customer ID
                users = load_users()
                for user_id, user in users.items():
                    if user.get('stripe_customer_id') == customer_id:
                        # Downgrade user to free plan
                        users[user_id]['plan'] = 'free'
                        users[user_id].pop('subscription_id', None)
                        save_users(users)
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
                users = load_users()
                user_id = current_user['id']
                
                if user_id in users:
                    users[user_id]['stripe_customer_id'] = result['customer_id']
                    save_users(users)
            
            return jsonify({
                'message': 'Please complete the checkout process',
                'checkout_url': result['checkout_url'],
                'session_id': result['session_id']
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Error creating checkout session: {str(e)}'}), 500
    else:
        # If Stripe is not available, use the simulated payment
        users = load_users()
        user_id = current_user['id']
        
        if users[user_id]['plan'] == 'premium':
            return jsonify({'message': 'User already has premium plan'}), 400
        
        # Update user plan
        users[user_id]['plan'] = 'premium'
        save_users(users)
        
        return jsonify({
            'message': 'Plan upgraded successfully',
            'plan': 'premium'
        }), 200
    
    
if __name__ == '__main__':
    # Ensure the user database exists
    if not os.path.exists(USER_DB_FILE):
        save_users({})
    
    # Update existing user records with Stripe fields
    update_user_schema()
    
    # Run the Flask app
    app.run(debug=True, port=5000)