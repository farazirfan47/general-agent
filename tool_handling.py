import asyncio
from app.agents.cua.cua_agent import CuaAgent
from app.agents.cua.docker_computer import DockerComputer
from app.agents.cua.local_playwright import LocalPlaywrightComputer
from app.agents.cua.scrapybara import ScrapybaraBrowser

async def handle_cua_request(task, emit_event_async=None):
    """
    Handle a CUA request with direct event emission.
    
    Args:
        task: The task to execute
        emit_event_async: Function to emit socket events directly
    
    Returns:
        Formatted response from CUA agent
    """
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
        
        # Execute the full turn with direct event emission
        input_items = [{"role": "user", "content": task}]
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