import React, { useState, useEffect } from 'react';
import { userService } from '../services/api';

const SubscriptionStatus = ({ user, onUpgrade }) => {
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    // Skip if user is not authenticated
    if (!user) {
      setLoading(false);
      return;
    }

    // Check subscription status
    const checkSubscription = async () => {
      try {
        const status = await userService.getSubscriptionStatus();
        setSubscription(status);
      } catch (err) {
        console.error('Error checking subscription:', err);
        setError('Could not retrieve subscription information');
      } finally {
        setLoading(false);
      }
    };

    checkSubscription();
  }, [user]);

  // Format date
  const formatDate = (timestamp) => {
    if (!timestamp) return 'N/A';
    
    const date = new Date(timestamp * 1000); // Convert from Unix timestamp
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  if (loading) {
    return <div className="subscription-status loading">Loading subscription information...</div>;
  }

  // If the user is on the premium plan but we don't have subscription details
  if (user && user.plan === 'premium' && (!subscription || !subscription.has_active_subscription)) {
    return (
      <div className="subscription-status">
        <h3>Premium Plan</h3>
        <p>You currently have unlimited access.</p>
        {error && <div className="error">{error}</div>}
      </div>
    );
  }

  // If the user has an active subscription
  if (subscription && subscription.has_active_subscription) {
    return (
      <div className="subscription-status premium">
        <h3>Premium Plan</h3>
        <p>You have an active subscription with unlimited access.</p>
        
        <div className="subscription-details">
          <p><strong>Renewal Date:</strong> {formatDate(subscription.current_period_end)}</p>
          
          {subscription.cancel_at_period_end ? (
            <p className="subscription-cancelling">
              Your subscription will end on the renewal date.
            </p>
          ) : (
            <button 
              className="secondary-button cancel-button"
              onClick={async () => {
                if (window.confirm('Are you sure you want to cancel your subscription? You will still have access until the end of your billing period.')) {
                  try {
                    await userService.cancelSubscription();
                    // Refresh subscription status
                    const status = await userService.getSubscriptionStatus();
                    setSubscription(status);
                  } catch (err) {
                    setError('Error cancelling subscription');
                  }
                }
              }}
            >
              Cancel Subscription
            </button>
          )}
        </div>
      </div>
    );
  }

  // Default: User doesn't have premium
  return (
    <div className="subscription-status free">
      <h3>Free Plan</h3>
      <p>You are currently on the free plan with limited usage.</p>
      <button className="primary-button" onClick={onUpgrade}>
        Upgrade to Premium
      </button>
    </div>
  );
};

export default SubscriptionStatus;