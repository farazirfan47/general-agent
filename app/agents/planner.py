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
        self.model = "o1"
    
    def create_plan(self, conversation) -> Dict:
        """
        Analyze the user query and create a structured plan.
        Ask clarifying questions if needed.
        
        Args:
            conversation: The full conversation history
            
        Returns:
            Dict containing the plan or clarifying questions
        """
        planner_instructions = f"""

        You are an expert Planning Agent that breaks down problems into clear, sequential steps, considering that each step runs in a new browser instance.

        # AVAILABLE TOOLS
        1. Web Search Tool - For finding current information, researching topics, locating resources
        2. Browser Tool - For performing tasks in a browser environment, interacting with websites

        # PLANNING GUIDELINES
        1. Break tasks into appropriate steps based on complexity - more for complex tasks, fewer for simple ones.
        2. Each step should accomplish ONE specific objective with clear outputs.
        3. IMPORTANT: Each step runs in a NEW browser instance with NO access to previous browser state.
        4. Each step must be completely self-contained with all necessary information.
        5. In step descriptions, include ALL information needed to execute that step independently.
        6. Explicitly state what information should be collected and passed to subsequent steps.
        7. For simple factual queries, use a single-step plan with web search.
        8. Ensure steps follow a logical progression where later steps incorporate outputs from earlier steps.

        # BROWSER CONTEXT HANDLING
        1. Always include relevant URLs, search terms, and navigation paths in each step description.
        2. Specify exactly what information to extract and how it should be formatted for the next step.
        3. When a step depends on previous results, clearly state what those dependencies are.
        4. Never assume information from a previous browser session will be available.

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

            print("Planner response: ", response.output_text)

            # Extract just the plan data
            plan_data = json.loads(response.output_text)
            return plan_data
            
        except Exception as e:
            print(f"Error in planner: {e}")
            raise e