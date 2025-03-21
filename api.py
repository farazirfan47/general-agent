from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
import uuid
from app.agents.agent_loop import AgentLoop
from app.memory.redis_memory import RedisMemory
from app.events.event_bus import register_websocket_handler, register_event_handler, unregister_websocket_handler, list_websocket_handlers, clear_all_websocket_handlers
import os
from redis import Redis

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store WebSocket connections by session ID
active_connections: Dict[str, List[WebSocket]] = {}

# Store running agent loops by session ID
active_agents: Dict[str, AgentLoop] = {}

# Get Redis URL from environment variable with a fallback for local development
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = Redis.from_url(redis_url)

# Add this at the top level of your api.py, after imports
clear_all_websocket_handlers()  # Clear any handlers from previous runs

# At the top of your file, add a counter for debugging
_websocket_connection_counter = 0

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    message: str

# Redis manager for session storage
memory_manager = RedisMemory()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str = None):
    global _websocket_connection_counter
    _websocket_connection_counter += 1
    connection_id = _websocket_connection_counter
    
    print(f"[API] New WebSocket connection #{connection_id} for session: {session_id}")
    list_websocket_handlers()
    
    # Clear all handlers on each new connection to ensure we start fresh
    # This is a temporary solution until we properly fix the handler tracking
    clear_all_websocket_handlers()
    list_websocket_handlers()
    
    await websocket.accept()
    
    # Initialize session_id if not provided
    if not session_id or session_id == "new":
        session_id = str(uuid.uuid4())
    
    # Store WebSocket connection
    if session_id not in active_connections:
        active_connections[session_id] = []
    active_connections[session_id].append(websocket)
    
    # Track connection status
    connection_active = True
    
    # Store the handler ID in the WebSocket object for later cleanup
    websocket._handler_id = None
    
    try:
        # Send initial session information
        await websocket.send_text(json.dumps({
            "type": "session_info",
            "data": {"session_id": session_id}
        }))
        
        # Create agent loop if not exists
        if session_id not in active_agents:
            agent = AgentLoop(session_id=session_id)
            active_agents[session_id] = agent
        else:
            agent = active_agents[session_id]
        
        # Register WebSocket event handler
        async def websocket_event_handler(event_type, data):
            # Check if connection is still active before sending
            nonlocal connection_active
            if not connection_active:
                return
            
            # Skip empty events
            if data is None or (isinstance(data, dict) and len(data) == 0):
                print(f"Skipping empty {event_type} event")
                return
            
            # Make sure data is serializable
            try:
                # Always make a deep copy to avoid modifying the original data
                import copy
                websocket_data = copy.deepcopy(data) if data is not None else {}
                
                # Ensure we have a dictionary
                if not isinstance(websocket_data, dict):
                    if isinstance(websocket_data, str):
                        # Try to convert string to dict if it looks like JSON
                        try:
                            # The json module is already imported at the top level
                            if websocket_data.strip().startswith('{'):
                                websocket_data = json.loads(websocket_data)
                            else:
                                websocket_data = {"message": websocket_data}
                        except:
                            websocket_data = {"message": websocket_data}
                    else:
                        # For any other non-dict type, convert to a simple dict with a message
                        websocket_data = {"message": str(websocket_data)}
                
                # Debug logging for stream_url
                if "stream_url" in websocket_data:
                    stream_url = websocket_data["stream_url"]
                    print(f"Found stream_url in {event_type} event: {stream_url[:50]}...")
                
                # Handle different event types with appropriate frontend event names
                websocket_event_type = event_type
                
                # Map browser_started events to create the browser iframe immediately
                if event_type == "browser_started":
                    # For browser_started events, send a special event to create the browser iframe
                    websocket_event_type = "cua_event"  # Use the existing frontend event type
                    # Add some extra context for the frontend
                    websocket_data["action"] = "browser_started"
                    websocket_data["description"] = "Browser session initialized"
                
                # Convert to JSON and send
                if connection_active:
                    print(f"Sending {websocket_event_type} event: {websocket_data}")
                    await websocket.send_text(json.dumps({
                        "type": websocket_event_type,
                        "data": websocket_data
                    }))
            except WebSocketDisconnect:
                # Mark connection as inactive if we get a disconnect exception
                connection_active = False
            except Exception as e:
                print(f"Error sending WebSocket event: {str(e)}")
                # Try to send a simple error message
                try:
                    if connection_active:
                        await websocket.send_text(json.dumps({
                            "type": "error", 
                            "data": {"message": f"Error processing {event_type} event: {str(e)}"}
                        }))
                except:
                    pass
        
        # Register the handler with the global event bus for WebSocket events
        handler_id = register_websocket_handler(websocket_event_handler)
        websocket._handler_id = handler_id  # Store for cleanup
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                user_message = message_data.get("message", "")
                
                # Process message with agent
                response = await agent.run_async(user_message, interactive_clarification=False)
                
                # Check if response is a clarification request
                if isinstance(response, dict) and response.get("type") == "clarification_needed":
                    # Send the clarification request to the client
                    await websocket.send_text(json.dumps({
                        "type": "clarification",
                        "data": {
                            "questions": response.get("questions", []),
                            "message": response.get("message", "")
                        }
                    }))
                else:
                    # Complete event is sent by the event handler for normal responses
                    pass
            
            elif message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong", 
                    "data": {"timestamp": message_data.get("timestamp")}
                }))
    
    except WebSocketDisconnect:
        # Mark connection as inactive
        connection_active = False
        # Remove WebSocket connection
        if session_id in active_connections:
            active_connections[session_id].remove(websocket)
            if not active_connections[session_id]:
                del active_connections[session_id]
        
        # Unregister the WebSocket handler using the stored ID
        if hasattr(websocket, '_handler_id') and websocket._handler_id:
            unregister_websocket_handler(websocket._handler_id)
            websocket._handler_id = None
    
    except Exception as e:
        try:
            if connection_active:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "data": {"message": str(e)}
                }))
        except:
            pass
    
    finally:
        # Mark connection as inactive in case we exit the loop for any reason
        connection_active = False
        
        # Clean up event handler registration
        try:
            if hasattr(websocket, '_handler_id') and websocket._handler_id:
                unregister_websocket_handler(websocket._handler_id)
                websocket._handler_id = None
        except:
            pass

@app.post("/api/chat", response_model=None)  # Remove response_model for dynamic response
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Process a chat request (non-WebSocket version)
    """
    session_id = request.session_id
    
    # Create session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Initialize agent loop if not exists
    if session_id not in active_agents:
        active_agents[session_id] = AgentLoop(session_id=session_id)
    
    # Process the message
    result = await active_agents[session_id].run_async(request.message, interactive_clarification=False)
    
    # Check if result is a clarification request
    if isinstance(result, dict) and result.get("type") == "clarification_needed":
        return {
            "session_id": session_id,
            "type": "clarification_needed",
            "questions": result.get("questions", []), 
            "message": result.get("message", "")
        }
    else:
        # Return normal response
        return ChatResponse(
            session_id=session_id,
            message=result
        )

@app.get("/api/conversation/{session_id}")
async def get_conversation(session_id: str):
    """
    Get full conversation history for a session
    """
    try:
        # Initialize memory manager if needed
        if not memory_manager:
            return {"error": "Memory manager not initialized"}
        
        # Get conversation history
        conversation = memory_manager.get_conversation(session_id)
        state = memory_manager.get_state(session_id)
        
        return {
            "session_id": session_id,
            "conversation": conversation,
            "state": state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 