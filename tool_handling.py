import asyncio
import datetime
from app.agents.cua.cua_agent import CuaAgent
from app.agents.cua.docker_computer import DockerComputer
from app.agents.cua.local_playwright import LocalPlaywrightComputer
from app.agents.cua.scrapybara import ScrapybaraBrowser
from utils import create_response

# Base instructions that the LLM should incorporate and expand upon
base_instructions = """
You are a web browsing agent that completes tasks autonomously.

CRITICAL SCROLLING RULES:
1. NEVER scroll to the absolute top or bottom of any page - this causes you to miss content.
2. Use INCREMENTAL scrolling - move approximately 20-30% of the viewport at a time.
3. After each incremental scroll, IMMEDIATELY document any visible content relevant to your task.
4. Count your scrolls explicitly: "Scroll #1", "Scroll #2", etc. to maintain awareness of position.
5. Limit consecutive scrolls in the same direction to a maximum of 5 before processing content.
6. If you notice you've reached a footer or header area, STOP scrolling in that direction.
7. When changing scroll direction, move in small increments (10-15% of viewport).
8. NEVER perform rapid consecutive scrolls - pause between each scroll action.

PREVENT SCROLLING ERRORS:
1. After any scroll action, verify you can see new content by mentioning specific elements now visible.
2. If you detect only navigation elements, headers, or footers after scrolling, immediately adjust your position.
3. Use specific CSS selectors or element descriptions when documenting to prove content visibility.
4. When content appears to repeat or you see only navigation elements, use "page up" or "page down" instead of continuous scrolling.
"""

async def enrich_task_with_llm(task):
    """
    Enriches a user task with additional context and detailed instructions using an LLM.
    Creates a comprehensive set of instructions for the browser agent based on the task nature.
    
    Args:
        task: The original user task
        
    Returns:
        Comprehensive instructions for the browser agent
    """
    
    prompt = f"""
    You are an expert at creating detailed instructions for an autonomous web browsing agent.
    
    ORIGINAL TASK: {task}
        
    DATE CONTEXT: Today is {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Please create a comprehensive set of instructions for the browser agent that:
    1. Incorporates and adapts the base instructions to this specific task
    2. Adds specific search terms the agent should use
    3. Suggests expected websites or sources to prioritize
    4. Specifies exact data points to extract
    5. Defines clear success criteria
    6. Provides fallback strategies if initial approaches fail
    7. Includes any domain-specific knowledge relevant to this task
    
    Your response should be a complete set of instructions ready to be given to the browser agent.
    Format the response as if you are directly instructing the browser agent.
    Do not include meta-commentary or explanations about the instructions themselves.
    """
    
    # Call the LLM service to get the comprehensive instructions
    comprehensive_instructions = create_response(
        model="o3-mini",
        input=[{"role": "user", "content": prompt}]
    )
    return comprehensive_instructions

async def handle_cua_request(task, emit_event_async=None):
    """
    Handle a CUA request with direct event emission.
    
    Args:
        task: The task to execute
        emit_event_async: Function to emit socket events directly
    
    Returns:
        Formatted response from CUA agent
    """
    
    # Get comprehensive instructions tailored to this specific task
    # comprehensive_instructions = await enrich_task_with_llm(task)
    
    # Create a new computer instance
    with ScrapybaraBrowser() as computer:
        # Emit browser_started event with stream URL as soon as the computer is ready
        if emit_event_async:
            print("Emitting browser_started event")
            stream_url = computer.get_stream_url()
            if stream_url:
                # Frontend can use this to show the browser window
                browser_event_data = {"stream_url": stream_url}
                print("Emitting browser_started event with data:", browser_event_data)
                if asyncio.iscoroutinefunction(emit_event_async):
                    await emit_event_async("browser_started", browser_event_data)
                else:
                    emit_event_async("browser_started", browser_event_data)
        
        # Pass emit_event_async directly to CuaAgent
        agent = CuaAgent(
            computer=computer, 
            # Pass the event emitter directly to CuaAgent
            emit_event_async=emit_event_async
        )

        # Format the task with the comprehensive instructions
        formatted_task = f"""
        <instructions>
        {base_instructions}
        </instructions>
        <task>
        {task}
        </task>

        IMPORTANT: When you are done with the task, summarize your findings in a structured format.
        """

        print(f"Formatted task: {formatted_task}")
        
        # Execute the full turn with direct event emission
        input_items = [{"role": "user", "content": formatted_task}]
        response_items = await agent.run_full_turn(input_items, debug=True)
        
        # Simplify to get just the text response
        formatted_response = format_response(response_items)
        print(formatted_response)
        
    return formatted_response
    
def format_response(response_items):
    """
    Format the response from CUA agent into a simple text response.
    Stream URLs are now handled by direct events, not in the response.
    """
    # Format response string using the items
    response_str = ""
    
    # Format messages
    for item in response_items:
        if isinstance(item, dict) and "role" in item:
            if item["role"] == "user":
                text = item["content"]
                response_str += f"User: {text}\n"
            elif item["role"] == "assistant":
                # Handle potential variations in content structure
                if isinstance(item["content"], list) and len(item["content"]) > 0:
                    if isinstance(item["content"][0], dict) and "text" in item["content"][0]:
                        text = item["content"][0]["text"]
                    else:
                        text = str(item["content"][0])
                else:
                    text = str(item["content"])
                response_str += f"Assistant: {text}\n"
    
    return response_str.strip()