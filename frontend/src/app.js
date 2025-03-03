// App.js - Main application component
import React, { useState, useEffect, useRef } from 'react';
import './app.css';
import ChatMessage from './components/ChatMessage';
import LoginModal from './components/LoginModal';
import UserMenu from './components/UserMenu';
import { chatService } from './services/api';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const messagesEndRef = useRef(null);

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
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
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
          <a href="/history" onClick={(e) => {
            e.preventDefault();
            // Handle history view logic
          }}>Chat History</a>
        </nav>
      </footer>

      {showLoginModal && (
        <LoginModal 
          onClose={() => setShowLoginModal(false)} 
          onLogin={handleLogin}
        />
      )}
    </div>
  );
}

export default App;