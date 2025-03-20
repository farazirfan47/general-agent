import React, { useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isDisabled?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isDisabled = false,
  placeholder = 'Type your message...'
}) => {
  const [message, setMessage] = useState('');

  const handleSendMessage = () => {
    if (message.trim() && !isDisabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex items-end w-full bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 p-4">
      <div className="relative flex-1 mr-2">
        <textarea
          className="w-full px-4 py-3 rounded-lg resize-none border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
          rows={2}
          placeholder={placeholder}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
        />
      </div>
      <button
        className="px-4 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        onClick={handleSendMessage}
        disabled={isDisabled || !message.trim()}
      >
        <span>Send</span>
      </button>
    </div>
  );
};

export default ChatInput; 