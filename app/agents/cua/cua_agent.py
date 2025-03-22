import asyncio
import uuid

from app.agents.cua.computer import Computer
from utils import (
    create_response,
    pp,
    sanitize_message,
)
import json
from typing import Callable, Dict, List, Any, Optional
import datetime
from app.events.event_bus import get_message_queue, send_message, receive_message

class CuaAgent:
    """
    A sample agent class that can be used to interact with a computer.
    """

    def __init__(
        self,
        model="computer-use-preview",
        computer: Computer = None,
        tools: list[dict] = [],
        acknowledge_safety_check_callback: Callable = lambda: False,
        emit_event_async: Callable = None,
    ):
        self.model = model
        self.computer = computer
        self.tools = tools
        self.print_steps = True
        self.debug = False
        self.acknowledge_safety_check_callback = acknowledge_safety_check_callback
        self.emit_event_async = emit_event_async

        if computer:
            self.tools += [
                {
                    "type": "computer-preview",
                    "display_width": computer.dimensions[0],
                    "display_height": computer.dimensions[1],
                    "environment": "browser",
                },
            ]

    def debug_print(self, *args):
        if self.debug:
            pp(*args)

    async def handle_item(self, item):
        """Handle each item; may cause a computer action + screenshot."""

        # Normal message handling
        if item["type"] == "message":
            print("We got text message back, could be question")
            if self.print_steps:
                # check if item["content"][0]["text"] is a question
                if item["content"][0]["text"].endswith("?"):
                    question = item["content"][0]["text"]
                    
                    # Generate a unique ID for this clarification request
                    clarification_id = str(uuid.uuid4())
                    
                    # Create an event to notify the frontend about the clarification needed
                    if self.emit_event_async:
                        try:
                            # Emit the clarification request with the ID
                            clarification_data = {
                                "question": question,
                                "type": "cua_clarification",
                                "id": clarification_id
                            }

                            print(f"Emitting clarification: {clarification_data}")
                            
                            if asyncio.iscoroutinefunction(self.emit_event_async):
                                await self.emit_event_async("cua_clarification", clarification_data)
                            else:
                                self.emit_event_async("cua_clarification", clarification_data)
                            
                            # Create the queue before waiting for a response - don't await this
                            get_message_queue(clarification_id)
                            print(f"Waiting for clarification response for {clarification_id}")
                            user_clarification = await receive_message(clarification_id, timeout=300)
                            print(f"Received clarification response: {user_clarification}")
                            
                            if user_clarification:
                                return [{"role": "user", "content": user_clarification}]
                            else:
                                print("Clarification timed out after 5 minutes")
                                return [{"role": "user", "content": "User did not respond to clarification request. Please terminate the task."}]
                        except Exception as e:
                            print(f"Error waiting for clarification: {e}")
                        
                        # Fallback to terminal input if no emit_event_async is available
                        # user_clarification = input("\nQuestion: " + question + "\n")
                        # return [{"role": "user", "content": user_clarification}]

        # Process reasoning events to emit more detailed updates
        if item["type"] == "reasoning" and self.emit_event_async:
            # Extract the reasoning text from the event
            reasoning_text = ""
            summary = item.get("summary", [])
            for summary_item in summary:
                if summary_item.get("type") == "summary_text":
                    reasoning_text = summary_item.get("text", "")
            
            # Only emit if we have text
            if reasoning_text:
                # Try to extract action type from the reasoning text
                action_type = reasoning_text.split()[0].lower() if reasoning_text else ""
                
                # Prepare event data with more structured information
                reasoning_event_data = {
                    "text": reasoning_text,
                    "action": action_type,
                    "description": reasoning_text
                }
                
                # Extract more specific details based on action type
                if "click" in action_type or "clicking" in action_type:
                    reasoning_event_data["action"] = "clicking"
                    # Try to extract what's being clicked
                    if "on" in reasoning_text:
                        parts = reasoning_text.split("on", 1)
                        if len(parts) > 1:
                            reasoning_event_data["element"] = parts[1].strip().split(".")[0].strip()
                elif "type" in action_type or "typing" in action_type:
                    reasoning_event_data["action"] = "typing"
                    # Try to extract what's being typed
                    if '"' in reasoning_text:
                        parts = reasoning_text.split('"')
                        if len(parts) > 2:
                            reasoning_event_data["text"] = parts[1]
                elif "search" in action_type or "searching" in action_type:
                    reasoning_event_data["action"] = "searching"
                    if "for" in reasoning_text:
                        parts = reasoning_text.split("for", 1)
                        if len(parts) > 1:
                            reasoning_event_data["query"] = parts[1].strip().split(".")[0].strip()
                elif "scroll" in action_type or "scrolling" in action_type:
                    reasoning_event_data["action"] = "scrolling"
                    if "down" in reasoning_text.lower():
                        reasoning_event_data["direction"] = "down"
                    elif "up" in reasoning_text.lower():
                        reasoning_event_data["direction"] = "up"
                elif "navigat" in action_type:
                    reasoning_event_data["action"] = "navigating"
                    if "to" in reasoning_text:
                        parts = reasoning_text.split("to", 1)
                        if len(parts) > 1:
                            reasoning_event_data["url"] = parts[1].strip().split(".")[0].strip()
                
                # Emit the event with error handling
                try:
                    if asyncio.iscoroutinefunction(self.emit_event_async):
                        await self.emit_event_async("cua_reasoning", reasoning_event_data)
                    else:
                        self.emit_event_async("cua_reasoning", reasoning_event_data)
                except Exception as e:
                    print(f"Error emitting event: {e}")
                    # Optionally set a flag to stop trying to emit events
                    self.emit_event_async = None

        # TODO: function call handling

        if item["type"] == "computer_call":
            action = item["action"]
            action_type = action["type"]
            action_args = {k: v for k, v in action.items() if k != "type"}
            if self.print_steps:
                print(f"{action_type}({action_args})")

            method = getattr(self.computer, action_type)
            method(**action_args)

            print(f"Computer call {action_type} completed")

            screenshot_base64 = self.computer.screenshot()
            
            # Get browser stream URL is handled at initialization now
            print(f"Screenshot Taken")

            # if user doesn't ack all safety checks exit with error
            pending_checks = item.get("pending_safety_checks", [])
            for check in pending_checks:
                message = check["message"]
                if not self.acknowledge_safety_check_callback(message):
                    raise ValueError(
                        f"Safety check failed: {message}. Cannot continue with unacknowledged safety checks."
                    )
            
            print(f"Acknowledged safety checks: {pending_checks}")

            # Create standard output 
            call_output = {
                "type": "computer_call_output",
                "call_id": item["call_id"],
                "acknowledged_safety_checks": pending_checks,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}",
                },
            }

            # Return a simple list with the output
            return [call_output]
            
        return []  # Return an empty list

    async def run_full_turn(
        self, input_items, print_steps=True, debug=False
    ):
        self.print_steps = print_steps
        self.debug = debug

        new_items = []
        
        # Initialize monitoring state
        monitoring_state = self._initialize_monitoring_state(input_items)

        # keep looping until we get a final response
        while new_items[-1].get("role") != "assistant" if len(new_items) > 0 else True:
            self.debug_print([sanitize_message(msg) for msg in input_items + new_items])

            # For the API call, we only send the actual items
            response = create_response(
                model=self.model,
                input=input_items + new_items,
                tools=self.tools,
                truncation="auto",
                temperature=0,
                reasoning={
                    "generate_summary": "concise",
                }
            )
        
            self.debug_print(response)

            if "output" not in response and self.debug:
                print(response)
                raise ValueError("No output from model")
            else:
                # Concatenate new items (simple list concatenation)
                new_items = new_items + response["output"]
                for item in response["output"]:
                    # Process item and get any new items to add
                    result_items = await self.handle_item(item)
                    
                    # Update monitoring state and check for interventions
                    # intervention_items = await self._monitor_and_intervene(item, monitoring_state, input_items + new_items)
                    
                    # print(f"Intervention items: {intervention_items}")
                    
                    # if intervention_items:
                    #     result_items.extend(intervention_items)
                    
                    # Add new items to our list (simple list concatenation)
                    new_items = new_items + result_items
                    
        return new_items
    
    def _initialize_monitoring_state(self, input_items):
        """Initialize the monitoring state for tracking agent behavior."""
        original_task = input_items[0]["content"] if input_items and len(input_items) > 0 else ""
        
        return {
            "original_task": original_task,
            "steps_taken": 0,
            "websites_visited": set(),
            "current_website": None,
            "last_action_time": None,
            "scroll_count_per_page": {},
            "actions_history": [],
            "items_processed": 0,
            "last_intervention_item": 0,
            "interventions_made": 0,
            "extracted_info": [],
        }
    
    async def _monitor_and_intervene(self, item, monitoring_state, current_conversation):
        """
        Monitor agent behavior and intervene if necessary using a monitoring LLM.
        
        Args:
            item: The current item being processed
            monitoring_state: The current monitoring state
            current_conversation: The current conversation history
            
        Returns:
            List of intervention items to add, if any
        """
        # Update monitoring state based on the item
        if item["type"] == "computer_call":
            action = item["action"]
            action_type = action["type"]
            
            # Create a record of this action
            action_record = {
                "type": action_type,
                "args": {k: v for k, v in action.items() if k != "type"},
                "timestamp": datetime.datetime.now().isoformat()
            }
            monitoring_state["actions_history"].append(action_record)
            
            # Track navigation
            if action_type == "navigate":
                url = action.get("url", "")
                monitoring_state["current_website"] = url
                monitoring_state["websites_visited"].add(url)
                monitoring_state["last_action_time"] = datetime.datetime.now()
                
                # Initialize scroll count for this page
                if url not in monitoring_state["scroll_count_per_page"]:
                    monitoring_state["scroll_count_per_page"][url] = 0
            
            # Track scrolling
            elif action_type == "scroll":
                current_site = monitoring_state["current_website"]
                if current_site:
                    monitoring_state["scroll_count_per_page"][current_site] = monitoring_state["scroll_count_per_page"].get(current_site, 0) + 1
                monitoring_state["last_action_time"] = datetime.datetime.now()
            
            monitoring_state["steps_taken"] += 1
        
        # Track reasoning and information extraction
        if item["type"] == "reasoning":
            summary = item.get("summary", [])
            for summary_item in summary:
                if summary_item.get("type") == "summary_text":
                    text = summary_item.get("text", "")
                    # Check if this reasoning step contains extracted information
                    if any(marker in text.lower() for marker in ["found:", "results:", "information:", "data:", "list:"]):
                        monitoring_state["extracted_info"].append(text)
        
        # Check if the agent is providing a final response
        if item.get("role") == "assistant" and isinstance(item.get("content"), (str, list)):
            # Record the response for analysis
            content = item["content"]
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict) and "text" in content[0]:
                monitoring_state["last_response"] = content[0]["text"]
            else:
                monitoring_state["last_response"] = str(content)
        
        # Increment the items processed counter
        monitoring_state["items_processed"] = monitoring_state.get("items_processed", 0) + 1
        
        # Check for interventions every N items
        items_between_interventions = 2  # Intervene after every 2 new items
        max_interventions = 5  # Limit total interventions to avoid excessive guidance
        
        if (monitoring_state["items_processed"] - monitoring_state.get("last_intervention_item", 0) >= items_between_interventions and 
            monitoring_state.get("interventions_made", 0) < max_interventions):
            
            intervention = await self._get_monitoring_llm_guidance(monitoring_state, current_conversation)
            if intervention:
                monitoring_state["last_intervention_item"] = monitoring_state["items_processed"]
                monitoring_state["interventions_made"] = monitoring_state.get("interventions_made", 0) + 1
                
                # Create intervention item
                intervention_item = {"role": "user", "content": intervention}
                
                # Log the intervention for debugging purposes
                if self.debug:
                    print(f"Monitoring LLM intervention: {intervention}")
                
                return [intervention_item]
        
        return []
    
    async def _get_monitoring_llm_guidance(self, state, current_conversation):
        """
        Use a monitoring LLM to analyze the agent's behavior and provide guidance.
        
        Args:
            state: The current monitoring state
            current_conversation: The current conversation history
            
        Returns:
            An intervention message if needed, or None
        """
        try:
            # Extract the original task
            original_task = state["original_task"]
            
            # Get the most recent messages for context (limit to last 5 for brevity)
            recent_messages = []
            for item in reversed(current_conversation):
                if len(recent_messages) >= 5:
                    break
                if item.get("role") in ["user", "assistant"]:
                    content = item.get("content", "")
                    if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                        content = content[0].get("text", "")
                    recent_messages.insert(0, f"{item.get('role', 'unknown')}: {content}")
            
            # Format the action history for analysis
            action_history = []
            for action in state["actions_history"][-10:]:  # Last 10 actions
                action_str = f"{action['type']}"
                if action['type'] == 'navigate':
                    action_str += f" to {action['args'].get('url', 'unknown')}"
                elif action['type'] == 'click':
                    action_str += f" at ({action['args'].get('x', '?')}, {action['args'].get('y', '?')})"
                elif action['type'] == 'type':
                    action_str += f" '{action['args'].get('text', '')}'"
                action_history.append(action_str)
            
            # Create a prompt for the monitoring LLM
            monitoring_prompt = f"""
            You are a monitoring system for a web browsing agent. The agent is working on this task:
            
            {original_task}
            
            The agent's current state:
            - Steps taken: {state["steps_taken"]}
            - Websites visited: {', '.join(state["websites_visited"])}
            - Current website: {state["current_website"]}
            - Scroll counts per page: {json.dumps(state["scroll_count_per_page"])}
            
            Recent actions:
            {json.dumps(action_history, indent=2)}
            
            Recent conversation:
            {json.dumps(recent_messages, indent=2)}
            
            Extracted information so far:
            {json.dumps(state["extracted_info"], indent=2)}
            
            Your job is to analyze the agent's behavior and determine if intervention is needed.
            Consider:
            1. Is the agent making progress toward completing the task?
            2. Is the agent getting distracted or going off-track?
            3. Is the agent spending too much time on one website without extracting information?
            4. Is the agent switching between too many websites without thorough exploration?
            5. Is the agent failing to extract and document information?
            6. Is the agent close to completing the task but missing a summary?
            
            If intervention is needed, provide a concise, helpful message to guide the agent.
            If no intervention is needed, respond with "NO_INTERVENTION".
            """
            
            # Call a monitoring LLM (using a different model than the agent)
            # Use a smaller, faster model for monitoring to reduce latency
            monitoring_model = "o3-mini"  # Adjust based on available models
            
            response = create_response(
                model=monitoring_model,
                input=[{"role": "user", "content": monitoring_prompt}]
            )
            
            print(f"Monitoring LLM response: {response}")
            
            if "output" in response:
                # Extract the actual guidance text from the response
                for output_item in response["output"]:
                    if output_item.get("type") == "message" and output_item.get("role") == "assistant":
                        content = output_item.get("content", [])
                        if content and isinstance(content, list):
                            for content_item in content:
                                if content_item.get("type") == "output_text":
                                    guidance_text = content_item.get("text", "")
                                    if guidance_text and "NO_INTERVENTION" not in guidance_text:
                                        return f"GUIDANCE: {guidance_text}"
            
            return None
            
        except Exception as e:
            print(f"Error in monitoring LLM: {e}")
            return None