import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
  isLoading?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ 
  role, 
  content, 
  timestamp,
  isLoading = false 
}) => {
  const isUser = role === 'user';
  
  // Define custom markdown components
  const components: Components = {
    code({ className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      return (
        <div className="code-block">
          <code className={match ? `language-${match[1]}` : ''} {...props}>
            {children}
          </code>
        </div>
      );
    },
  };
  
  return (
    <div className={`flex w-full my-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`
        flex flex-col max-w-3xl p-4 rounded-lg
        ${isUser 
          ? 'bg-primary-600 text-white rounded-br-none' 
          : 'bg-gray-100 dark:bg-gray-800 rounded-bl-none'}
      `}>
        <div className="flex items-center mb-2">
          <div className={`
            flex items-center justify-center w-8 h-8 rounded-full mr-2
            ${isUser 
              ? 'bg-primary-700' 
              : 'bg-secondary-500'}
          `}>
            {isUser ? '👤' : '🤖'}
          </div>
          <div className="font-medium">
            {isUser ? 'You' : 'Assistant'}
          </div>
          {timestamp && (
            <div className="ml-2 text-xs opacity-70">
              {timestamp.toLocaleTimeString()}
            </div>
          )}
        </div>
        
        <div className="prose dark:prose-invert max-w-none">
          {isLoading ? (
            <div className="thinking-animation">
              <span></span>
              <span></span>
              <span></span>
            </div>
          ) : (
            <ReactMarkdown components={components}>
              {content}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage; 