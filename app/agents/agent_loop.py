import os
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent
from app.memory.redis_memory import RedisMemory
from app.events.event_bus import emit_event_async

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
        Synchronous wrapper around run_async
        
        Args:
            user_query: The user's query or request
            
        Returns:
            Final response text
        """
        # Use asyncio.run to run the async method in a sync context
        return asyncio.run(self.run_async(user_query, interactive_clarification=True))
    
    async def run_async(self, user_query: str, interactive_clarification: bool = False) -> str:
        """
        Process a user query through the complete agent workflow
        
        Args:
            user_query: The user's query or request
            interactive_clarification: If True, handle clarifications interactively, otherwise return early
            
        Returns:
            Final response text or "Clarification needed" if clarification is required in non-interactive mode
        """
        print("\n=== Starting New Query ===")
        print(f"User Query: {user_query}")
        print(f"Session ID: {self.session_id}")
        
        # Store the original query in state and add to conversation
        self.memory_manager.update_state(self.session_id, {"original_query": user_query})
        self.memory_manager.add_user_message(self.session_id, user_query)
        
        # await emit_event_async("thinking", {"message": "Processing your request..."})
        
        # Get conversation history for context
        conversation = self.memory_manager.get_conversation(self.session_id)
        
        # Get plan from the Planner
        await emit_event_async("thinking", {"message": "Creating plan..."})

        print("Conversations before plan: ", conversation)

        plan_data = self.planner.create_plan(conversation)
        
        # Check if clarification is needed
        if plan_data.get("clarification_needed", False):
            clarifying_questions = plan_data.get("clarifying_questions", [])
            
            # Create a proper message for the clarification
            assistant_message = "I need some clarification: " + " ".join(clarifying_questions)
            
            # Store the assistant message asking for clarification
            self.memory_manager.add_assistant_message(self.session_id, assistant_message)
            
            # If in interactive terminal mode, get input directly
            if interactive_clarification:
                # Interactive clarification mode (for terminal use)
                print("\n=== Clarification Needed ===")
                for i, question in enumerate(clarifying_questions, 1):
                    print(f"{i}. {question}")
                
                user_clarification = input("\nPlease provide clarifications: ")
                
                # Store the clarification
                self.memory_manager.add_user_message(self.session_id, user_clarification)
                
                # Refresh conversation history
                conversation = self.memory_manager.get_conversation(self.session_id)
                
                # Update the plan with clarification
                plan_data = self.planner.create_plan(conversation)
                
                # Check if further clarification is needed (recursive case)
                if plan_data.get("clarification_needed", False):
                    # Recursively call run_async with the same interactive_clarification setting
                    return await self.run_async(user_clarification, interactive_clarification)
            else:
                # For web-based flows, return a special response indicating clarification is needed
                # The frontend will handle displaying the questions and getting user input
                # The next message from the user will be treated as the clarification
                return {
                    "type": "clarification_needed",
                    "questions": clarifying_questions,
                    "message": assistant_message
                }
        
        # Extract the plan steps
        plan = plan_data.get("plan", [])

        print("Plan: ", plan)
        
        if not plan:
            return "Failed to create a plan. Please try again with a more specific query."
        
        await emit_event_async("plan", {"plan": plan})
        
        # Store the plan in state
        self.memory_manager.update_state(self.session_id, {"plan": plan})
        
        # Execute the plan
        return await self._execute_plan_async(plan)
    
    def _execute_plan(self, plan: List[Dict]) -> str:
        """
        Synchronous wrapper around _execute_plan_async
        
        Args:
            plan: List of plan steps to execute
            
        Returns:
            Final response text
        """
        # Use asyncio.run to run the async method in a sync context
        return asyncio.run(self._execute_plan_async(plan))
    
    async def _execute_plan_async(self, plan: List[Dict]) -> str:
        """
        Execute each step of the plan and generate final response
        
        Args:
            plan: List of plan steps to execute
            
        Returns:
            Final response text
        """
        await emit_event_async("executing", {"message": "Executing plan..."})
        
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
            await emit_event_async("step", {
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
            
            # Pass the event emitter directly to the executor agent
            await emit_event_async("executing_step", {"step": i, "description": step_description})
            
            # Execute step with executor agent asynchronously
            start_time = time.time()
            # Pass the emit_event_async method directly to executor
            step_result = await self.executor.execute_step_async(
                step, 
                context, 
                memory, 
                emit_event_async
            )
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
                "description": step_description,
                "result": step_result
            })
            context["results"][f"step_{i}"] = step_result
            
            # Update context in state
            self.memory_manager.update_state(self.session_id, {"context": context})
        
        # Generate final response
        print("Generating final response...")
        await emit_event_async("finalizing", {"message": "Generating final response..."})
        
        conversation = self.memory_manager.get_conversation(self.session_id)
        final_response = await self.executor.generate_final_response_async(context, conversation)

        print("Final response: ", final_response)
        
        # Add final response to conversation
        self.memory_manager.add_assistant_message(self.session_id, final_response)
        
        # Emit a completion event to signal the frontend that processing is done
        await emit_event_async("complete", {"message": final_response})

        print("Final response emitted")
        return final_response