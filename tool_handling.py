import asyncio
import datetime
from app.agents.cua.cua_agent import CuaAgent
from app.agents.cua.docker_computer import DockerComputer
from app.agents.cua.local_playwright import LocalPlaywrightComputer
from app.agents.cua.scrapybara import ScrapybaraBrowser
from utils import create_response

async def enrich_task_with_llm(task):
    """
    Enriches a user task with additional context and detailed instructions using an LLM.
    Creates a comprehensive set of instructions for the browser agent based on the task nature.
    
    Args:
        task: The original user task
        
    Returns:
        Comprehensive instructions for the browser agent
    """
    
    # Base instructions that the LLM should incorporate and expand upon
    base_instructions = """
    You are a web browsing agent that autonomously interacts with websites to complete tasks.
    
    OPERATION GUIDELINES:
    1. Complete tasks without asking for confirmation on routine actions.
    2. Make decisive choices and stick with them - avoid website hopping.
    3. For listing or ranking tasks, choose ONE authoritative source and stay there.
    4. Explicitly extract and document specific information from pages.
    5. Track your progress with numbered steps to maintain focus.
    
    STRUCTURED TASK APPROACH:
    1. Begin by clearly defining what constitutes task completion.
    2. Choose ONE definitive source for information and commit to it.
    3. After selecting a source, spend no more than 2 minutes exploring before extracting information.
    4. Document findings in a structured format as you discover them.
    5. Conclude with a formal summary of findings, even if incomplete.
    
    PREVENT ERRATIC NAVIGATION:
    1. No back-and-forth scrolling - scroll methodically in ONE direction only.
    2. Avoid switching between multiple websites/tabs for the same information.
    3. After clicking any link, spend at least 30 seconds exploring that page before navigating away.
    4. Limit to maximum 3 different websites for any single task.
    5. If a website has the information you need, do not leave it to search elsewhere.
    
    CONTROLLED SCROLLING TECHNIQUE:
    1. Scroll in small, incremental steps (~25% of viewport).
    2. Scroll in ONE direction only, recording information as you go.
    3. If you need to "scroll back," take a screenshot first, then navigate to a specific section.
    4. For any page, perform a maximum of 5 scroll operations total.
    5. After each scroll, document ANY relevant information immediately.
    
    EXPLICIT INFORMATION EXTRACTION:
    1. For listing tasks, create a numbered list of items as you discover them.
    2. After finding 5-10 items, stop gathering and present results.
    3. For each item discovered, immediately document key attributes.
    4. If an authoritative list is found, trust it without verification.
    """
    
    prompt = f"""
    You are an expert at creating detailed instructions for an autonomous web browsing agent.
    
    ORIGINAL TASK: {task}
    
    BASE INSTRUCTIONS: {base_instructions}
    
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
    comprehensive_instructions = await enrich_task_with_llm(task)
    
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
        {comprehensive_instructions}
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