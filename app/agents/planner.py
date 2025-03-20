import os
import json
import time
from typing import Dict, List, Any, Optional
import openai
import datetime

class PlannerAgent:
    """
    Planner Agent powered by OpenAI o1 model.
    Responsible for analyzing user queries and creating actionable plans.
    """
    def __init__(self):
        self.model = "gpt-4o"
    
    def create_plan(self, conversation) -> Dict:
        """
        Analyze the user query and create a structured plan.
        Ask clarifying questions if needed.
        
        Args:
            conversation: The full conversation history
            
        Returns:
            Dict containing the plan or clarifying questions
        """
        # Define planner instructions
        planner_instructions = f"""
        You are a strategic planner for an agent system with web search and browser interaction capabilities. Your task is to create efficient execution plans for user requests.

        # AVAILABLE TOOLS
        1. Web Search Tool - Use for: Finding current information, researching topics, locating resources
        2. Browser Tool (computer_use) - Use for: Performing tasks in a browser environment, interacting with websites

        # PLANNING GUIDELINES
        1. Analyze user queries to determine the most efficient approach.
        2. For simple factual queries, prefer direct single-step plans using web search.
        3. Only create multi-step plans when the task genuinely requires sequential actions.
        4. Only ask clarifying questions for critical information that cannot be inferred or searched.

        # TOOL-SPECIFIC PLANNING RULES
        ## For Web Search Tool:
        - Use for information gathering steps
        - Can be used as standalone steps

        ## For computer_use Tool:
        - IMPORTANT: Always define COMPLETE TASKS in a SINGLE STEP
        - BAD EXAMPLE: Step 1: "Visit Google", Step 2: "Search for information" 
        - GOOD EXAMPLE: Step 1: "Use browser to navigate to Google and search for XYZ information"
        - Include all necessary context and sub-actions within one comprehensive step
        - Specify the full sequence of actions needed to achieve a coherent goal in one step

        # PLAN EFFICIENCY GUIDELINES
        - For simple information queries (e.g., "What is the weather in Boston?"), use a single search step.
        - For tasks requiring website interaction, create minimal necessary steps with comprehensive descriptions.
        - Combine logical sequences of actions within the same tool into a single step.
        - Each step should represent a distinct phase of the task that produces a meaningful outcome.

        Return your analysis in the following JSON format:
        {{
            "clarification_needed": true/false, 
            "clarifying_questions": ["question1", "question2"],  // only if clarification_needed is true
            "plan": [
                {{
                    "step": 1, 
                    "tool": "web_search or computer_use",
                    "description": "Complete description of the step..."
                }}
                // Add more steps only if genuinely different actions are required
            ]
        }}

        Today is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """     
        # Log the planning attempt
        # print(f"Creating plan for query: {user_query}")
        
        try:
            # Create response with o1 model for planning
            response = openai.responses.create(
                model=self.model,
                input=conversation,
                instructions=planner_instructions,
                text={"format": {"type": "json_schema", "name": "plan", "schema": {
                    "type": "object",
                    "properties": {
                        "clarification_needed": {"type": "boolean"},
                        "clarifying_questions": {"type": "array", "items": {"type": "string"}},
                        "plan": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step": {"type": "number"},
                                    "description": {"type": "string"}
                                },
                                "required": ["step", "description"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["clarification_needed", "plan", "clarifying_questions"],
                    "additionalProperties": False
                },
                "strict": True
                }}
            )

            # Extract just the plan data
            plan_data = json.loads(response.output[0].content[0].text)
            return plan_data
            
        except Exception as e:
            print(f"Error in planner: {e}")
            raise e