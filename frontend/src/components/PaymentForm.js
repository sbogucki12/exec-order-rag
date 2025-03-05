// components/PaymentForm.js
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const PaymentForm = () => {
  const [showComingSoon, setShowComingSoon] = useState(false);
  const navigate = useNavigate();
  
  const handleUpgradeClick = (e) => {
    e.preventDefault();
    setShowComingSoon(true);
  };
  
  const handleClose = () => {
    setShowComingSoon(false);
  };
  
  return (
    <div className="payment-form-container">
      <h2>Upgrade to Premium</h2>
      <p>Upgrade to our premium plan to enjoy unlimited access to our Executive Orders chatbot.</p>
      
      <div className="pricing-container">
        <div className="pricing-card">
          <h3>Premium Plan</h3>
          <p className="price">$9.99/month</p>
          <ul>
            <li>Unlimited prompts</li>
            <li>Priority processing</li>
            <li>Advanced features</li>
            <li>Chat history storage</li>
          </ul>
          <button 
            className="upgrade-button"
            onClick={handleUpgradeClick}
          >
            Upgrade Now
          </button>
        </div>
      </div>
      
      {showComingSoon && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Coming Soon!</h3>
            <p>Our payment system is currently under development. This feature will be available soon!</p>
            <p>Thank you for your interest in our premium plan.</p>
            <button onClick={handleClose} className="close-button">Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaymentForm;