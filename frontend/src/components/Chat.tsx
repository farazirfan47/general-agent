import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import StatusIndicator from './StatusIndicator';
import { wsManager, WebSocketEventType } from '@/lib/websocket';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

interface StatusUpdate {
  id: string;
  type: 'thinking' | 'web_search' | 'computer_use' | 'cua_event' | 'step' | 'plan';
  message: string;
  details?: any;
  timestamp: Date;
}

const Chat: React.FC = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [statusUpdates, setStatusUpdates] = useState<StatusUpdate[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Connect to WebSocket when component mounts
  useEffect(() => {
    // Only run on client-side
    if (typeof window === 'undefined') return;
    
    const connectToWebSocket = async () => {
      try {
        // Get session ID from URL if provided
        const session = searchParams.get('session');
        const sessionIdParam = session || 'new';
        
        // Connect to WebSocket
        const newSessionId = await wsManager.connect(sessionIdParam);
        setSessionId(newSessionId);
        setIsConnected(true);
        
        // Update URL with session ID if not already there
        if (!session && newSessionId) {
          // Use window.history for client-side URL updates
          const url = new URL(window.location.href);
          url.searchParams.set('session', newSessionId);
          window.history.pushState({}, '', url.toString());
        }
        
        // If session ID was provided, fetch conversation history
        if (sessionIdParam !== 'new') {
          fetchConversationHistory(sessionIdParam);
        }
      } catch (error) {
        console.error('Failed to connect to WebSocket:', error);
      }
    };
    
    connectToWebSocket();
    
    // Setup event listeners
    setupEventListeners();
    
    // Cleanup on unmount
    return () => {
      wsManager.disconnect();
      cleanupEventListeners();
    };
  }, [searchParams]); // Only run when search params change
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, statusUpdates]);
  
  // Setup WebSocket event listeners
  const setupEventListeners = () => {
    // Status update events
    wsManager.addEventListener(WebSocketEventType.Thinking, handleThinkingEvent);
    wsManager.addEventListener(WebSocketEventType.Plan, handlePlanEvent);
    wsManager.addEventListener(WebSocketEventType.Step, handleStepEvent);
    wsManager.addEventListener(WebSocketEventType.ToolUsage, handleToolUsageEvent);
    wsManager.addEventListener(WebSocketEventType.CuaEvent, handleCuaEvent);
    wsManager.addEventListener(WebSocketEventType.Complete, handleCompleteEvent);
    wsManager.addEventListener(WebSocketEventType.Error, handleErrorEvent);
  };
  
  // Clean up event listeners
  const cleanupEventListeners = () => {
    wsManager.removeEventListener(WebSocketEventType.Thinking, handleThinkingEvent);
    wsManager.removeEventListener(WebSocketEventType.Plan, handlePlanEvent);
    wsManager.removeEventListener(WebSocketEventType.Step, handleStepEvent);
    wsManager.removeEventListener(WebSocketEventType.ToolUsage, handleToolUsageEvent);
    wsManager.removeEventListener(WebSocketEventType.CuaEvent, handleCuaEvent);
    wsManager.removeEventListener(WebSocketEventType.Complete, handleCompleteEvent);
    wsManager.removeEventListener(WebSocketEventType.Error, handleErrorEvent);
  };
  
  // Fetch conversation history for an existing session
  const fetchConversationHistory = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/conversation/${sessionId}`);
      if (!response.ok) throw new Error('Failed to fetch conversation history');
      
      const data = await response.json();
      
      // Convert conversation to messages format
      const historyMessages = data.conversation
        .filter((msg: any) => msg.role === 'user' || msg.role === 'assistant')
        .map((msg: any) => ({
          role: msg.role,
          content: msg.content,
          timestamp: new Date()
        }));
      
      setMessages(historyMessages);
    } catch (error) {
      console.error('Error fetching conversation history:', error);
    }
  };
  
  // Handle sending a new message
  const handleSendMessage = (message: string) => {
    // Add user message to the list
    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsProcessing(true);
    
    // Clear status updates for new request
    setStatusUpdates([]);
    
    // Send to WebSocket
    wsManager.sendMessage(message);
    
    // Add initial thinking status
    addStatusUpdate({
      type: 'thinking',
      message: 'Processing your request...',
      details: null
    });
  };
  
  // Add a new status update
  const addStatusUpdate = ({ type, message, details }: { type: StatusUpdate['type'], message: string, details: any }) => {
    const update: StatusUpdate = {
      id: Math.random().toString(36).substring(2, 9),
      type,
      message,
      details,
      timestamp: new Date()
    };
    
    setStatusUpdates(prev => [...prev, update]);
  };
  
  // Event handlers
  const handleThinkingEvent = (data: any) => {
    addStatusUpdate({
      type: 'thinking',
      message: data.message || 'Thinking...',
      details: null
    });
  };
  
  const handlePlanEvent = (data: any) => {
    addStatusUpdate({
      type: 'plan',
      message: 'Created a plan',
      details: data
    });
  };
  
  const handleStepEvent = (data: any) => {
    addStatusUpdate({
      type: 'step',
      message: `Step ${data.current}/${data.total}`,
      details: data
    });
  };
  
  const handleToolUsageEvent = (data: any) => {
    const tool = data.tool;
    let message = 'Using a tool';
    
    if (tool === 'web_search') {
      message = 'Searching the web';
      addStatusUpdate({
        type: 'web_search',
        message,
        details: data
      });
    } else if (tool === 'computer_use') {
      message = 'Using computer browser';
      addStatusUpdate({
        type: 'computer_use',
        message,
        details: data
      });
    }
  };
  
  const handleCuaEvent = (data: any) => {
    addStatusUpdate({
      type: 'cua_event',
      message: 'Browser action',
      details: data
    });
  };
  
  const handleCompleteEvent = (data: any) => {
    // Add assistant message with the final response
    const assistantMessage: Message = {
      role: 'assistant',
      content: data.message,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    setIsProcessing(false);
  };
  
  const handleErrorEvent = (data: any) => {
    // Add error message
    addStatusUpdate({
      type: 'thinking',
      message: `Error: ${data.message}`,
      details: null
    });
    
    setIsProcessing(false);
  };
  
  // Generate shareable link
  const getShareableLink = () => {
    if (!sessionId) return '';
    const baseUrl = window.location.origin;
    return `${baseUrl}/?session=${sessionId}`;
  };
  
  // Copy shareable link to clipboard
  const copyShareableLink = () => {
    const link = getShareableLink();
    navigator.clipboard.writeText(link);
    alert('Link copied to clipboard!');
  };
  
  // Handle creating a new chat
  const handleNewChat = () => {
    if (typeof window !== 'undefined') {
      window.location.href = '/?session=new';
    }
  };
  
  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header */}
      <header className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
        <h1 className="text-xl font-bold">AI Assistant</h1>
        
        <div className="flex items-center space-x-4">
          {sessionId && (
            <div className="flex items-center text-sm">
              <span className="mr-2">Session ID: {sessionId}</span>
              <button 
                className="text-primary-600 hover:text-primary-700"
                onClick={copyShareableLink}
              >
                📋 Copy Link
              </button>
            </div>
          )}
          
          <button 
            className="px-3 py-1 text-sm bg-primary-600 hover:bg-primary-700 text-white rounded-md"
            onClick={handleNewChat}
          >
            New Chat
          </button>
        </div>
      </header>
      
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center p-6 max-w-md">
              <h2 className="text-2xl font-bold mb-2">Welcome to AI Assistant</h2>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Start a conversation with the AI assistant to get help with various tasks.
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Render chat messages */}
            {messages.map((message, index) => (
              <ChatMessage 
                key={`msg-${index}`}
                role={message.role}
                content={message.content}
                timestamp={message.timestamp}
              />
            ))}
            
            {/* Status updates */}
            {isProcessing && (
              <div className="my-4 border border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                <h3 className="font-medium mb-2">Status Updates</h3>
                <div className="space-y-1 max-h-48 overflow-y-auto">
                  {statusUpdates.map((update) => (
                    <StatusIndicator
                      key={update.id}
                      type={update.type}
                      message={update.message}
                      details={update.details}
                    />
                  ))}
                </div>
              </div>
            )}
            
            {/* Thinking indicator if processing */}
            {isProcessing && (
              <ChatMessage 
                role="assistant"
                content=""
                isLoading={true}
              />
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Area */}
      <ChatInput 
        onSendMessage={handleSendMessage}
        isDisabled={!isConnected || isProcessing}
        placeholder={isConnected ? "Type your message..." : "Connecting..."}
      />
    </div>
  );
};

export default Chat; 