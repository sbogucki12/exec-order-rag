// App.js - Main application component
import React, { useState, useEffect, useRef } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, Link } from 'react-router-dom';
import './app.css';
import ChatMessage from './components/ChatMessage';
import LoginModal from './components/LoginModal';
import UserMenu from './components/UserMenu';
import PaymentForm from './components/PaymentForm';
import SubscriptionStatus from './components/SubscriptionStatus';
import SubscriptionSuccess from './components/SubscriptionSuccess';
import SubscriptionCancel from './components/SubscriptionCancel';
import { chatService, authService } from './services/api';
import ChatHistory from './components/ChatHistory';


const AccountPage = ({ user, isAuthenticated, handleLogout }) => {
  const [showPaymentForm, setShowPaymentForm] = useState(false);

  if (!isAuthenticated) {
    return <Navigate to="/" />;
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>My Account</h1>
        <div className="header-right">
          <UserMenu user={user} onLogout={handleLogout} />
        </div>
      </header>

      <main className="account-container">
        <div className="account-section">
          <h2>Account Details</h2>
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Plan:</strong> {user.plan === 'premium' ? 'Premium' : 'Free'}</p>
        </div>

        <div className="account-section">
          <h2>Subscription</h2>
          {showPaymentForm ? (
            <PaymentForm 
              onSuccess={(updatedUser) => {
                // You'll need to have a way to update the user object here
                setShowPaymentForm(false);
              }}
              onCancel={() => setShowPaymentForm(false)}
            />
          ) : (
            <SubscriptionStatus 
              user={user} 
              onUpgrade={() => setShowPaymentForm(true)} 
            />
          )}
        </div>
      </main>

      <footer className="app-footer">
        <nav>
          <a href="/" onClick={(e) => {
            e.preventDefault();
            window.location.href = '/';
          }}>Back to Chat</a>
        </nav>
      </footer>
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const messagesEndRef = useRef(null);

// Load user from localStorage on initial render
useEffect(() => {
  const token = localStorage.getItem('token');
  const userData = localStorage.getItem('user');
  
  if (token && userData) {
    setUser(JSON.parse(userData));
    setIsAuthenticated(true);
  }
  
  // Load saved messages
  const savedMessages = localStorage.getItem('chatHistory');
  if (savedMessages) {
    setMessages(JSON.parse(savedMessages));
  }
}, []);

// Save messages to localStorage when they change
useEffect(() => {
  if (messages.length > 0) {
    localStorage.setItem('chatHistory', JSON.stringify(messages));
  }
}, [messages]);

  // Handle API calls to your backend
  // In App.js, update the sendMessage function
  const sendMessage = async (e) => {
  e.preventDefault();
  if (!inputValue.trim()) return;
  
  // Add user message to chat
  const userMessage = { sender: 'user', text: inputValue };
  setMessages([...messages, userMessage]);
  setInputValue('');
  setLoading(true);
  
  try {
    // Call the API
    const response = await chatService.sendMessage(inputValue, messages);
    
    // Add bot response to chat
    setMessages([...messages, userMessage, {
      sender: 'bot',
      text: response.response
    }]);
  } catch (error) {
    if (error.response && error.response.status === 429) {
      // Usage limit exceeded
      setMessages([...messages, userMessage, {
        sender: 'bot',
        text: 'You have reached your usage limit for today. Please sign in or upgrade your plan to continue.'
      }]);
      setShowLoginModal(true);
    } else {
      console.error('Error:', error);
      setMessages([...messages, userMessage, {
        sender: 'bot',
        text: 'Sorry, I encountered an error. Please try again later.'
      }]);
    }
  } finally {
    setLoading(false);
  }
};

  // Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle login
  const handleLogin = (userData) => {
    setUser(userData);
    setIsAuthenticated(true);
    setShowLoginModal(false);
  };

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setIsAuthenticated(false);
  };

    // Add clear chat function here
    const clearChat = () => {
      setMessages([]);
      localStorage.removeItem('chatHistory');
    };

    return (
      <Router>
        <Routes>
          <Route path="/" element={
            <div className="app-container">
              <header className="app-header">
                <h1>Executive Orders RAG Chatbot</h1>
                <div className="header-right">
                  {isAuthenticated ? (
                    <UserMenu user={user} onLogout={handleLogout} />
                  ) : (
                    <button className="login-button" onClick={() => setShowLoginModal(true)}>
                      Sign In
                    </button>
                  )}
                </div>
              </header>
    
              <main className="chat-container">
                <div className="messages-container">
                  {messages.length === 0 ? (
                    <div className="welcome-message">
                      <h2>Welcome to the Executive Orders RAG Chatbot</h2>
                      <p>Ask me anything about U.S. Executive Orders.</p>
                    </div>
                  ) : (
                    messages.map((message, index) => (
                      <ChatMessage key={index} message={message} />
                    ))
                  )}
                  {loading && (
                    <div className="message bot-message">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
    
                <form className="input-form" onSubmit={sendMessage}>
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Ask about Executive Orders..."
                    disabled={loading}
                  />
                  <button type="submit" disabled={loading || !inputValue.trim()}>
                    Send
                  </button>
                </form>
              </main>
    
              <footer className="app-footer">
                <nav>
                  <a href="/docs" target="_blank" rel="noopener noreferrer">Documentation</a>
                  <button className="clear-button" onClick={clearChat}>Clear Chat</button>
                  {isAuthenticated && (
                    <Link to="/account">My Account</Link>
                  )}
                </nav>
              </footer>
    
              {showLoginModal && (
                <LoginModal 
                  onClose={() => setShowLoginModal(false)} 
                  onLogin={handleLogin}
                />
              )}
            </div>
          } />
          
          {/* Other routes */}
          <Route path="/account" element={
            <AccountPage 
              user={user} 
              isAuthenticated={isAuthenticated} 
              handleLogout={handleLogout} 
            />
          } />
            <Route path="/history" element={
            <ChatHistory 
              messages={messages}
              user={user}
              isAuthenticated={isAuthenticated}
              handleLogout={handleLogout}
            />
          } />
          <Route path="/subscription/success" element={<SubscriptionSuccess />} />
          <Route path="/subscription/cancel" element={<SubscriptionCancel />} />
        </Routes>
      </Router>
    );
}

export default App;