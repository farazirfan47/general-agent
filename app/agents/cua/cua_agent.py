import asyncio

from app.agents.cua.computer import Computer
from utils import (
    create_response,
    pp,
    sanitize_message,
)
import json
from typing import Callable, Dict, List, Any, Optional
import datetime

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
                    # user_clarification = input("\nQuestion: " + item["content"][0]["text"] + "\n")
                    # return [{"role": "user", "content": user_clarification}]
                    print(f"Question: {item['content'][0]['text']}")

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
        
        system_prompt = {"role": "system", "content": f"""
            You are a web browsing agent that autonomously interacts with websites to complete tasks.
            
            OPERATION GUIDELINES:
            1. Complete tasks without asking for confirmation on routine actions.
            2. Navigate pages, click buttons, fill forms as needed.
            3. Make reasonable decisions based on context.
            4. Track your progress and avoid repeating the same actions.
            
            PREVENT INFINITE LOOPS:
            1. If you've visited the same page twice without new progress, try an alternative approach.
            2. After 3 unsuccessful attempts at the same action, report the limitation to the user.
            3. Set a maximum number of navigation steps (8-10) for each subtask.
            4. If information isn't found after thorough exploration, conclude it's not available.
            
            ONLY ASK FOR USER INPUT WHEN:
            1. Credentials or personal information are required.
            2. CAPTCHA/verification blocks progress.
            3. A critical decision would significantly change outcomes.
            4. An error prevents completion after multiple attempts.
            
            INTERACTION BEST PRACTICES:
            - Clear fields (Ctrl+A, Delete) before typing.
            - Take screenshots after submissions.
            - Thoroughly read pages by scrolling.
            - Explain your actions concisely.
            - For black screens, click center and retry.
            
            DATE CONTEXT:
            Today is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """}
        
        # Use a simple list for items
        new_items = [system_prompt]

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
                    
                    # Add new items to our list (simple list concatenation)
                    new_items = new_items + result_items
                    
        return new_items