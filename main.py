from app.agents.agent_loop import AgentLoop
from dotenv import load_dotenv


load_dotenv(override=True)

if __name__ == "__main__":
    # Initialize the orchestrator
    agent = AgentLoop()
    
    # Example query
    user_query = input("What would you like help with today? ")
    
    # Run the agent
    result = agent.run(user_query)
    
    # Print the final result
    print("\n====== FINAL RESULT ======")
    print(result)