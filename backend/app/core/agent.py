from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from app.config import settings
from .rag_chain import ask_question
from .llm_factory import get_llm

# Initialize the LLM via factory
llm = get_llm()

@tool
def it_support_lookup(question: str) -> str:
    """
    Use this tool to answer questions about internal IT support issues such as VPN connectivity, 
    password resets, timesheet or portal login errors, hardware requests, printer problems, 
    software licenses, or email/network access issues. 
    
    Do not use this tool for general knowledge questions unrelated to IT support.
    
    WHY THIS DOCSTRING IS CRITICAL:
    In a ReAct agent, the LLM reads the docstring of every available tool to decide whether 
    to use it. A vague docstring (like "Searches the database") will confuse the LLM into 
    routing general questions here. A highly specific docstring ensures perfect routing.
    """
    # Call our RAG chain
    result = ask_question(question)
    # The agent just needs the string answer. It doesn't need our internal structure.
    return result["answer"]

def create_it_agent():
    """
    Builds the ReAct agent using LangGraph.
    Note: In modern LangChain, AgentExecutor has been deprecated in favor of LangGraph.
    
    WHAT IS THE REACT LOOP?
    ReAct stands for Reason + Act. 
    Step 1 (Thought): The LLM analyzes the user's question and reads the tool docstrings.
    Step 2 (Action): If it decides a tool is needed, it outputs an Action (e.g., call `it_support_lookup`).
    Step 3 (Observation): The tool executes and returns its result back to the LLM.
    Step 4 (Thought): The LLM reads the observation. If it has enough info, it generates the Final Answer.
                      If not, it calls another tool. (Repeat).
    """
    tools = [it_support_lookup]
    
    # Construct the ReAct agent (the "brain") using LangGraph
    # This replaces the old create_react_agent + AgentExecutor pattern
    agent = create_react_agent(llm, tools)
    
    return agent


def run_agent_verbose(agent, query: str):
    """
    Helper function to run the LangGraph agent and print the intermediate steps 
    (mimicking verbose=True from the old AgentExecutor).
    """
    print(f"\nQuestion: {query}")
    print("-" * 50)
    
    # Stream the events from the agent to see the ReAct loop in action
    events = agent.stream(
        {"messages": [("user", query)]},
        stream_mode="values"
    )
    
    for event in events:
        message = event["messages"][-1]
        
        # If it's an AI message with a tool call (Action)
        if hasattr(message, "tool_calls") and message.tool_calls:
            print(f"🤔 THOUGHT / ACTION: The agent decided to call tool '{message.tool_calls[0]['name']}' with args: {message.tool_calls[0]['args']}")
        
        # If it's a Tool message (Observation)
        elif hasattr(message, "name") and message.type == "tool":
            print(f"🔍 OBSERVATION (Tool Result): {message.content[:200]}...")
            
        # If it's the final AI answer
        elif message.type == "ai" and (not hasattr(message, "tool_calls") or not message.tool_calls):
            if message.content:
                print(f"✅ FINAL ANSWER: {message.content}")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("INITIALIZING REACT AGENT")
    print("="*50)
    
    agent = create_it_agent()
    
    print("\n\n--- TEST 1: GENERAL KNOWLEDGE (EXPECT: NO TOOL INVOKED) ---")
    general_question = "What is the capital of France?"
    run_agent_verbose(agent, general_question)
    
    print("\n\n--- TEST 2: IT SUPPORT (EXPECT: TOOL INVOKED) ---")
    it_question = "My VPN keeps failing authentication, what do I do?"
    run_agent_verbose(agent, it_question)
    
    print("\nTests complete!")
