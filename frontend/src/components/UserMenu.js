// components/UserMenu.js
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const UserMenu = ({ user, onLogout }) => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef(null);
  const navigate = useNavigate(); // Add this hook for navigation

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
            {user.plan === 'free' && (
              <li onClick={() => handleNavigation('/account')}>Upgrade to Premium</li>
            )}
            <li onClick={onLogout}>Sign Out</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default UserMenu;