import os
import json
import time
from typing import Dict, List, Any, Optional
from openai import OpenAI
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
        
    def execute_step(self, step: Dict, context: Dict, memory: Dict) -> Dict:
        """
        Execute a single step of the plan using the ReAct pattern
        
        Args:
            step: The current step to execute
            context: The current execution context including previous steps
            memory: The memory state from previous steps
            
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
            # Execute the step
            response = self.client.responses.create(
                model=self.model,
                input=memory["conversation"],
                instructions=executor_instructions,
                tools=[{ "type": "web_search_preview" }, cua_tool],
                temperature=0
            )

            memory["conversation"].append(response.output)

            # print("Response:")
            # print(response.output_text)
            # for message in response.output:
            #     if message.type == "function_call":
            #         memory["conversation"].append({   
            #             "role": "assistant",
            #             "content": response.output_text
            #         })
            #         break

            for message in response.output:
                if message.type == "function_call":
                    tool_call_name = message.name
                    args = json.loads(message.arguments)
                    if tool_call_name == "computer_use":
                        print(f"Executing CUA request: {args['task']}")
                        tool_response = handle_cua_request(args["task"])
                        callback_message = self.create_function_call_result_message(tool_response, message.id)
                        memory["conversation"].append(callback_message)
                        print("Before recursive call to execute_step")
                        # print(memory["conversation"])
                        # Recursive call to execute_step
                        print("Recursive call to execute_step")
                        return self.execute_step(step, context, memory)
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
            "role": "tool",
            "content": json.dumps(api_response),
            "tool_call_id": tool_call_id
        }
        return function_call_result_message


    def generate_final_response(self, context: Dict, conversation: List[Dict]) -> str:
        """
        Generate a final comprehensive response based on all step results
        
        Args:
            context: The execution context with all completed steps
            memory: The memory state from all previous steps
            
        Returns:
            Final response text
        """
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
            # Create response with GPT-4o for final summary
            response = self.client.responses.create(
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