// components/ChatHistory.js
import React from 'react';
import { useNavigate } from 'react-router-dom';
import ChatMessage from './ChatMessage';

const ChatHistory = ({ messages, user, isAuthenticated, handleLogout }) => {
  const navigate = useNavigate();

  if (!isAuthenticated) {
    return navigate('/');
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Chat History</h1>
        <div className="header-right">
          <button className="secondary-button" onClick={() => navigate('/')}>
            Back to Chat
          </button>
        </div>
      </header>

      <main className="chat-container">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <p>You have no chat history yet.</p>
            </div>
          ) : (
            <>
              <h2>Your Recent Conversations</h2>
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}
            </>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <nav>
          <button className="secondary-button" onClick={() => navigate('/')}>
            Return to Chat
          </button>
        </nav>
      </footer>
    </div>
  );
};

export default ChatHistory;