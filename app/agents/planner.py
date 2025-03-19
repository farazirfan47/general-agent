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
    
    def create_plan(self, user_query: str) -> Dict:
        """
        Analyze the user query and create a structured plan.
        Ask clarifying questions if needed.
        
        Args:
            user_query: The user's original request
            
        Returns:
            Dict containing the plan or clarifying questions
        """
        # Define planner instructions
        planner_instructions = f"""
        You are a strategic planner for an agent system with web search and browser interaction capabilities. Your task is to:

        1. Analyze user queries to determine the most efficient approach.
        2. For simple factual queries, prefer direct single-step plans using web search.
        3. Only create multi-step plans when the task genuinely requires sequential actions.
        4. Only ask clarifying questions for critical information that cannot be inferred or searched.

        PLAN EFFICIENCY GUIDELINES:
        - For simple information queries (e.g., "What is the weather in Boston?", "When is YC's deadline?"), use a single search step.
        - For tasks requiring website interaction (form filling, navigation through multiple pages), create minimal necessary steps.
        - Avoid breaking down obvious sub-steps (e.g., don't list "scroll down" or "click search button" as separate steps).

        Return your analysis in the following JSON format:
        {{
            "clarification_needed": true/false, 
            "clarifying_questions": ["question1", "question2"],  // only if clarification_needed is true
            "plan": [
                {{"step": 1, "description": "..."}}
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
                input=user_query,
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

            for message in response.output:
                if message.type == "message":
                    plan_text = message.content[0].text
                    plan_data = json.loads(plan_text)
                    return plan_data
            else:
                print("No response from planner")
            
        except Exception as e:
            print(f"Error in planner: {e}")
            raise e
            # Return fallback plan in case of error
            # fallback_plan = {
            #     "clarification_needed": False,
            #     "plan": [
            #         {"step": 1, "description": "Understand user query"},
            #         {"step": 2, "description": "Execute the query", "tools": ["web_search"]},
            #         {"step": 3, "description": "Summarize results", "tools": []}
            #     ]
            # }
            # return fallback_plan
    
    def handle_clarification(self, original_query: str, plan_data: Dict, user_clarification: str) -> Dict:
        """
        Re-plan after receiving user clarification.
        
        Args:
            original_query: The original user request
            plan_data: The previous plan data with clarification questions
            user_clarification: The user's clarification response
            
        Returns:
            Updated plan Dict
        """
        # Create an enhanced query with the clarification
        enhanced_query = f"""
        Original query: {original_query}
        
        Clarifying questions asked:
        {json.dumps(plan_data.get('clarifying_questions', []), indent=2)}
        
        User clarification:
        {user_clarification}
        """
        
        # Create a new plan with the clarification
        return self.create_plan(enhanced_query)