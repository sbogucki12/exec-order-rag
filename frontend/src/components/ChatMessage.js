// components/ChatMessage.js
import React from 'react';

const ChatMessage = ({ message }) => {
  const { sender, text } = message;
  
  return (
    <div className={`message ${sender === 'user' ? 'user-message' : 'bot-message'}`}>
      {text}
    </div>
  );
};

export default ChatMessage;