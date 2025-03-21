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

def register_websocket_handler(handler: Callable) -> None:
    """
    Register a handler for all events to be sent via WebSocket.
    
    Args:
        handler: Function that takes event_type and data
    """
    _websocket_handlers.append(handler)

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
    # Call specific event handlers
    handlers = _event_handlers.get(event_type, [])
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
        except Exception as e:
            print(f"Error in {event_type} event handler: {str(e)}")
    
    # Call websocket handlers
    for handler in _websocket_handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event_type, data)
            else:
                handler(event_type, data)
        except Exception as e:
            print(f"Error in websocket handler for {event_type}: {str(e)}") 