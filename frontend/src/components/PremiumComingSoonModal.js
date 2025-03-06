// components/PremiumComingSoonModal.js
import React from 'react';
import './PremiumComingSoonModal.css';

const PremiumComingSoonModal = ({ onClose }) => {
  return (
    <div className="modal-overlay">
      <div className="premium-modal-content">
        <div className="modal-header">
          <h2>Premium Features Coming Soon!</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="premium-content">
          <div className="premium-icon">🚀</div>
          
          <p className="premium-message">
            We're excited to announce that premium features for our Executive Orders Chatbot 
            are currently in development and will be launching soon!
          </p>
          
          <div className="premium-features">
            <h3>Premium will include:</h3>
            <ul>
              <li>Unlimited queries</li>
              <li>Priority support</li>
              <li>Enhanced search capabilities</li>
              <li>Downloadable search results</li>
              <li>Advanced analytics</li>
            </ul>
          </div>
          
          <div className="premium-notification">
            <p>Want to be notified when premium features launch?</p>
            <button className="notify-button" onClick={() => {
              alert('Your email has been added to our notification list!');
            }}>
              Keep Me Updated
            </button>
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="continue-button" onClick={onClose}>
            Continue with Free Plan
          </button>
        </div>
      </div>
    </div>
  );
};

export default PremiumComingSoonModal;