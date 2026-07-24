import os
import sys

# Ensure backend directory is in sys.path so 'app' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.agent import create_it_agent
from app.core.telemetry import get_langfuse_handler

def run_telemetry_test():
    print("Initializing IT Agent...")
    agent = create_it_agent()
    
    print("Setting up Langfuse CallbackHandler...")
    langfuse_handler = get_langfuse_handler()
    
    if not langfuse_handler:
        print("Langfuse is not configured. Please set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in .env")
        return
        
    callbacks = [langfuse_handler]
    
    test_queries = [
        "How do I reset my Windows password?",
        "My VPN isn't connecting and gives error 809.",
        "I need a license for Adobe Photoshop.",
        "What is the capital of France?" # General knowledge to see routing
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n[{i}/{len(test_queries)}] Running query: '{query}'")
        print("-" * 50)
        
        # We attach the Langfuse handler directly to the invoke call via config
        # This will automatically trace the agent steps, LLM calls, and tool executions.
        result = agent.invoke(
            {"messages": [("user", query)]},
            config={"callbacks": callbacks}
        )
        
        answer = result["messages"][-1].content
        print(f"Agent Answer: {answer}")

    print("\n" + "="*50)
    print("Test complete. Please check your Langfuse dashboard to see the traces.")
    print("You should see the LLM and Agent steps in Langfuse, and the Chroma DB spans in your console output!")
    
if __name__ == "__main__":
    run_telemetry_test()
