// components/LoginModal.js
import React, { useState } from 'react';
import { authService } from '../services/api';

const LoginModal = ({ onClose, onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('free');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
  
    try {
      if (isSignUp) {
        // Register new user
        const data = await authService.register(email, password, selectedPlan);
        // Save token and user data
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        // Call the onLogin function with user data
        onLogin(data.user);
      } else {
        // Login existing user
        const data = await authService.login(email, password);
        // Save token and user data
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        // Call the onLogin function with user data
        onLogin(data.user);
      }
    } catch (error) {
      if (error.response && error.response.data) {
        setError(error.response.data.error || 'Authentication failed');
      } else {
        setError('Unable to connect to the server. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Toggle between login and signup
  const toggleAuthMode = () => {
    setIsSignUp(!isSignUp);
    setError('');
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>{isSignUp ? 'Create an Account' : 'Sign In'}</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        {error && <div className="error-message">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          
          {isSignUp && (
            <div className="subscription-options">
              <h3>Choose a Plan</h3>
              
              <div 
                className={`subscription-option ${selectedPlan === 'free' ? 'selected' : ''}`}
                onClick={() => setSelectedPlan('free')}
              >
                <div className="subscription-option-header">
                  <h4>Free Plan</h4>
                  <span className="subscription-option-price">$0/month</span>
                </div>
                <div className="subscription-option-features">
                  <p>• 5 queries per day</p>
                  <p>• Basic access to Executive Orders data</p>
                </div>
              </div>
              
              <div 
                className={`subscription-option ${selectedPlan === 'premium' ? 'selected' : ''}`}
                onClick={() => setSelectedPlan('premium')}
              >
                <div className="subscription-option-header">
                  <h4>Premium Plan</h4>
                  <span className="subscription-option-price">$∞.99/month</span>
                </div>
                <div className="subscription-option-features">
                  <p>• 500 queries  a day</p>
                </div>
              </div>
            </div>
          )}
          
          <div className="form-actions">
            <button
              type="submit"
              className="primary-button"
              disabled={loading}
            >
              {loading ? 'Processing...' : isSignUp ? 'Create Account' : 'Sign In'}
            </button>
          </div>
        </form>
        
        <div className="option-divider">or</div>
        
        <button 
          className="secondary-button"
          onClick={toggleAuthMode}
          style={{ width: '100%' }}
        >
          {isSignUp ? 'Already have an account? Sign in' : 'Need an account? Sign up'}
        </button>
      </div>
    </div>
  );
};

export default LoginModal;