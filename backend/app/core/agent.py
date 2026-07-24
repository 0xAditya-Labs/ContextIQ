from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from app.config import settings
from .rag_chain import ask_question
from .llm_factory import get_llm
from .telemetry import get_langfuse_handler

# Initialize the LLM via factory
llm = get_llm()

from langchain_core.tools import StructuredTool

def it_support_lookup_func(question: str) -> str:
    # Call our RAG chain
    result = ask_question(question)
    # The agent just needs the string answer. It doesn't need our internal structure.
    return result["answer"]

# Dynamically construct the tool so we can A/B test the description from the .env file
it_support_lookup = StructuredTool.from_function(
    func=it_support_lookup_func,
    name="it_support_lookup",
    description=settings.TOOL_DESCRIPTION,
    return_direct=True
)

AGENT_SYSTEM_PROMPT = """You are ContextIQ, a strictly scoped enterprise IT support assistant for Accenture.

Your ONLY purpose is to help with ONE of these 8 internal IT support categories:
1. VPN connectivity and authentication issues
2. Password resets and account lockouts
3. Timesheet and internal portal login errors
4. Laptop and hardware requests
5. Printer setup and troubleshooting
6. Software license requests
7. Email access problems
8. WiFi and network access issues

STRICT RULES:
- If the user's question clearly falls into one of the 8 categories above, use the `it_support_lookup` tool.
- If the user's question is outside these 8 categories (e.g. general knowledge, geography, coding help, news, weather, or anything not IT-related), you MUST respond ONLY with this exact message:
  "I'm sorry, I can only assist with Accenture IT support topics such as VPN, passwords, timesheets, hardware, printers, software licenses, email, or network issues. Please contact the general helpdesk for other enquiries."
- NEVER use your general knowledge to answer questions that are not in the 8 categories.
- NEVER answer questions about geography, history, science, news, or any non-IT topic.
"""

def create_it_agent():
    """
    Builds the ReAct agent using LangGraph.
    
    The agent is given a strict system prompt that confines it to the 8 IT support
    categories. Questions outside these categories are rejected without touching the 
    Vector DB, saving both latency and API token costs.
    
    NOTE: AgentExecutor has been removed in newer versions of LangChain in favor of LangGraph.
    Therefore, we use LangGraph's `create_react_agent` instead of AgentExecutor.
    """
    from langchain_core.messages import SystemMessage
    tools = [it_support_lookup]
    
    # Inject the strict system prompt so the agent refuses off-topic questions
    agent = create_react_agent(
        llm,
        tools,
        prompt=AGENT_SYSTEM_PROMPT
    )
    
    return agent


def run_agent_verbose(agent, query: str):
    """
    Helper function to run the LangGraph agent and print the intermediate steps.
    """
    print(f"\nQuestion: {query}")
    print("-" * 50)
    
    # We use recursion_limit=8 to mimic a maximum of 3 tool calls.
    # (In LangGraph, each tool call uses 2 recursion steps: agent -> tool -> agent).
    # This acts as a hard safety net to prevent infinite loops.
    callbacks = []
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        callbacks.append(langfuse_handler)
        
    events = agent.stream(
        {"messages": [("user", query)]},
        stream_mode="values",
        config={
            "recursion_limit": 8,
            "callbacks": callbacks
        }
    )
    
    tool_calls_count = 0
    
    for event in events:
        message = event["messages"][-1]
        
        # If it's an AI message with a tool call (Action)
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls_count += 1
            print(f" ---> THOUGHT / ACTION: The agent decided to call tool '{message.tool_calls[0]['name']}' with args: {message.tool_calls[0]['args']}")
        
        # If it's a Tool message (Observation)
        elif hasattr(message, "name") and message.type == "tool":
            print(f"----> OBSERVATION (Tool Result): {message.content[:200]}...")
            
        # If it's the final AI answer
        elif message.type == "ai" and (not hasattr(message, "tool_calls") or not message.tool_calls):
            if message.content:
                print(f"--->  FINAL ANSWER: {message.content}")
                
    print(f"\nTotal Tool Calls: {tool_calls_count}")

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
