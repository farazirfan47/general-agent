from app.agents.cua.cua_agent import CuaAgent
from app.agents.cua.docker_computer import  DockerComputer
from app.agents.cua.local_playwright import LocalPlaywrightComputer

def handle_cua_request(task):
    with LocalPlaywrightComputer() as computer:
        agent = CuaAgent(computer=computer)
        input_items = [{"role": "user", "content": task}]
        response_items = agent.run_full_turn(input_items, debug=True, show_images=True)
        formatted_response = format_response(response_items)
        print(formatted_response)
        return formatted_response
    
def format_response(response_items):
    # loop through all the response items and create a string like this:
    # User: ...
    # Assistant: ...
    response_str = ""
    for item in response_items:
        if item["role"] == "user":
            text = item["content"]
            response_str += f"User: {text}\n"
        elif item["role"] == "assistant":
            text = item["content"]["text"]
            response_str += f"Assistant: {text}\n"
    return response_str