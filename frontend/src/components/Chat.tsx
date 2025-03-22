import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import StatusIndicator from './StatusIndicator';
import { wsManager, WebSocketEventType } from '@/lib/websocket';
import { WS_URL, API_URL } from '../config/api';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  requiresResponse?: boolean;
  clarificationId?: string;
  isClarification?: boolean;
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
  const [clarificationMode, setClarificationMode] = useState<boolean>(false);
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
    wsManager.addEventListener(WebSocketEventType.CuaClarification, handleCuaClarificationEvent);
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
    wsManager.removeEventListener(WebSocketEventType.CuaClarification, handleCuaClarificationEvent);
  };
  
  // Fetch conversation history for an existing session
  const fetchConversationHistory = async (sessionId: string) => {
    try {
      const response = await fetch(`${API_URL}/api/conversation/${sessionId}`);
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
    // Check if we're in clarification mode
    if (clarificationMode) {
      // Find the last message that requires a response
      const lastClarificationMessage = [...messages].reverse()
        .find(msg => msg.role === 'assistant' && msg.requiresResponse);
      
      if (lastClarificationMessage && lastClarificationMessage.clarificationId) {
        // Add user message to the list
        const userMessage: Message = {
          role: 'user',
          content: message,
          timestamp: new Date(),
          isClarification: true
        };
        
        // Update the clarification message to show it's been answered
        const updatedMessages = messages.map(msg => {
          if (msg === lastClarificationMessage) {
            return {
              ...msg,
              requiresResponse: false // Mark as no longer requiring response
            };
          }
          return msg;
        });
        
        // Add the user's response to the messages
        setMessages([...updatedMessages, userMessage]);
        setIsProcessing(true);
        setClarificationMode(false);

        console.log("Sending clarification response:", {
          type: 'clarification_response',
          data: {
            response: message,
            id: lastClarificationMessage.clarificationId
          }
        });
        
        // Before sending the clarification response
        console.log("WebSocket readyState:", wsManager.socket?.readyState);
        // 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
        
        // Use a fetch call to the debug endpoint
        fetch(`${API_URL}/api/send_clarification/${lastClarificationMessage.clarificationId}/${encodeURIComponent(message)}`, {
          method: 'POST',
        })
        .then(response => response.json())
        .then(data => console.log('Clarification sent successfully:', data))
        .catch(error => console.error('Error sending clarification:', error));
        
        // Add a thinking status
        addStatusUpdate({
          type: 'thinking',
          message: 'Processing your clarification...',
          details: null
        });
        
        return;
      }
    }
    
    // Regular message handling (your existing code)
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
  
  // Add a new status update - with validation to prevent empty updates
  const addStatusUpdate = ({ type, message, details }: { type: StatusUpdate['type'], message: string, details: any }) => {
    // Skip empty or meaningless updates
    if (!message || message.trim() === '') {
      console.log("Skipping empty status update");
      return;
    }
    
    const update: StatusUpdate = {
      id: Math.random().toString(36).substring(2, 9),
      type,
      message,
      details,
      timestamp: new Date()
    };
    
    setStatusUpdates(prev => [...prev, update]);
  };
  
  // Event handlers with validation
  const handleThinkingEvent = (data: any) => {
    // Skip if data is empty or has no message
    if (!data || !data.message || data.message.trim() === '') {
      return;
    }
    
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
    // Skip empty events
    if (!data) {
      console.log("Skipping empty CUA event");
      return;
    }
    
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
    
    // Skip events with no action or empty action
    if (!data.action || data.action.trim() === '') {
      console.log("Skipping CUA event with no action");
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
    // Skip if data is empty or has no message
    if (!data || (!data.message && !data.questions)) {
      console.log("Skipping empty clarification event");
      return;
    }
    
    // Construct a meaningful message from the questions if message is not provided
    let clarificationMessage = data.message || "";
    
    // If there's no message but there are questions, create a message from the questions
    if (!clarificationMessage && data.questions && data.questions.length > 0) {
      clarificationMessage = "I need some clarification:\n\n" + 
        data.questions.map((q: string, i: number) => `${i+1}. ${q}`).join("\n");
    }
    
    // Add assistant message asking for clarification
    const assistantMessage: Message = {
      role: 'assistant',
      content: clarificationMessage,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    setIsProcessing(false);
    
    // Clear status updates after adding the clarification message
    setStatusUpdates([]);
  };
  
  // Handle CUA clarification event
  const handleCuaClarificationEvent = (data: any) => {
    // Skip if data is empty or has no question
    if (!data || !data.question) {
      console.log("Skipping empty CUA clarification event");
      return;
    }
    
    console.log("Received CUA clarification request:", data);
    console.log("Setting clarification mode to true");
    console.log("Storing clarification ID:", data.id);
    
    // Extract the question and ID
    const question = data.question;
    const clarificationId = data.id;
    
    // Add assistant message asking the clarification question
    const assistantMessage: Message = {
      role: 'assistant',
      content: question,
      timestamp: new Date(),
      requiresResponse: true,  // Flag to indicate this needs a direct response
      clarificationId: clarificationId  // Store the ID for the response
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    
    // Set a special processing state that indicates we're waiting for user clarification
    setIsProcessing(false);
    setClarificationMode(true);
    
    // IMPORTANT: Don't clear status updates during clarification
    // This was causing the browser iframe to disappear
    // setStatusUpdates([]);
    
    // Instead, add a clarification status update while keeping existing ones
    addStatusUpdate({
      type: 'thinking',
      message: 'Waiting for your clarification...',
      details: null
    });
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

      {/* Updated main content area with reordered elements */}
      <div className="flex-1 overflow-hidden flex justify-center">
        <div className="flex grow flex-col h-full w-full max-w-[1000px] gap-2">
          <div className="h-[calc(100vh-140px)] overflow-y-auto px-4 md:px-10 flex flex-col">
            <div className="mt-auto space-y-5 pt-4">
              {/* All messages in conversation order, including answered clarifications */}
              {messages
                .filter(msg => !(msg.role === 'assistant' && msg.requiresResponse))
                .map((msg, index) => (
                  <ChatMessage
                    key={`${msg.role}-${index}`}
                    content={msg.content}
                    role={msg.role}
                    timestamp={msg.timestamp}
                    isLoading={index === messages.length - 1 && msg.role === 'assistant' && isProcessing}
                  />
                ))}
                
              {/* Status updates and activity timeline - show during processing OR clarification mode */}
              {(isProcessing || clarificationMode) && statusUpdates.length > 0 && (
                <div className="flex justify-start w-full">
                  <StatusIndicator updates={statusUpdates} />
                </div>
              )}
              
              {/* Browser view - shown before clarification questions */}
              {browserStreamUrl && statusUpdates.filter(u => u.type !== 'thinking').length > 0 && (
                <div className="w-[530px] mb-6 mt-2">
                  <div className="bg-zinc-900 text-white rounded-t-lg p-2 flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <circle cx="8.5" cy="8.5" r="1.5"></circle>
                        <polyline points="21 15 16 10 5 21"></polyline>
                      </svg>
                      <span className="text-zinc-400">Browser</span>
                    </div>
                    <div className="h-5 w-5 flex items-center justify-center">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
                        <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
                      </svg>
                    </div>
                  </div>
                  <div className="browser-view w-full h-[400px] border border-zinc-800 rounded-b-lg overflow-hidden relative">
                    <iframe 
                      src={browserStreamUrl}
                      className="w-full h-full border-0"
                      title="Browser View"
                      style={{ 
                        display: 'block',
                        width: '100%',
                        height: '100%',
                        overflow: 'hidden'
                      }}
                      sandbox="allow-same-origin allow-scripts"
                      scrolling="auto"
                    ></iframe>
                    
                    {/* Overlay for iframe interaction */}
                    <div 
                      className="absolute inset-0 bg-transparent hover:bg-gradient-to-t hover:from-black/50 hover:to-transparent cursor-pointer group transition-all duration-300"
                      onClick={(e) => {
                        // Remove the overlay when clicked
                        e.currentTarget.style.display = 'none';
                      }}
                    >
                      <div className="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-all duration-200 border border-white text-white bg-transparent px-4 py-2 rounded-full font-medium shadow-lg hover:scale-105">
                        Take Control
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Pending clarification messages - shown after browser view */}
              {messages
                .filter(msg => msg.role === 'assistant' && msg.requiresResponse)
                .map((msg, index) => (
                  <ChatMessage
                    key={`clarification-${index}`}
                    role={msg.role}
                    content={msg.content}
                    timestamp={msg.timestamp}
                    isLoading={false}
                  />
                ))}
              
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