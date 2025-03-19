import os
import json
import time
from typing import Dict, List, Any, Optional
import openai
from app.agents.planner import PlannerAgent
from app.agents.executor import ExecutorAgent

class AgentLoop:
    """
    Orchestrates the workflow between Planner and Executor agents.
    Manages the end-to-end process from user query to final response.
    """
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.memory = {
            "state": {},
            "conversation": []
        }
    
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
        
        # Store the original query
        self.memory["state"]["original_query"] = user_query
        self.memory["conversation"].append({
            "role": "user", 
            "content": user_query
        })
        
        # Get plan from the Planner
        plan_data = self.planner.create_plan(user_query)
        
        # Check if clarification is needed
        while plan_data.get("clarification_needed", False):
            clarifying_questions = plan_data.get("clarifying_questions", [])
            
            print("\n=== Clarification Needed ===")
            for i, question in enumerate(clarifying_questions, 1):
                print(f"{i}. {question}")
            
            user_clarification = input("\nPlease provide clarifications: ")
            
            # Store the clarification
            self.memory["conversation"].append({
                "role": "assistant", 
                "content": "I need some clarification: " + " ".join(clarifying_questions)
            })
            self.memory["conversation"].append({
                "role": "user", 
                "content": user_clarification
            })
            
            # Update the plan with clarification
            plan_data = self.planner.handle_clarification(
                user_query, 
                plan_data, 
                user_clarification
            )
        
        # Extract the plan steps
        plan = plan_data.get("plan", [])
        
        if not plan:
            print(plan_data)
            return "Failed to create a plan. Please try again with a more specific query."
        
        print("\n=== Plan Created ===")
        print(json.dumps(plan, indent=2))

        # Store the plan
        self.memory["state"]["plan"] = plan
        
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
        
        # Initialize execution context
        context = {
            "plan": plan,
            "original_query": self.memory["state"]["original_query"],
            "completed_steps": [],
            "current_step": 0
        }
        
        # Execute each step in sequence
        total_steps = len(plan)
        for i, step in enumerate(plan, 1):
            print(f"\n--- Step {i}/{total_steps}: {step['description']} ---")
            
            # Update context for current step
            context["current_step"] = i
            
            # Execute step with ReAct pattern
            start_time = time.time()
            step_result = self.executor.execute_step(step, context, self.memory)
            execution_time = time.time() - start_time
            
            print(f"Step completed in {execution_time:.2f} seconds")
            
            # Store the step result
            self.memory["conversation"].append({
                "role": "assistant", 
                "content": step_result
            })
            # Update context with completed step results
            context["completed_steps"].append({
                "step": i,
                "description": step["description"]
            })
            
            # Track progress
            print(f"Progress: {i}/{total_steps} steps completed")
        
        # Generate final response
        print("\n=== Generating Final Response ===")
        final_response = self.executor.generate_final_response(context, self.memory)
        
        # Store the final response
        self.memory["conversation"].append({
            "role": "assistant", 
            "content": final_response
        })
        
        return final_response