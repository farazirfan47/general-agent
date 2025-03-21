from app.agents.agent_loop import AgentLoop
from dotenv import load_dotenv
import os
import sys


load_dotenv(override=True)

def main():
    # Check if a session ID was provided
    session_id = None
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        print(f"Loading existing session: {session_id}")
    
    # Initialize the agent with the provided or new session
    agent = AgentLoop(session_id=session_id)
    current_session_id = agent.get_session_id()
    
    print(f"Session ID: {current_session_id}")
    print("Type 'exit' to quit, 'new' to start a new session")
    
    try:
        while True:
            # Get user input
            user_query = input("\nWhat would you like help with today? ")
            
            # Check for special commands
            if user_query.lower() == 'exit':
                break
            elif user_query.lower() == 'new':
                # Create a new session
                agent = AgentLoop()
                current_session_id = agent.get_session_id()
                print(f"Started new session: {current_session_id}")
                continue
            
            # Run the agent (the run method internally uses asyncio.run)
            result = agent.run(user_query)
            
            # Print the final result
            print("\n====== FINAL RESULT ======")
            print(result)
            print("\n====== SESSION ID ======")
            print(f"Current session ID: {current_session_id}")
            print("(Save this ID to continue this conversation later)")
    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()