from app.agents.cua.computer import Computer
from utils import (
    create_response,
    show_image,
    pp,
    sanitize_message,
    check_blocklisted_url,
)
import json
from typing import Callable
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
    ):
        self.model = model
        self.computer = computer
        self.tools = tools
        self.print_steps = True
        self.debug = False
        self.show_images = False
        self.acknowledge_safety_check_callback = acknowledge_safety_check_callback

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

    def handle_item(self, item):
        """Handle each item; may cause a computer action + screenshot."""

        # Normal message handling
        if item["type"] == "message":
            print("We got text message back, could be question")
            if self.print_steps:
                # check if item["content"][0]["text"] is a question
                if item["content"][0]["text"].endswith("?"):
                    user_clarification = input("\nQuestion: " + item["content"][0]["text"] + "\n")
                    return [{"role": "user", "content": user_clarification}]

        # TODO: function call handling

        if item["type"] == "computer_call":
            action = item["action"]
            action_type = action["type"]
            action_args = {k: v for k, v in action.items() if k != "type"}
            if self.print_steps:
                print(f"{action_type}({action_args})")

            method = getattr(self.computer, action_type)
            method(**action_args)

            screenshot_base64 = self.computer.screenshot()
            if self.show_images:
                show_image(screenshot_base64)

            # if user doesn't ack all safety checks exit with error
            pending_checks = item.get("pending_safety_checks", [])
            for check in pending_checks:
                message = check["message"]
                if not self.acknowledge_safety_check_callback(message):
                    raise ValueError(
                        f"Safety check failed: {message}. Cannot continue with unacknowledged safety checks."
                    )

            call_output = {
                "type": "computer_call_output",
                "call_id": item["call_id"],
                "acknowledged_safety_checks": pending_checks,
                "output": {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{screenshot_base64}",
                },
            }

            # additional URL safety checks for browser environments
            if self.computer.environment == "browser":
                current_url = self.computer.get_current_url()
                check_blocklisted_url(current_url)
                call_output["output"]["current_url"] = current_url

            return [call_output]
        return []

    def run_full_turn(
        self, input_items, print_steps=True, debug=False, show_images=False
    ):
        self.print_steps = print_steps
        self.debug = debug
        self.show_images = show_images
        new_items = [
            {"role": "system", "content": f"""
                You are responsible for browsing and interacting with web pages in a sandboxed environment.
                
                OPERATION GUIDELINES:
                1. Act autonomously to accomplish the user's request without asking for confirmation or clarification for routine tasks.
                2. Navigate the web, click buttons, fill forms, and browse multiple pages as needed to complete the task.
                3. Make reasonable decisions based on context when encountering options (select most relevant link, use default settings, etc.).
                4. If multiple approaches exist, choose the most efficient path without asking the user.
                
                ONLY ASK FOR USER INPUT WHEN:
                1. Encountering login credentials, passwords, or personal identifiable information.
                2. Facing a CAPTCHA or verification challenge that blocks progress.
                3. Reaching a critical decision point that significantly changes the outcome (e.g., finalizing a purchase, selecting between fundamentally different options).
                4. Encountering an unexpected error or limitation that prevents task completion.
                
                VALIDATION CHECKS BEFORE ASKING:
                - Have I exhausted all possible autonomous approaches to resolve this?
                - Is this truly a critical decision that requires human judgment?
                - Would making a reasonable assumption here significantly impact the final outcome?
                - Is this information impossible to infer from previous context?
                
                INTERACTION BEST PRACTICES:
                - Always clear input fields with Ctrl+A and Delete before entering text.
                - After submitting with Enter, take an extra screenshot and move to the next field.
                - Optimize by combining related actions when possible to reduce function calls.
                - You can take actions on authenticated sites; assume the user is already authenticated.
                - For black screens, click the center and take another screenshot.
                - Read pages thoroughly by scrolling until sufficient information is gathered.
                - Explain your actions and reasoning clearly.
                - Break complex tasks into smaller steps.
                - If a request implies needing external information, search for it directly.
                - Zoom out or scroll to ensure all content is visible.
        
                DATE CONTEXT:
                Today is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """}
        ]

        # keep looping until we get a final response
        while new_items[-1].get("role") != "assistant" if new_items else True:
            self.debug_print([sanitize_message(msg) for msg in input_items + new_items])

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
                # concatenate new items
                new_items += response["output"]
                for item in response["output"]:
                    new_items += self.handle_item(item)

        return new_items