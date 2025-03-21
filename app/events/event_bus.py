"""
Event bus for handling various events in the application.
This module provides mechanisms for emitting and subscribing to events.
"""

import asyncio
from typing import Dict, List, Callable, Any, Optional

# Store event handlers by event type
_event_handlers: Dict[str, List[Callable]] = {}

# For WebSocket events
_websocket_handlers: List[Callable] = []

def register_event_handler(event_type: str, handler: Callable) -> None:
    """
    Register a handler for a specific event type.
    
    Args:
        event_type: The type of event to handle
        handler: Function to call when event is emitted
    """
    if event_type not in _event_handlers:
        _event_handlers[event_type] = []
    _event_handlers[event_type].append(handler)

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
    handlers = _event_handlers.get(event_type, [])
    for handler in handlers:
        try:
            handler(data)
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
    handlers = _event_handlers.get(event_type, [])
    print(f"[EventBus] {len(handlers)} specific handlers for {event_type}")
    
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
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