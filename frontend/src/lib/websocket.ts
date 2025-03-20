type WebSocketCallback = (event: any) => void;

interface WebSocketManager {
  socket: WebSocket | null;
  sessionId: string | null;
  eventListeners: Map<string, WebSocketCallback[]>;
  connect: (sessionId?: string) => Promise<string>;
  disconnect: () => void;
  sendMessage: (message: string) => void;
  addEventListener: (event: string, callback: WebSocketCallback) => void;
  removeEventListener: (event: string, callback: WebSocketCallback) => void;
}

// Create WebSocket manager singleton
export const wsManager: WebSocketManager = {
  socket: null,
  sessionId: null,
  eventListeners: new Map(),

  // Connect to WebSocket server
  connect: (sessionId = 'new') => {
    return new Promise((resolve, reject) => {
      try {
        // Check if we're in a browser environment
        if (typeof window === 'undefined') {
          reject(new Error('WebSocket can only be used in browser environment'));
          return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
        const host = window.location.host;
        const url = `${protocol}://${host}/ws/${sessionId}`;
        
        // Close existing connection if any
        if (wsManager.socket) {
          wsManager.socket.close();
        }
        
        // Create new WebSocket connection
        wsManager.socket = new WebSocket(url);
        
        // Setup event handlers
        wsManager.socket.onopen = () => {
          console.log('WebSocket connected');
        };
        
        wsManager.socket.onclose = () => {
          console.log('WebSocket disconnected');
        };
        
        wsManager.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
        
        // Handle incoming messages
        wsManager.socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            // Handle session initialization
            if (data.type === 'session_info' && data.data.session_id) {
              wsManager.sessionId = data.data.session_id;
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
          if (!wsManager.sessionId) {
            reject(new Error('WebSocket connection timeout'));
          }
        }, 5000);
      } catch (error) {
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
  }
};

// Define event types
export enum WebSocketEventType {
  Thinking = 'thinking',
  Plan = 'plan',
  Step = 'step',
  ToolUsage = 'tool_usage',
  CuaEvent = 'cua_event',
  Executing = 'executing',
  ExecutingStep = 'executing_step',
  Complete = 'complete',
  Error = 'error',
  Clarification = 'clarification',
  All = 'all'
} 