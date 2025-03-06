import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext'; // Adjust path as needed

const DeleteAccount = () => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleInitialClick = () => {
    setShowConfirmation(true);
  };

  const handleDeleteAccount = async () => {
    // Check if confirmation text matches expected value
    if (confirmation.toLowerCase() !== 'delete my account') {
      setError('Please type "delete my account" to confirm.');
      return;
    }

    setIsDeleting(true);
    setError('');

    try {
      const token = localStorage.getItem('token');
      
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch('/api/user/delete-account', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to delete account');
      }

      // Account deleted successfully
      logout();
      navigate('/deleted', { replace: true });
    } catch (err) {
      setError(err.message);
      setIsDeleting(false);
    }
  };

  return (
    <div className="delete-account-container">
      <h2>Delete Account</h2>
      
      {!showConfirmation ? (
        <div>
          <p>
            Deleting your account will permanently remove all your data, including:
          </p>
          <ul>
            <li>Your user profile</li>
            <li>All chat history</li>
            <li>Usage statistics</li>
            {/* Add other data that will be deleted */}
          </ul>
          <p>This action cannot be undone.</p>
          
          <button 
            className="danger-button"
            onClick={handleInitialClick}
          >
            I Want to Delete My Account
          </button>
        </div>
      ) : (
        <div className="confirmation-section">
          <p className="warning">
            <strong>Final Warning:</strong> This will permanently delete your account and all associated data.
            This action cannot be reversed.
          </p>
          
          <div className="confirmation-input">
            <label>Type "delete my account" to confirm:</label>
            <input
              type="text"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
              placeholder="delete my account"
            />
          </div>
          
          {error && <p className="error-message">{error}</p>}
          
          <div className="button-group">
            <button
              className="cancel-button"
              onClick={() => setShowConfirmation(false)}
              disabled={isDeleting}
            >
              Cancel
            </button>
            
            <button
              className="delete-button"
              onClick={handleDeleteAccount}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Permanently Delete Account'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DeleteAccount;