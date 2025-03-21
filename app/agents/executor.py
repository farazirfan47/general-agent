import os
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Callable
from openai import OpenAI, AsyncOpenAI
from tools.cua_tool import cua_tool
from tool_handling import handle_cua_request

class ExecutorAgent:
    """
    Executor Agent powered by OpenAI GPT-4o model.
    Responsible for executing individual steps of a plan.
    """
    def __init__(self):
        self.model = "gpt-4o"
        self.client = OpenAI()
        self.async_client = AsyncOpenAI()
        # Track active CUA agents
        self.active_cua_agents = []
        
    def execute_step(self, step: Dict, context: Dict, memory: Dict, emit_event_async: Optional[Callable] = None) -> Dict:
        """
        Synchronous wrapper around execute_step_async
        
        Args:
            step: The current step to execute
            context: The current execution context including previous steps
            memory: The memory state from previous steps
            emit_event_async: Function to emit socket events directly
            
        Returns:
            Dict containing the step execution result
        """
        return asyncio.run(self.execute_step_async(step, context, memory, emit_event_async))
    
    async def execute_step_async(self, step: Dict, context: Dict, memory: Dict, emit_event_async: Optional[Callable] = None) -> Dict:
        """
        Execute a single step of the plan using the ReAct pattern
        
        Args:
            step: The current step to execute
            context: The current execution context including previous steps
            memory: The memory state from previous steps
            emit_event_async: Function to emit socket events directly
            
        Returns:
            Dict containing the step execution result
        """
        
        # Prepare executor instructions using ReAct pattern
        executor_instructions = f"""
        # EXECUTION CONTEXT
        ## Plan Context
        {json.dumps(context, indent=2)}

        ## Current Step to Execute
        {json.dumps(step, indent=2)}

        # AVAILABLE TOOLS
        1. Web Search Tool - Use for: Finding current information, researching topics, locating resources
        2. Browser Tool (computer_use) - Use for: Performing tasks in a browser environment, interacting with websites

        # GUIDELINES FOR TOOL USAGE
        ## When using computer_use tool:
        - Provide comprehensive task descriptions that can stand alone
        - Include relevant context from the conversation
        - Clearly define the specific goal and expected outcome
        - Specify exactly what should be done and any constraints
        - Remember that the executing agent has no access to previous conversation

        # OUTPUT FORMAT
        Please execute this step using the appropriate tools. When you're done, provide a summary of what you accomplished.
        """
        
        try:            
            # Initialize step result
            result = ""
            # Execute the step asynchronously
            response = await self.async_client.responses.create(
                model=self.model,
                input=memory["conversation"],
                instructions=executor_instructions,
                tools=[{ "type": "web_search_preview" }, cua_tool],
                temperature=0
            )

            # check if we have a function call in the response via loop
            function_call = False
            for message in response.output:
                if message.type == "function_call":
                    function_call = True
                    break
            
            if function_call == False:
                memory["conversation"].append(response.output)
            else:
                # loop through the response.output and convert class object to a dictionary and then create a full list and add it to the conversation
                for message in response.output:
                    message = message.__dict__
                    memory["conversation"].append(message)

            for message in response.output:
                if message.type == "function_call":
                    tool_name = message.name
                    args = json.loads(message.arguments)
                    
                    # Emit tool usage event directly
                    if emit_event_async:
                        await emit_event_async("tool_usage", {"tool": tool_name, "args": args})
                    
                    if tool_name == "computer_use":
                        print(f"Executing CUA request: {args['task']}")
                        
                        # Emit computer use specific event with task info
                        if emit_event_async:
                            # Create event data with the task
                            cua_event_data = {"task": args.get("task", "")}
                            # Emit the event
                            await emit_event_async("cua_event", cua_event_data)
                        
                        # Handle CUA request by passing the event emitter directly to handle_cua_request
                        # Also pass self to register the CUA agent
                        tool_response = await handle_cua_request(args["task"], emit_event_async)

                        print("Successfully executed CUA request, Outside the function")
                        
                        # Add the response to the conversation
                        callback_message = self.create_function_call_result_message(tool_response, message.call_id)
                        memory["conversation"].append(callback_message)
                        result = tool_response
                        
                        # Recursive call to execute_step_async to continue processing
                        # return await self.execute_step_async(step, context, memory, emit_event_async)
                elif message.type == "web_search_call":
                    print(f"Executing web search")
                    result = response.output_text
                else:
                    result = response.output_text

            return result
            
        except Exception as e:
            error_msg = f"Error executing step: {e}"
            print(error_msg)
            raise e
            
    def create_function_call_result_message(self, api_response, tool_call_id):
        function_call_result_message = {
            "type": "function_call_output",
            "output": json.dumps(api_response),
            "call_id": tool_call_id
        }
        return function_call_result_message
    
    async def generate_final_response_async(self, context: Dict, conversation: List[Dict]) -> str:
        
        final_instructions = """
        You are generating a final, comprehensive response to the user based on all completed steps.
        Synthesize the results from all steps into a coherent, well-structured response.
        
        Make sure your response:
        1. Directly addresses the original user query
        2. Summarizes key findings or results
        3. Presents information in a clear, well-organized way
        4. Includes relevant specific details from the step results
        5. Avoids repeating unnecessary execution details or reasoning steps
        
        Return your response in markdown format.
        """
        
        try:
            # Create response with GPT-4o for final summary asynchronously
            response = await self.async_client.responses.create(
                model=self.model,
                input=conversation,
                instructions=final_instructions,
                temperature=0
            )
            
            # Extract the text response
            final_result = response.output[0].content[0].text
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error generating final response: {e}"
            print(error_msg)
            return f"Failed to generate final response: {str(e)}"