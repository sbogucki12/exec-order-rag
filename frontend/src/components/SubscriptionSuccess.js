import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { userService } from '../services/api';

const SubscriptionSuccess = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // Verify the subscription status upon successful payment
    const verifySubscription = async () => {
      try {
        // Check the subscription status
        const status = await userService.getSubscriptionStatus();
        
        if (status && status.has_active_subscription) {
          setLoading(false);
          // Automatically redirect after 5 seconds
          setTimeout(() => {
            navigate('/');
          }, 5000);
        } else {
          setError('Subscription verification failed. Please contact support.');
          setLoading(false);
        }
      } catch (err) {
        console.error('Error verifying subscription:', err);
        setError('Error verifying subscription. Please contact support.');
        setLoading(false);
      }
    };

    verifySubscription();
  }, [navigate]);

  return (
    <div className="subscription-success-page">
      <div className="subscription-success-content">
        <h1>🎉 Subscription Successful!</h1>
        
        {loading ? (
          <p>Verifying your subscription...</p>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : (
          <>
            <p>Thank you for subscribing to the Premium plan! Your account has been upgraded.</p>
            <p>You now have unlimited access to the Executive Orders RAG Chatbot.</p>
            <p>You will be redirected to the main page in a few seconds...</p>
            
            <button 
              className="primary-button"
              onClick={() => navigate('/')}
            >
              Return to Chat
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default SubscriptionSuccess;