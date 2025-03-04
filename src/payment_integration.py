"""
Payment integration module using Stripe
"""

import os
import stripe
import json
import logging
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Stripe with API key
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY')

# Define product and price IDs
PREMIUM_PRICE_ID = os.environ.get('STRIPE_PREMIUM_PRICE_ID')

class PaymentHandler:
    """
    Handle Stripe payment operations for subscription management
    """
    
    @staticmethod
    def create_customer(email: str, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new Stripe customer
        
        Args:
            email: Customer email
            name: Optional customer name
            
        Returns:
            dict: Stripe customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name
            )
            logger.info(f"Created Stripe customer: {customer.id}")
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}")
            raise
    
    @staticmethod
    def create_checkout_session(customer_id: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
        """
        Create a checkout session for subscription
        
        Args:
            customer_id: Stripe customer ID
            success_url: URL to redirect on successful payment
            cancel_url: URL to redirect on cancelled payment
            
        Returns:
            dict: Checkout session object
        """
        try:
            if not PREMIUM_PRICE_ID:
                raise ValueError("Missing STRIPE_PREMIUM_PRICE_ID environment variable")
            
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': PREMIUM_PRICE_ID,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
            )
            
            logger.info(f"Created checkout session: {session.id}")
            return session
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise
    
    @staticmethod
    def cancel_subscription(subscription_id: str) -> Dict[str, Any]:
        """
        Cancel a subscription
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            dict: Cancelled subscription object
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            
            logger.info(f"Cancelled subscription: {subscription_id}")
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {str(e)}")
            raise
    
    @staticmethod
    def get_subscription(subscription_id: str) -> Dict[str, Any]:
        """
        Get subscription details
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            dict: Subscription object
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving subscription: {str(e)}")
            raise
    
    @staticmethod
    def get_customer_subscriptions(customer_id: str) -> Dict[str, Any]:
        """
        Get all subscriptions for a customer
        
        Args:
            customer_id: Stripe customer ID
            
        Returns:
            dict: List of subscription objects
        """
        try:
            subscriptions = stripe.Subscription.list(
                customer=customer_id,
                status='all',
                limit=100
            )
            return subscriptions
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error listing subscriptions: {str(e)}")
            raise
    
    @staticmethod
    def handle_webhook(payload: Dict[str, Any], signature: str, endpoint_secret: str) -> Tuple[str, Dict[str, Any]]:
        """
        Handle Stripe webhook events
        
        Args:
            payload: Webhook request body
            signature: Stripe signature header
            endpoint_secret: Webhook endpoint secret
            
        Returns:
            tuple: (event type, event data)
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, endpoint_secret
            )
            
            # Handle specific events
            event_type = event['type']
            event_data = event['data']['object']
            
            logger.info(f"Received Stripe webhook: {event_type}")
            
            return event_type, event_data
            
        except ValueError as e:
            # Invalid payload
            logger.error(f"Invalid payload in webhook: {str(e)}")
            raise
        except stripe.error.SignatureVerificationError as e:
            # Invalid signature
            logger.error(f"Invalid signature in webhook: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise

# Helper functions for the API
def create_subscription_for_user(email: str, name: Optional[str] = None, success_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
    """
    Create a customer and checkout session for a new subscription
    
    Args:
        email: Customer email
        name: Optional customer name
        success_url: URL to redirect on successful payment
        cancel_url: URL to redirect on cancelled payment
        
    Returns:
        dict: Session information with URL
    """
    # Default URLs if not provided
    if not success_url:
        success_url = os.environ.get('STRIPE_SUCCESS_URL', 'http://localhost:3000/subscription/success')
    if not cancel_url:
        cancel_url = os.environ.get('STRIPE_CANCEL_URL', 'http://localhost:3000/subscription/cancel')
    
    # Create or retrieve customer
    try:
        # Try to find existing customer by email
        customers = stripe.Customer.list(email=email, limit=1)
        if customers and customers.data:
            customer = customers.data[0]
            logger.info(f"Found existing customer: {customer.id}")
        else:
            # Create new customer
            customer = PaymentHandler.create_customer(email, name)
        
        # Create checkout session
        session = PaymentHandler.create_checkout_session(
            customer_id=customer.id,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return {
            'session_id': session.id,
            'checkout_url': session.url,
            'customer_id': customer.id
        }
    
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise

def verify_subscription_status(customer_id: str) -> Dict[str, Any]:
    """
    Verify if a customer has an active subscription
    
    Args:
        customer_id: Stripe customer ID
        
    Returns:
        dict: Subscription status information
    """
    try:
        subscriptions = PaymentHandler.get_customer_subscriptions(customer_id)
        
        active_subscription = None
        
        # Find active subscription
        for subscription in subscriptions.data:
            if subscription.status == 'active':
                active_subscription = subscription
                break
        
        if active_subscription:
            # Get the current period end as timestamp
            current_period_end = active_subscription.current_period_end
            
            return {
                'has_active_subscription': True,
                'subscription_id': active_subscription.id,
                'status': active_subscription.status,
                'current_period_end': current_period_end,
                'cancel_at_period_end': active_subscription.cancel_at_period_end
            }
        else:
            return {
                'has_active_subscription': False
            }
    
    except Exception as e:
        logger.error(f"Error verifying subscription: {str(e)}")
        raise