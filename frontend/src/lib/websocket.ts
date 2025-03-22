import { WS_URL } from '../config/api';

type WebSocketCallback = (event: any) => void;

interface WebSocketManager {
  socket: WebSocket | null;
  sessionId: string | null;
  eventListeners: Map<string, WebSocketCallback[]>;
  messageQueue: any[];
  isConnecting: boolean;
  connect: (sessionId?: string) => Promise<string>;
  disconnect: () => void;
  sendMessage: (message: string) => void;
  addEventListener: (event: string, callback: WebSocketCallback) => void;
  removeEventListener: (event: string, callback: WebSocketCallback) => void;
  sendEvent: (eventType: string, data: any) => void;
}

// Create WebSocket manager singleton
export const wsManager: WebSocketManager = {
  socket: null,
  sessionId: null,
  eventListeners: new Map(),
  messageQueue: [],
  isConnecting: false,

  // Connect to WebSocket server
  connect: async (sessionId?: string): Promise<string> => {
    // If already connecting, return a promise that resolves when the connection is established
    if (wsManager.isConnecting) {
      console.log("Already connecting to WebSocket, waiting for connection...");
      return new Promise((resolve, reject) => {
        const checkConnection = setInterval(() => {
          if (wsManager.sessionId) {
            clearInterval(checkConnection);
            resolve(wsManager.sessionId);
          }
        }, 100);
        
        // Timeout after 5 seconds
        setTimeout(() => {
          clearInterval(checkConnection);
          reject(new Error("Connection timeout while waiting for existing connection"));
        }, 5000);
      });
    }
    
    // If already connected with the same session ID, return the session ID
    if (wsManager.socket && 
        wsManager.socket.readyState === WebSocket.OPEN && 
        wsManager.sessionId && 
        sessionId && 
        wsManager.sessionId === sessionId) {
      console.log(`Already connected to session ${sessionId}`);
      return wsManager.sessionId;
    }
    
    // Set connecting flag
    wsManager.isConnecting = true;
    
    return new Promise((resolve, reject) => {
      try {
        // Use 'new' as default if sessionId is undefined
        const actualSessionId = sessionId || 'new';
        
        // Close existing connection if any
        if (wsManager.socket) {
          console.log("Closing existing WebSocket connection before creating a new one");
          wsManager.socket.close();
          wsManager.socket = null;
        }
        
        // Clear any existing session ID
        wsManager.sessionId = null;
        
        // Determine WebSocket URL
        const isNextDevServer = process.env.NODE_ENV === 'development';
        let wsUrl: string;
        if (isNextDevServer) {
          wsUrl = actualSessionId === 'new' 
            ? `/ws/new` 
            : `/ws/${actualSessionId}`;
        } else {
          wsUrl = actualSessionId === 'new' 
            ? `${WS_URL}/ws/new` 
            : `${WS_URL}/ws/${actualSessionId}`;
        }
        
        console.log(`Connecting to WebSocket at ${wsUrl}`);
        
        // Create new WebSocket connection
        const ws = new WebSocket(wsUrl);
        wsManager.socket = ws;
        
        // Setup event handlers
        ws.onopen = () => {
          console.log('WebSocket connected');
        };
        
        ws.onclose = () => {
          console.log('WebSocket disconnected');
          wsManager.socket = null; // Clear the socket reference
          wsManager.isConnecting = false; // Reset connecting flag
        };
        
        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          wsManager.isConnecting = false; // Reset connecting flag
          reject(error);
        };
        
        // Handle incoming messages
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // Handle session initialization
            if (data.type === 'session_info' && data.data.session_id) {
              wsManager.sessionId = data.data.session_id;
              wsManager.isConnecting = false; // Reset connecting flag
              resolve(data.data.session_id);
            }
            
            // Notify all registered listeners for this event type
            const listeners = wsManager.eventListeners.get(data.type) || [];
            listeners.forEach(callback => callback(data.data));
            
            // Notify 'all' event listeners
            const allListeners = wsManager.eventListeners.get('all') || [];
            allListeners.forEach(callback => callback(data));
          } catch (error) {
            console.error('Error processing WebSocket message:', error);
          }
        };
        
        // If we don't get a session_info within 5 seconds, reject
        setTimeout(() => {
          if (wsManager.isConnecting) {
            wsManager.isConnecting = false; // Reset connecting flag
            reject(new Error('WebSocket connection timeout'));
          }
        }, 5000);
      } catch (error) {
        wsManager.isConnecting = false; // Reset connecting flag
        reject(error);
      }
    });
  },

  // Disconnect WebSocket
  disconnect: () => {
    if (wsManager.socket) {
      wsManager.socket.close();
      wsManager.socket = null;
    }
    wsManager.isConnecting = false; // Reset connecting flag
  },

  // Send message through WebSocket
  sendMessage: (message: string) => {
    if (wsManager.socket && wsManager.socket.readyState === WebSocket.OPEN) {
      wsManager.socket.send(JSON.stringify({
        type: 'message',
        message,
      }));
    } else {
      console.error('WebSocket not connected');
      // Try to reconnect and then send the message
      wsManager.connect(wsManager.sessionId || undefined)
        .then(() => {
          // Wait a moment for the connection to establish
          setTimeout(() => {
            if (wsManager.socket && wsManager.socket.readyState === WebSocket.OPEN) {
              wsManager.socket.send(JSON.stringify({
                type: 'message',
                message,
              }));
            }
          }, 500);
        })
        .catch(err => console.error('Failed to reconnect WebSocket:', err));
    }
  },

  // Add event listener
  addEventListener: (event: string, callback: WebSocketCallback) => {
    if (!wsManager.eventListeners.has(event)) {
      wsManager.eventListeners.set(event, []);
    }
    wsManager.eventListeners.get(event)?.push(callback);
  },

  // Remove event listener
  removeEventListener: (event: string, callback: WebSocketCallback) => {
    if (wsManager.eventListeners.has(event)) {
      const listeners = wsManager.eventListeners.get(event) || [];
      wsManager.eventListeners.set(
        event,
        listeners.filter(cb => cb !== callback)
      );
    }
  },

  // Send custom event
  sendEvent: (eventType: string, data: any) => {
    if (!wsManager.socket || wsManager.socket.readyState !== WebSocket.OPEN) {
      console.log("WebSocket not open, attempting to reconnect...");
      // Attempt to reconnect
      wsManager.connect(wsManager.sessionId || undefined)
        .then(() => {
          console.log("Reconnected, now sending event");
          // Now send the event
          const message = { type: eventType, data: data };
          wsManager.socket?.send(JSON.stringify(message));
        })
        .catch(err => console.error("Failed to reconnect:", err));
      return;
    }

    const message = {
      type: eventType,
      data: data
    };
    console.log(`Sending WebSocket event: ${JSON.stringify(message)}`);
    wsManager.socket.send(JSON.stringify(message));
  }
};

// Define event types
export enum WebSocketEventType {
  Thinking = 'thinking',
  Plan = 'plan',
  Step = 'step',
  ToolUsage = 'tool_usage',
  CuaEvent = 'cua_event',
  CuaReasoning = 'cua_reasoning',
  Executing = 'executing',
  ExecutingStep = 'executing_step',
  Complete = 'complete',
  Error = 'error',
  Clarification = 'clarification',
  CuaClarification = 'cua_clarification',
  TookControl = 'took_control',
  TookControlResponse = 'took_control_response',
  All = 'all'
} 