"""
Event bus for handling various events in the application.
This module provides mechanisms for emitting and subscribing to events.
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional
import json

# Global event listeners by event type
_event_listeners: Dict[str, List[Callable]] = {}

# Global message queue for direct communication
_message_queues: Dict[str, asyncio.Queue] = {}

# For WebSocket events
_websocket_handlers: List[Callable] = []

def register_event_listener(event_type: str, listener: Callable):
    """Register a listener for a specific event type"""
    if event_type not in _event_listeners:
        _event_listeners[event_type] = []
    _event_listeners[event_type].append(listener)
    return len(_event_listeners[event_type]) - 1  # Return listener index for unregistering

def unregister_event_listener(event_type: str, listener_index: int):
    """Unregister a listener by its index"""
    if event_type in _event_listeners and 0 <= listener_index < len(_event_listeners[event_type]):
        _event_listeners[event_type].pop(listener_index)

# Direct message queue functions
def get_message_queue(queue_id: str) -> asyncio.Queue:
    """Get or create a message queue for direct communication"""
    if queue_id not in _message_queues:
        print(f"[EventBus] Creating new message queue: {queue_id}")
        _message_queues[queue_id] = asyncio.Queue()
    else:
        print(f"[EventBus] Using existing message queue: {queue_id}")
    return _message_queues[queue_id]

async def send_message(queue_id: str, message: str):
    """Send a message to a specific queue."""
    if queue_id in _message_queues:
        await _message_queues[queue_id].put(message)
        print(f"[EventBus] Message sent to queue {queue_id}: {message}")
        return True
    else:
        print(f"[EventBus] Queue {queue_id} not found")
        # Try to find a session with this ID in active_sessions
        from api import active_sessions
        if queue_id in active_sessions:
            websocket = active_sessions[queue_id]
            try:
                await websocket.send_text(json.dumps({
                    "type": "message",
                    "data": {"message": message}
                }))
                print(f"[EventBus] Message sent via WebSocket for queue {queue_id}")
                return True
            except Exception as e:
                print(f"[EventBus] Error sending message via WebSocket: {e}")
        return False

async def receive_message(queue_id: str, timeout: float = None) -> Any:
    """Receive a message from a specific queue with optional timeout"""
    queue = get_message_queue(queue_id)
    print(f"[EventBus] Waiting for message on queue {queue_id} with timeout {timeout}")
    try:
        if timeout:
            result = await asyncio.wait_for(queue.get(), timeout=timeout)
            print(f"[EventBus] Received message from queue {queue_id}: {result}")
            return result
        else:
            result = await queue.get()
            print(f"[EventBus] Received message from queue {queue_id}: {result}")
            return result
    except asyncio.TimeoutError:
        print(f"[EventBus] Timeout waiting for message on queue {queue_id}")
        return None
    except Exception as e:
        print(f"[EventBus] Error receiving message from queue {queue_id}: {e}")
        return None

def register_websocket_handler(handler: Callable) -> Callable:
    """
    Register a handler for all events to be sent via WebSocket.
    
    Args:
        handler: Function that takes event_type and data
    
    Returns:
        The handler function (for unregistration)
    """
    # Check if this handler is already registered to prevent duplicates
    if handler not in _websocket_handlers:
        print(f"[EventBus] Registering new WebSocket handler: {id(handler)}")
        _websocket_handlers.append(handler)
    else:
        print(f"[EventBus] Handler already registered: {id(handler)}")
    
    # Return the handler itself for reference (useful for unregistering)
    return handler

def emit_event(event_type: str, data: Any) -> None:
    """
    Emit an event synchronously.
    
    Args:
        event_type: The type of event
        data: Event data
    """
    # Call specific event handlers
    handlers = _event_listeners.get(event_type, [])
    for handler in handlers:
        try:
            handler(event_type, data)
        except Exception as e:
            print(f"Error in {event_type} event handler: {str(e)}")
    
    # Call websocket handlers
    for handler in _websocket_handlers:
        try:
            handler(event_type, data)
        except Exception as e:
            print(f"Error in websocket handler for {event_type}: {str(e)}")

async def emit_event_async(event_type: str, data: Any) -> None:
    """
    Emit an event asynchronously.
    
    Args:
        event_type: The type of event
        data: Event data
    """
    print(f"[EventBus] emit_event_async called for {event_type}")
    
    # Call specific event handlers
    handlers = _event_listeners.get(event_type, [])
    print(f"[EventBus] {len(handlers)} specific handlers for {event_type}")
    
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_type, data)
            else:
                handler(event_type, data)
        except Exception as e:
            print(f"Error in {event_type} event handler: {str(e)}")
    
    # Call websocket handlers
    print(f"[EventBus] {len(_websocket_handlers)} websocket handlers")
    for handler in _websocket_handlers:
        print(f"[EventBus] Calling websocket handler for {event_type}")
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_type, data)
            else:
                handler(event_type, data)
        except Exception as e:
            print(f"Error in websocket handler for {event_type}: {str(e)}") 

def unregister_websocket_handler(handler: Callable) -> None:
    """
    Unregister a handler for WebSocket events.
    
    Args:
        handler: The handler function to unregister
    """
    print(f"[EventBus] Attempting to unregister handler: {id(handler)}")
    if handler in _websocket_handlers:
        _websocket_handlers.remove(handler)
        print(f"[EventBus] Successfully unregistered handler: {id(handler)}")
    else:
        print(f"[EventBus] Handler not found in registered handlers: {id(handler)}") 

def list_websocket_handlers():
    """
    List all currently registered WebSocket handlers.
    """
    print(f"[EventBus] Currently registered WebSocket handlers ({len(_websocket_handlers)}):")
    for i, handler in enumerate(_websocket_handlers):
        print(f"  {i+1}. Handler ID: {id(handler)}") 

def clear_all_websocket_handlers():
    """
    Clear all registered WebSocket handlers.
    """
    global _websocket_handlers
    print(f"[EventBus] Clearing all {len(_websocket_handlers)} WebSocket handlers")
    _websocket_handlers = [] 

def register_event_handler(event_type: str, handler: Callable) -> None:
    """
    Register a handler for a specific event type (legacy function).
    This is kept for backward compatibility.
    
    Args:
        event_type: The type of event to handle
        handler: Function to call when event is emitted
    """
    # Wrap the handler to match the new signature
    def wrapped_handler(event_type, data):
        return handler(data)
    
    # Register with the new function
    register_event_listener(event_type, wrapped_handler) 

# For backward compatibility
def emit_event_handler(event_type: str, data: Any) -> None:
    """Legacy function for backward compatibility"""
    return emit_event(event_type, data) 