from fastapi import FastAPI, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
import uuid
from app.agents.agent_loop import AgentLoop
from app.memory.redis_memory import RedisMemory

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

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    message: str

# Redis manager for session storage
memory_manager = RedisMemory()

# Custom AgentLoop class that emits events during processing
class WebSocketAgentLoop(AgentLoop):
    def __init__(self, session_id=None, redis_url=None, websocket=None):
        super().__init__(session_id=session_id, redis_url=redis_url)
        self.websocket = websocket
    
    async def emit_event(self, event_type, data):
        """Send event updates to the WebSocket client"""
        if self.websocket:
            event = {
                "type": event_type,
                "data": data
            }
            await self.websocket.send_text(json.dumps(event))
    
    async def run_async(self, user_query: str) -> str:
        """Async version of run method with WebSocket events"""
        print(f"\n=== Starting New Query ===")
        print(f"User Query: {user_query}")
        print(f"Session ID: {self.session_id}")
        
        # Store the original query in state and add to conversation
        self.memory_manager.update_state(self.session_id, {"original_query": user_query})
        self.memory_manager.add_user_message(self.session_id, user_query)
        
        await self.emit_event("thinking", {"message": "Processing your request..."})
        
        # Get conversation history for context
        conversation = self.memory_manager.get_conversation(self.session_id)
        
        # Get plan from the Planner
        await self.emit_event("thinking", {"message": "Creating plan..."})
        plan_data = self.planner.create_plan(conversation)
        
        # Check if clarification is needed (simplified for now)
        if plan_data.get("clarification_needed", False):
            await self.emit_event("clarification", {"questions": plan_data.get("clarifying_questions", [])})
            return "Clarification needed"
        
        # Extract the plan steps
        plan = plan_data.get("plan", [])
        
        if not plan:
            return "Failed to create a plan. Please try again with a more specific query."
        
        await self.emit_event("plan", {"plan": plan})
        
        # Store the plan in state
        self.memory_manager.update_state(self.session_id, {"plan": plan})
        
        # Execute the plan
        return await self._execute_plan_async(plan)
    
    async def _execute_plan_async(self, plan: List[Dict]) -> str:
        """Async version of _execute_plan with WebSocket events"""
        await self.emit_event("executing", {"message": "Executing plan..."})
        
        # Get current state
        state = self.memory_manager.get_state(self.session_id)
        
        # Initialize execution context
        context = {
            "plan": plan,
            "original_query": state.get("original_query", ""),
            "completed_steps": [],
            "current_step": 0,
            "results": {},
        }
        
        # Execute each step in sequence
        total_steps = len(plan)
        for i, step in enumerate(plan, 1):
            step_description = step['description']
            await self.emit_event("step", {
                "current": i, 
                "total": total_steps, 
                "description": step_description
            })
            
            # Update context for current step
            context["current_step"] = i
            
            # Create memory object with conversation
            memory = {
                "conversation": self.memory_manager.get_conversation(self.session_id)
            }
            
            # Monitor for tool usage
            def tool_callback(tool_name, args):
                asyncio.create_task(self.emit_event("tool_usage", {
                    "tool": tool_name,
                    "args": args
                }))
            
            # Custom executor logic would go here to track tool usage
            # For now, we'll just simulate it
            await self.emit_event("executing_step", {"step": i, "description": step_description})
            
            # Check for specific tools in description
            if "web search" in step_description.lower():
                await self.emit_event("tool_usage", {"tool": "web_search", "query": state.get("original_query", "")})
            
            if "browser" in step_description.lower() or "computer use" in step_description.lower():
                await self.emit_event("tool_usage", {"tool": "computer_use", "task": step_description})
            
            # Simulate CUA agent real-time events if the step involves computer use
            if "browser" in step_description.lower() or "computer use" in step_description.lower():
                # Simulate some browser interactions
                await asyncio.sleep(1)
                await self.emit_event("cua_event", {"action": "click", "x": 500, "y": 300})
                await asyncio.sleep(0.5)
                await self.emit_event("cua_event", {"action": "type", "text": "example search"})
                await asyncio.sleep(0.5)
                await self.emit_event("cua_event", {"action": "keypress", "keys": ["Enter"]})
                await asyncio.sleep(1)
                await self.emit_event("cua_event", {"action": "scroll", "direction": "down"})
            
            # Execute step with executor agent (simplified here)
            await asyncio.sleep(2)  # Simulate processing time
            step_result = f"Completed step {i}: {step_description}"
            
            # Update context with completed step results
            context["completed_steps"].append({
                "step": i,
                "description": step_description,
                "result": step_result
            })
            context["results"][f"step_{i}"] = step_result
            
            # Update context in state
            self.memory_manager.update_state(self.session_id, {"context": context})
        
        # Generate final response
        await self.emit_event("finalizing", {"message": "Generating final response..."})
        
        # Simulate generating final response
        await asyncio.sleep(1)
        conversation = self.memory_manager.get_conversation(self.session_id)
        final_response = f"I've completed your request: {state.get('original_query', '')}"
        
        # Add final response to conversation
        self.memory_manager.add_assistant_message(self.session_id, final_response)
        
        await self.emit_event("complete", {"message": final_response})
        
        return final_response


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str = None):
    await websocket.accept()
    
    # Initialize session_id if not provided
    if not session_id or session_id == "new":
        session_id = str(uuid.uuid4())
    
    # Store WebSocket connection
    if session_id not in active_connections:
        active_connections[session_id] = []
    active_connections[session_id].append(websocket)
    
    try:
        # Send initial session information
        await websocket.send_text(json.dumps({
            "type": "session_info",
            "data": {"session_id": session_id}
        }))
        
        # Create agent loop if not exists
        if session_id not in active_agents:
            active_agents[session_id] = WebSocketAgentLoop(session_id=session_id, websocket=websocket)
        else:
            active_agents[session_id].websocket = websocket
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                user_message = message_data.get("message", "")
                
                # Process message with agent
                response = await active_agents[session_id].run_async(user_message)
            
            elif message_data.get("type") == "ping":
                await websocket.send_text(json.dumps({
                    "type": "pong", 
                    "data": {"timestamp": message_data.get("timestamp")}
                }))
    
    except WebSocketDisconnect:
        # Remove WebSocket connection
        if session_id in active_connections:
            active_connections[session_id].remove(websocket)
            if not active_connections[session_id]:
                del active_connections[session_id]
    
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "data": {"message": str(e)}
        }))


@app.post("/api/chat", response_model=ChatResponse)
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
        active_agents[session_id] = WebSocketAgentLoop(session_id=session_id)
    
    # Process the message in background
    result = await active_agents[session_id].run_async(request.message)
    
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