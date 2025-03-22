import os
import json
import time
import asyncio
import openai
from openai import AsyncOpenAI
from typing import Dict, List, Any, Optional, Callable
import datetime
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
                self.session_id = self.memory_manager.create_session(session_id)
        else:
            print("[AgentLoop] No session ID provided, creating a new one")
            print(f"This should not happen, session_id: {session_id}")
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
        
        # Get conversation history for context
        conversation = self.memory_manager.get_conversation(self.session_id)
        
        # Analyze query complexity to determine the appropriate approach
        complexity_result = await self._analyze_query_complexity(user_query, conversation)
        
        # If query is simple or a follow-up that doesn't need planning, handle directly
        if complexity_result["use_direct_response"]:
            direct_response = await self._generate_direct_response(user_query, conversation)
            self.memory_manager.add_assistant_message(self.session_id, direct_response)
            await emit_event_async("complete", {"message": direct_response})
            return direct_response
        
        # For complex queries, use the full planning and execution workflow
        await emit_event_async("thinking", {"message": "Creating plan..."})

        print("Conversations before plan: ", conversation)

        # Pass the complexity result to the planner to use the appropriate model
        plan_data = self.planner.create_plan(conversation, model=complexity_result["recommended_model"])
        
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
                emit_event_async,
                session_id=self.session_id
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

    async def _analyze_query_complexity(self, query: str, conversation: List[Dict]) -> Dict:
        """
        Analyzes the complexity of a query to determine the appropriate processing approach.
        
        Args:
            query: The user's query
            conversation: The conversation history
            
        Returns:
            Dict with complexity assessment and recommended approach
        """
        print("\n=== Query Complexity Analysis ===")
        print(f"Analyzing query: '{query}'")
        
        # Check if this is a follow-up question
        is_followup = len(conversation) > 2
        print(f"Is follow-up question: {is_followup}")
        
        # Simple heuristics for query complexity
        query_length = len(query.split())
        contains_complex_keywords = any(keyword in query.lower() for keyword in 
                                       ["compare", "analyze", "research", "find", "search", 
                                        "steps", "how to", "procedure", "workflow"])
        
        print(f"Query length (words): {query_length}")
        print(f"Contains complex keywords: {contains_complex_keywords}")
        
        # More sophisticated analysis using a lightweight model
        try:
            print("Performing detailed complexity analysis with GPT-4o...")
            response = openai.responses.create(
                model="gpt-4o",  # Using a faster model for this analysis
                input=query,
                instructions="""
                Analyze this query and determine:
                1. Complexity (1-10 scale)
                2. Whether it requires multi-step planning
                3. Whether it requires web search or browsing
                4. If it's a simple factual question or follow-up
                
                Return a JSON with these assessments.
                """,
                text={"format": {"type": "json_schema", "name": "query_analysis", "schema": {
                    "type": "object",
                    "properties": {
                        "complexity_score": {"type": "number"},
                        "requires_planning": {"type": "boolean"},
                        "requires_web_tools": {"type": "boolean"},
                        "is_simple_factual": {"type": "boolean"}
                    },
                    "required": ["complexity_score", "requires_planning", "requires_web_tools", "is_simple_factual"],
                    "additionalProperties": False
                }}}
            )
            
            analysis = json.loads(response.output_text)
            print(f"Analysis result: {json.dumps(analysis, indent=2)}")
            
            # Determine the best approach based on the analysis
            use_direct_response = (
                analysis["complexity_score"] < 4 or 
                (is_followup and not analysis["requires_web_tools"]) or
                analysis["is_simple_factual"]
            )
            
            # Choose the appropriate model based on complexity
            if analysis["complexity_score"] >= 7:
                recommended_model = "o1"  # Most powerful reasoning model
            elif analysis["complexity_score"] >= 4:
                recommended_model = "o3-mini"  # Medium reasoning model
            else:
                recommended_model = "gpt-4o"  # Fast model for simple queries
                
            print(f"Decision: Use direct response: {use_direct_response}")
            print(f"Recommended model: {recommended_model}")
            
            result = {
                "complexity_score": analysis["complexity_score"],
                "use_direct_response": use_direct_response,
                "requires_planning": analysis["requires_planning"],
                "recommended_model": recommended_model
            }
            print(f"Final complexity assessment: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            print(f"Error in complexity analysis: {e}")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception details: {str(e)}")
            print("Falling back to simple heuristics...")
            
            # Fallback to simple heuristics if the model call fails
            complexity_score = min(query_length / 10, 10)  # Simple length-based score
            if contains_complex_keywords:
                complexity_score += 2
            
            print(f"Fallback complexity score: {complexity_score}")
            
            use_direct_response = complexity_score < 5 and not contains_complex_keywords
            
            result = {
                "complexity_score": complexity_score,
                "use_direct_response": use_direct_response,
                "requires_planning": complexity_score >= 5 or contains_complex_keywords,
                "recommended_model": "o3-mini"  # Default to o3-mini as a safe choice
            }
            
            print(f"Fallback assessment: {json.dumps(result, indent=2)}")
            return result

    async def _generate_direct_response(self, query: str, conversation: List[Dict]) -> str:
        """
        Generate a direct response for simple queries without going through the planning process.
        Includes web search capability for factual questions.
        
        Args:
            query: The user's query
            conversation: The conversation history
            
        Returns:
            Direct response text
        """
        try:
            print("Initializing AsyncOpenAI client for direct response...")
            # Initialize async client
            async_client = AsyncOpenAI()
            
            # Create instructions for direct response
            direct_response_instructions = """
            You are a helpful assistant. Provide a direct, concise response to the user's query.
            Use the web search tool when you need to find current information or verify facts.
            Respond conversationally and cite sources when you use search results.
            
            Focus on answering the user's question efficiently without unnecessary steps.
            """
            
            print("Sending request to GPT-4o with web search capability...")
            # Execute the direct response with web search capability
            response = await async_client.responses.create(
                model="gpt-4o",  # Using a faster model for direct responses
                input=conversation,
                instructions=direct_response_instructions,
                tools=[{ "type": "web_search_preview" }],
                temperature=0
            )
            
            # Process the response similar to executor.py
            result = ""
            function_call = False
            
            for message in response.output:
                if message.type == "function_call":
                    function_call = True
                    print("Function call detected in direct response")
                    break
            
            if not function_call:
                # If no function calls, just get the text response
                print("No function calls, using direct text response")
                result = response.output_text
            else:
                # Handle any web search calls that might have happened
                for message in response.output:
                    if message.type == "web_search_call":
                        print(f"Web search executed in direct response")
                        # The model has already processed the search results
                        result = response.output_text
                    else:
                        result = response.output_text
            
            print(f"Direct response generated successfully (length: {len(result)})")
            return result
            
        except Exception as e:
            print(f"Error generating direct response: {e}")
            print(f"Exception type: {type(e).__name__}")
            print(f"Exception details: {str(e)}")
            return "I'm sorry, I encountered an error while processing your request. Could you please try again?"