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
  type: 'thinking' | 'web_search' | 'computer_use' | 'cua_event' | 'cua_reasoning' | 'step' | 'plan';
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
  const [browserStreamUrl, setBrowserStreamUrl] = useState<string | null>(null);
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
    wsManager.addEventListener(WebSocketEventType.CuaReasoning, handleCuaReasoningEvent);
    wsManager.addEventListener(WebSocketEventType.Complete, handleCompleteEvent);
    wsManager.addEventListener(WebSocketEventType.Error, handleErrorEvent);
    wsManager.addEventListener(WebSocketEventType.Clarification, handleClarificationEvent);
  };
  
  // Clean up event listeners
  const cleanupEventListeners = () => {
    wsManager.removeEventListener(WebSocketEventType.Thinking, handleThinkingEvent);
    wsManager.removeEventListener(WebSocketEventType.Plan, handlePlanEvent);
    wsManager.removeEventListener(WebSocketEventType.Step, handleStepEvent);
    wsManager.removeEventListener(WebSocketEventType.ToolUsage, handleToolUsageEvent);
    wsManager.removeEventListener(WebSocketEventType.CuaEvent, handleCuaEvent);
    wsManager.removeEventListener(WebSocketEventType.CuaReasoning, handleCuaReasoningEvent);
    wsManager.removeEventListener(WebSocketEventType.Complete, handleCompleteEvent);
    wsManager.removeEventListener(WebSocketEventType.Error, handleErrorEvent);
    wsManager.removeEventListener(WebSocketEventType.Clarification, handleClarificationEvent);
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
    
    // Add initial thinking status
    addStatusUpdate({
      type: 'thinking',
      message: 'Processing your request...',
      details: null
    });
    
    // For search-like queries, add some initial steps that mimic the screenshot
    if (message.toLowerCase().includes('search') || 
        message.toLowerCase().includes('find') || 
        message.toLowerCase().includes('list') ||
        message.toLowerCase().includes('show')) {
      
      // Add a searching step
      addStatusUpdate({
        type: 'web_search',
        message: `Searching for ${message.length > 20 ? message.substring(0, 20) + '...' : message}`,
        details: { query: message }
      });
    }
    
    // Send to WebSocket
    wsManager.sendMessage(message);
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
    // We're not showing the plan anymore, but we'll keep track of it
    // in case we need it for reference
    console.log("Plan received but not displayed:", data);
    
    // Don't add any status update for plans
    // Instead, we could add a first step if there are no steps yet
    if (statusUpdates.filter(update => update.type === 'step').length === 0 && data.steps && data.steps.length > 0) {
      // Add the first step as "Planning"
      addStatusUpdate({
        type: 'step',
        message: 'Planning the approach',
        details: {
          current: 1,
          total: data.steps.length,
          completed: false
        }
      });
    }
  };
  
  const handleStepEvent = (data: any) => {
    // Check if this step already exists in our status updates
    const existingStepIndex = statusUpdates.findIndex(
      update => update.type === 'step' && update.details?.current === data.current
    );
    
    // If the step already exists, update it with new information
    if (existingStepIndex !== -1) {
      const updatedStatusUpdates = [...statusUpdates];
      updatedStatusUpdates[existingStepIndex] = {
        ...updatedStatusUpdates[existingStepIndex],
        message: data.description || `Step ${data.current}/${data.total}: ${data.content || ''}`,
        details: {
          ...data,
          completed: data.completed || false
        }
      };
      setStatusUpdates(updatedStatusUpdates);
    } else {
      // Add a new step
      addStatusUpdate({
        type: 'step',
        message: data.description || `Step ${data.current}/${data.total}: ${data.content || ''}`,
        details: {
          ...data,
          completed: data.completed || false
        }
      });
    }
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
      // Check if the browser stream URL is available in the data
      if (data.stream_url) {
        setBrowserStreamUrl(data.stream_url);
      }
      addStatusUpdate({
        type: 'computer_use',
        message,
        details: data
      });
    }
  };
  
  const handleCuaEvent = (data: any) => {
    // Check if there's a stream URL in the data (should be at the top level)
    if (data.stream_url && !browserStreamUrl) {
      console.log("Setting browser stream URL:", data.stream_url);
      setBrowserStreamUrl(data.stream_url);
    }
    
    // Handle browser_started events immediately to show the iframe
    if (data.action === "browser_started") {
      console.log("Browser started event received with stream URL:", data.stream_url);
      setBrowserStreamUrl(data.stream_url);
      // Add a status update for browser initialization
      addStatusUpdate({
        type: 'cua_event',
        message: "Browser session initialized",
        details: data
      });
      return;
    }
    
    // Format the message based on the action type
    let message = 'Browser action';
    let details = data;
    
    // Format the message based on the action type
    if (data.action) {
      switch (data.action.toLowerCase()) {
        case 'searching':
          message = `Searching for "${data.query || 'information'}"`;
          break;
        case 'selecting':
          message = `Selecting ${data.element || 'an item'}`;
          break;
        case 'scrolling':
          message = `Scrolling ${data.direction || 'page'}`;
          break;
        case 'capturing':
          message = `Capturing ${data.element || 'information'}`;
          break;
        case 'completed':
          message = `Completed list of ${data.task || 'items'}`;
          break;
        case 'clicking':
          message = `Clicking on ${data.element || 'element'}`;
          break;
        case 'typing':
          message = `Typing ${data.text ? '"' + data.text + '"' : 'text'}`;
          break;
        case 'navigating':
          message = `Navigating to ${data.url || 'page'}`;
          break;
        default:
          // Clean and capitalize the action for display
          const actionText = data.action.toLowerCase()
            .replace(/_/g, ' ')
            .replace(/\b\w/g, (c: string) => c.toUpperCase());
          
          message = actionText;
      }
    }
    
    // Add description if available
    if (data.description) {
      details = {
        ...data,
        description: data.description
      };
    }
    
    addStatusUpdate({
      type: 'cua_event',
      message,
      details
    });
  };
  
  const handleCuaReasoningEvent = (data: any) => {
    // Create a readable message based on reasoning text
    let message = 'Reasoning';
    
    if (data.text) {
      // Extract the first sentence or up to 60 chars for the main message
      const firstSentence = data.text.split('.')[0];
      message = firstSentence.length > 60 
        ? firstSentence.substring(0, 60) + '...' 
        : firstSentence;
    }
    
    // Add reasoning status update
    addStatusUpdate({
      type: 'cua_reasoning',
      message,
      details: data
    });
  };
  
  const handleCompleteEvent = (data: any) => {
    // Mark all steps as completed
    const updatedStatusUpdates = statusUpdates.map(update => {
      if (update.type === 'step') {
        return {
          ...update,
          details: {
            ...update.details,
            completed: true
          }
        };
      }
      return update;
    });
    
    setStatusUpdates(updatedStatusUpdates);
    
    // Add assistant message with the final response
    const assistantMessage: Message = {
      role: 'assistant',
      content: data.message,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    setIsProcessing(false);
    
    // Check if we should keep the browser view open
    const shouldKeepBrowserOpen = data.keep_browser_open === true || 
                                 (data.message && data.message.includes("I'll keep the browser open"));
    
    // Only reset the browserStreamUrl if we don't need to keep it open
    if (!shouldKeepBrowserOpen) {
      console.log("Closing browser view after completion");
      setBrowserStreamUrl(null);
    } else {
      console.log("Keeping browser view open after completion");
    }
    
    // Clear status updates after a short delay to show completion
    setTimeout(() => {
      setStatusUpdates([]);
    }, 2000);
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
  
  // Handle clarification event
  const handleClarificationEvent = (data: any) => {
    // Add assistant message asking for clarification
    const assistantMessage: Message = {
      role: 'assistant',
      content: data.message,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    setIsProcessing(false);
  };
  
  // Get shareable link for this conversation
  const getShareableLink = () => {
    const url = new URL(window.location.href);
    return url.toString();
  };
  
  // Copy shareable link to clipboard
  const copyShareableLink = () => {
    navigator.clipboard.writeText(getShareableLink());
  };
  
  // Start a new chat
  const handleNewChat = () => {
    // Redirect to new session
    router.push('/?session=new');
  };
  
  return (
    <div className="flex flex-col w-full h-full">
      {/* New Header Component */}
      <header className="bg-zinc-900 text-white p-4 flex justify-between items-center border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <h1 className="text-xl font-semibold">AI Assistant</h1>
          {sessionId && <span className="text-xs text-zinc-400">Session: {sessionId}</span>}
        </div>
        <div className="flex gap-2">
          <button 
            onClick={handleNewChat}
            className="px-3 py-1 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-md transition-colors"
          >
            New Chat
          </button>
          <button 
            onClick={copyShareableLink}
            className="px-3 py-1 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-md transition-colors flex items-center gap-1"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
            </svg>
            Share
          </button>
        </div>
      </header>

      {/* Updated main content area - now full width */}
      <div className="flex-1 overflow-hidden flex justify-center">
        <div className="flex grow flex-col h-full w-full max-w-[1000px] gap-2">
          <div className="h-[calc(100vh-140px)] overflow-y-auto px-4 md:px-10 flex flex-col">
            <div className="mt-auto space-y-5 pt-4">
              {messages.map((msg, index) => (
                <ChatMessage
                  key={`${msg.role}-${index}`}
                  role={msg.role}
                  content={msg.content}
                  timestamp={msg.timestamp}
                  isLoading={index === messages.length - 1 && msg.role === 'assistant' && isProcessing}
                />
              ))}
              
              {/* Status updates and activity timeline */}
              {isProcessing && statusUpdates.length > 0 && (
                <div className="flex justify-start w-full">
                  <StatusIndicator updates={statusUpdates} />
                </div>
              )}
              
              {/* Browser view - shows after some status updates have accumulated */}
              {browserStreamUrl && statusUpdates.filter(u => u.type !== 'thinking').length > 0 && (
                <div className="w-full mb-6 mt-2">
                  <div className="bg-zinc-900 text-white rounded-t-lg p-2 flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <circle cx="8.5" cy="8.5" r="1.5"></circle>
                        <polyline points="21 15 16 10 5 21"></polyline>
                      </svg>
                      <span className="text-zinc-400">Operator Browser</span>
                    </div>
                    <div className="h-5 w-5 flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                        <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
                      </svg>
                    </div>
                  </div>
                  <div className="browser-view">
                    <iframe 
                      src={browserStreamUrl}
                      className="w-full h-[400px]"
                      frameBorder="0"
                      title="Browser View"
                    ></iframe>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          </div>
          
          <ChatInput
            onSendMessage={handleSendMessage}
            isDisabled={!isConnected || isProcessing}
            placeholder="Message..."
          />
        </div>
      </div>
    </div>
  );
};

export default Chat; 