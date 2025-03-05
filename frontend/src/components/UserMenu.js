// components/UserMenu.js
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const UserMenu = ({ user, onLogout }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showComingSoon, setShowComingSoon] = useState(false);
  const menuRef = useRef(null);
  const navigate = useNavigate(); // Add this hook for navigation

  const handleUpgradeClick = (e) => {
    e.preventDefault();
    setShowComingSoon(true);
    setIsOpen(false); // Close the dropdown menu
  }
  
  // Add this function to close the modal
  const handleCloseModal = () => {
    setShowComingSoon(false);
  };

  // Get initials from email for avatar
  const getInitials = (email) => {
    if (!email) return 'U';
    return email.charAt(0).toUpperCase();
  };

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Handle navigation clicks
  const handleNavigation = (path) => {
    setIsOpen(false);
    navigate(path);
  };

  return (
    <div className="user-menu" ref={menuRef}>
      <div className="user-profile" onClick={() => setIsOpen(!isOpen)}>
        <div className="user-avatar">
          {getInitials(user.email)}
        </div>
        <span>{user.email}</span>
      </div>
  
      {isOpen && (
        <div className="user-dropdown">
          <ul>
            <li className="username">{user.email}</li>
            <li className="subscription">
              {user.plan === 'premium' ? 'Premium Plan' : 'Free Plan'}
            </li>
            <li onClick={() => handleNavigation('/history')}>View History</li>
            <li onClick={() => handleNavigation('/account')}>Account Settings</li>
            {user && user.plan === 'free' && (
              <li>
                <a href="#upgrade" onClick={handleUpgradeClick}>
                  Upgrade to Premium
                </a>
              </li>
            )}
            <li onClick={onLogout}>Sign Out</li>
          </ul>
        </div>
      )}
      
      {/* Coming Soon Modal */}
      {showComingSoon && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Coming Soon!</h3>
            <p>Our payment system is currently under development. This feature will be available soon!</p>
            <p>Thank you for your interest in our premium plan.</p>
            <button onClick={handleCloseModal} className="close-button">Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserMenu;