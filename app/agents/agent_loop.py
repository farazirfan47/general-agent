import os
import json
import time
from typing import Dict, List, Any, Optional
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.memory.redis_memory import RedisMemory

class AgentLoop:
    """
    Orchestrates the workflow between Planner and Executor agents.
    Manages the end-to-end process from user query to final response.
    Uses Redis for persistent memory and multi-turn conversation support.
    """
    def __init__(self, session_id: Optional[str] = None, redis_url: Optional[str] = None):
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.memory_manager = RedisMemory(redis_url=redis_url)
        
        # Create a new session or use an existing one
        if session_id:
            self.session_id = session_id
            # Verify the session exists, create a new one if it doesn't
            if not self.memory_manager.get_session(session_id):
                self.session_id = self.memory_manager.create_session()
        else:
            self.session_id = self.memory_manager.create_session()
    
    def run(self, user_query: str) -> str:
        """
        Process a user query through the complete agent workflow
        
        Args:
            user_query: The user's query or request
            
        Returns:
            Final response text
        """
        print("\n=== Starting New Query ===")
        print(f"User Query: {user_query}")
        print(f"Session ID: {self.session_id}")
        
        # Store the original query in state and add to conversation
        self.memory_manager.update_state(self.session_id, {"original_query": user_query})
        self.memory_manager.add_user_message(self.session_id, user_query)
        
        # Get conversation history for context
        conversation = self.memory_manager.get_conversation(self.session_id)
        
        # Get plan from the Planner
        plan_data = self.planner.create_plan(conversation)
        
        # Check if clarification is needed
        while plan_data.get("clarification_needed", False):
            clarifying_questions = plan_data.get("clarifying_questions", [])
            
            print("\n=== Clarification Needed ===")
            for i, question in enumerate(clarifying_questions, 1):
                print(f"{i}. {question}")
            
            user_clarification = input("\nPlease provide clarifications: ")
            
            # Store the clarification
            assistant_message = "I need some clarification: " + " ".join(clarifying_questions)
            self.memory_manager.add_assistant_message(self.session_id, assistant_message)
            self.memory_manager.add_user_message(self.session_id, user_clarification)
            
            # Refresh conversation history
            conversation = self.memory_manager.get_conversation(self.session_id)
            
            # Update the plan with clarification - now just call create_plan again with updated conversation
            plan_data = self.planner.create_plan(conversation)
        
        # Extract the plan steps
        plan = plan_data.get("plan", [])
        
        if not plan:
            print(plan_data)
            return "Failed to create a plan. Please try again with a more specific query."
        
        print("\n=== Plan Created ===")
        print(json.dumps(plan, indent=2))

        # Store the plan in state
        self.memory_manager.update_state(self.session_id, {"plan": plan})
        
        # Execute the plan
        return self._execute_plan(plan)
    
    def _execute_plan(self, plan: List[Dict]) -> str:
        """
        Execute each step of the plan and generate final response
        
        Args:
            plan: List of plan steps to execute
            
        Returns:
            Final response text
        """
        print("\n=== Executing Plan ===")
        
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
            print(f"\n--- Step {i}/{total_steps}: {step['description']} ---")
            
            # Update context for current step
            context["current_step"] = i
            
            # Create memory object with conversation
            memory = {
                "conversation": self.memory_manager.get_conversation(self.session_id)
            }
            
            # Execute step with ReAct pattern
            start_time = time.time()
            step_result = self.executor.execute_step(step, context, memory)
            execution_time = time.time() - start_time
            
            print(f"Step completed in {execution_time:.2f} seconds")
            
            # Update conversation in Redis with any new messages added during execution
            for message in memory["conversation"]:
                # Skip messages already in the conversation
                existing_conversation = self.memory_manager.get_conversation(self.session_id)
                if message not in existing_conversation:
                    self.memory_manager.add_message(self.session_id, message)
            
            # Update context with completed step results
            context["completed_steps"].append({
                "step": i,
                "description": step["description"],
                "result": step_result
            })
            context["results"][f"step_{i}"] = step_result
            
            # Track progress
            print(f"Progress: {i}/{total_steps} steps completed")

            # Update context in state
            self.memory_manager.update_state(self.session_id, {"context": context})

            # Print conversation so far
            print("\n=== Conversation so far ===")
            print(json.dumps(self.memory_manager.get_conversation(self.session_id), indent=2))

            # Print context so far
            print("\n=== Context so far ===")
            print(json.dumps(context, indent=2))
        
        # Generate final response
        print("\n=== Generating Final Response ===")
        conversation = self.memory_manager.get_conversation(self.session_id)
        final_response = self.executor.generate_final_response(context, conversation)

        return final_response
    
    def get_session_id(self) -> str:
        """
        Get the current session ID.
        
        Returns:
            Session ID string
        """
        return self.session_id
    
    def load_session(self, session_id: str) -> bool:
        """
        Load an existing session.
        
        Args:
            session_id: The session ID to load
            
        Returns:
            Success flag
        """
        if self.memory_manager.get_session(session_id):
            self.session_id = session_id
            return True
        return False