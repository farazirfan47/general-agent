import React from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
  isLoading?: boolean;
  requiresResponse?: boolean;
  isClarification?: boolean;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ 
  role, 
  content, 
  timestamp,
  isLoading = false,
  requiresResponse,
  isClarification
}) => {
  const isUser = role === 'user';
  
  // Define custom markdown components
  const components: Components = {
    code({ className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '');
      return (
        <div className="code-block relative my-2 rounded-md overflow-hidden">
          {match && (
            <div className="bg-gray-800 px-4 py-1 text-xs text-gray-300 font-mono">
              {match[1]}
            </div>
          )}
          <pre className="overflow-x-auto p-4 bg-gray-900 text-gray-100">
            <code className={match ? `language-${match[1]}` : ''} {...props}>
              {children}
            </code>
          </pre>
        </div>
      );
    },
    p({ children }) {
      return <p className="mb-2">{children}</p>;
    },
    ul({ children }) {
      return <ul className="list-disc pl-5 mb-2">{children}</ul>;
    },
    ol({ children }) {
      return <ol className="list-decimal pl-5 mb-2">{children}</ol>;
    },
    li({ children }) {
      return <li className="mb-1">{children}</li>;
    },
    a({ href, children }) {
      return (
        <a 
          href={href} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-blue-600 dark:text-blue-400 hover:underline"
        >
          {children}
        </a>
      );
    }
  };
  
  return (
    <div className={`flex ${role === 'assistant' ? 'justify-start' : 'justify-end'}`}>
      <div className={`max-w-[80%] ${isUser ? 'bg-white' : 'bg-[#ededed]'} rounded-md p-4`}>
        {/* Add a visual indicator for messages requiring response */}
        {requiresResponse && (
          <div className="mb-2 text-amber-500 text-sm font-medium flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            Please respond to this question
          </div>
        )}
        
        {/* For clarification responses, add a subtle indicator */}
        {isClarification && (
          <div className="mb-1 text-blue-400 text-xs">
            Clarification response
          </div>
        )}
        
        {isUser ? (
          <div className="flex justify-end">
            <div>
              <div className="ml-4 rounded-[16px] px-4 py-2 md:ml-24 bg-[#ededed] text-stone-900 font-light">
                <div>
                  <div>
                    <ReactMarkdown components={components}>
                      {content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col">
            <div className="flex">
              <div className="mr-4 rounded-[16px] px-4 py-2 md:mr-24 text-black bg-white font-light">
                <div>
                  {isLoading ? (
                    <div className="flex space-x-1.5 items-center p-2">
                      <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600"></div>
                      <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600"></div>
                      <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600"></div>
                    </div>
                  ) : (
                    <ReactMarkdown components={components}>
                      {content}
                    </ReactMarkdown>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatMessage; 