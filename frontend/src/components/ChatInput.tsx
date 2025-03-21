import React, { useState, KeyboardEvent, useRef, useEffect } from 'react';

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
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [isComposing, setIsComposing] = useState(false);

  const handleSendMessage = () => {
    if (message.trim() && !isDisabled) {
      onSendMessage(message);
      setMessage('');
      
      // Reset textarea height after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  // Auto-resize textarea as user types
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const textarea = e.target;
    setMessage(textarea.value);
    
    // Reset height to auto to correctly calculate the new height
    textarea.style.height = 'auto';
    
    // Set new height based on content (with max height limit)
    const newHeight = Math.min(textarea.scrollHeight, 150);
    textarea.style.height = `${newHeight}px`;
  };

  return (
    <div className="p-4 px-10">
      <div className="flex items-center">
        <div className="flex w-full items-center pb-4 md:pb-1">
          <div className="flex w-full flex-col gap-1.5 rounded-[20px] p-2.5 pl-1.5 transition-colors bg-white border border-stone-200 shadow-sm">
            <div className="flex items-end gap-1.5 md:gap-2 pl-4">
              <div className="flex min-w-0 flex-1 flex-col">
                <textarea
                  ref={textareaRef}
                  id="prompt-textarea"
                  tabIndex={0}
                  dir="auto"
                  rows={2}
                  placeholder={placeholder}
                  className="mb-2 resize-none border-0 focus:outline-none text-sm bg-transparent px-0 pb-6 pt-2"
                  value={message}
                  onChange={handleTextareaChange}
                  onKeyDown={handleKeyDown}
                  onCompositionStart={() => setIsComposing(true)}
                  onCompositionEnd={() => setIsComposing(false)}
                  disabled={isDisabled}
                />
              </div>
              <button
                disabled={!message.trim() || isDisabled}
                data-testid="send-button"
                className="flex size-8 items-end justify-center rounded-full bg-black text-white transition-colors hover:opacity-70 focus-visible:outline-none focus-visible:outline-black disabled:bg-[#D7D7D7] disabled:text-[#f4f4f4] disabled:hover:opacity-100"
                onClick={handleSendMessage}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="32"
                  height="32"
                  fill="none"
                  viewBox="0 0 32 32"
                  className="icon-2xl"
                >
                  <path
                    fill="currentColor"
                    fillRule="evenodd"
                    d="M15.192 8.906a1.143 1.143 0 0 1 1.616 0l5.143 5.143a1.143 1.143 0 0 1-1.616 1.616l-3.192-3.192v9.813a1.143 1.143 0 0 1-2.286 0v-9.813l-3.192 3.192a1.143 1.143 0 1 1-1.616-1.616z"
                    clipRule="evenodd"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInput; 