import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const SubscriptionCancel = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Automatically redirect after 5 seconds
    const timer = setTimeout(() => {
      navigate('/');
    }, 5000);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="subscription-cancel-page">
      <div className="subscription-cancel-content">
        <h1>Subscription Cancelled</h1>
        <p>Your subscription process was cancelled.</p>
        <p>You can still use the free tier of our service with limited access.</p>
        <p>You will be redirected to the main page in a few seconds...</p>
        
        <div className="button-group">
          <button 
            className="primary-button"
            onClick={() => navigate('/')}
          >
            Return to Chat
          </button>
          
          <button 
            className="secondary-button"
            onClick={() => navigate('/account')}
          >
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubscriptionCancel;