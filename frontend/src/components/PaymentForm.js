import React, { useState } from 'react';
import { userService } from '../services/api';

const PaymentForm = ({ onSuccess, onCancel }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleUpgrade = async () => {
    setLoading(true);
    setError('');

    try {
      // Get the current URL base for success/cancel redirects
      const baseUrl = window.location.origin;
      
      // Call the API to create a checkout session
      const response = await userService.upgradeAccount({
        success_url: `${baseUrl}/subscription/success`,
        cancel_url: `${baseUrl}/subscription/cancel`
      });

      // Redirect to the Stripe checkout page
      if (response && response.checkout_url) {
        window.location.href = response.checkout_url;
      } else {
        // For demo or if Stripe is not configured, handle success directly
        if (response && response.message === 'Plan upgraded successfully') {
          onSuccess();
        } else {
          setError('Invalid response from server');
        }
      }
    } catch (error) {
      console.error('Payment error:', error);
      setError(error.response?.data?.error || 'Error processing payment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="payment-form">
      <h2>Upgrade to Premium</h2>
      
      <div className="subscription-options">
        <div className="subscription-option selected">
          <div className="subscription-option-header">
            <h4>Premium Plan</h4>
            <span className="subscription-option-price">$9.99/month</span>
          </div>
          <div className="subscription-option-features">
            <p>• Unlimited queries</p>
            <p>• Enhanced data access</p>
            <p>• Priority support</p>
          </div>
        </div>
      </div>
      
      {error && <div className="error-message">{error}</div>}
      
      <div className="form-actions">
        <button 
          onClick={handleUpgrade} 
          className="primary-button"
          disabled={loading}
        >
          {loading ? 'Processing...' : 'Upgrade Now'}
        </button>
        
        <button 
          onClick={onCancel} 
          className="secondary-button"
          disabled={loading}
        >
          Cancel
        </button>
      </div>
    </div>
  );
};

export default PaymentForm;