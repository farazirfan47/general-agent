import json
import uuid
import time
from typing import Dict, List, Any, Optional
import redis
import os

class RedisMemory:
    """
    Redis-based memory system for the agent conversations and state.
    Provides persistence and session management for multi-turn conversations.
    """
    def __init__(self, redis_url=None, expire_time=86400):  # Default expiry: 24 hours
        """
        Initialize the Redis memory manager.
        
        Args:
            redis_url: Redis connection URL (defaults to REDIS_URL env var)
            expire_time: Default TTL for conversation records in seconds
        """
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(self.redis_url)
        self.expire_time = expire_time
        
    def create_session(self) -> str:
        """
        Create a new conversation session.
        
        Returns:
            session_id: Unique identifier for the conversation
        """
        session_id = str(uuid.uuid4())
        timestamp = time.time()
        
        # Initialize empty conversation and state
        session_data = {
            "created_at": timestamp,
            "updated_at": timestamp,
            "state": {},
            "conversation": []
        }
        
        # Store in Redis
        self.redis.set(
            f"session:{session_id}", 
            json.dumps(session_data),
            ex=self.expire_time
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve a session by ID.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Session data or None if not found
        """
        session_data = self.redis.get(f"session:{session_id}")
        if not session_data:
            return None
        
        return json.loads(session_data)
    
    def update_session(self, session_id: str, data: Dict) -> bool:
        """
        Update an existing session with new data.
        
        Args:
            session_id: The session identifier
            data: The complete session data to store
            
        Returns:
            Success flag
        """
        # Update timestamp
        data["updated_at"] = time.time()
        
        # Store in Redis with TTL
        return self.redis.set(
            f"session:{session_id}",
            json.dumps(data),
            ex=self.expire_time
        )
    
    def add_message(self, session_id: str, message: Any) -> bool:
        """
        Add any type of message to the conversation history.
        
        Args:
            session_id: The session identifier
            message: The message to add (can be a dict, string, or any JSON-serializable object)
            
        Returns:
            Success flag
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Custom JSON encoder to handle complex objects
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                # Try to get object's __dict__ attribute
                try:
                    return obj.__dict__
                except AttributeError:
                    # If that fails, try string representation
                    try:
                        return str(obj)
                    except:
                        return f"<Unserializable object of type {type(obj).__name__}>"
        
        # Ensure message is JSON-serializable
        try:
            # First attempt to serialize with the custom encoder
            serialized = json.dumps(message, cls=CustomEncoder)
            # If successful, parse it back to get a fully serializable object
            serializable_message = json.loads(serialized)
            if isinstance(serializable_message, list):
                session_data["conversation"] += serializable_message
            else:
                session_data["conversation"].append(serializable_message)
        except Exception as e:
            # If all serialization attempts fail, store a simplified version
            error_message = {
                "error": f"Could not serialize message: {str(e)}",
                "object_type": str(type(message).__name__),
                "string_representation": str(message)
            }
            session_data["conversation"].append(error_message)
        
        # Update session
        return self.update_session(session_id, session_data)
    
    def add_user_message(self, session_id: str, message: str) -> bool:
        """
        Add a user message to the conversation history.
        
        Args:
            session_id: The session identifier
            message: The user's message
            
        Returns:
            Success flag
        """
        return self.add_message(session_id, {
            "role": "user",
            "content": message
        })
    
    def add_assistant_message(self, session_id: str, message: str) -> bool:
        """
        Add an assistant message to the conversation history.
        
        Args:
            session_id: The session identifier
            message: The assistant's message
            
        Returns:
            Success flag
        """
        return self.add_message(session_id, {
            "role": "assistant",
            "content": message
        })
    
    def get_conversation(self, session_id: str) -> List[Dict]:
        """
        Get the full conversation history for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            List of conversation messages
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return []
        
        return session_data.get("conversation", [])
    
    def update_state(self, session_id: str, state_updates: Dict) -> bool:
        """
        Update the state for a session.
        
        Args:
            session_id: The session identifier
            state_updates: Dictionary of state updates to apply
            
        Returns:
            Success flag
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Update state with new values
        session_data["state"].update(state_updates)
        
        # Update session
        return self.update_session(session_id, session_data)
    
    def get_state(self, session_id: str) -> Dict:
        """
        Get the current state for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Current state dict
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return {}
        
        return session_data.get("state", {})
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all associated data.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Success flag
        """
        return self.redis.delete(f"session:{session_id}") > 0 