"""
ContextIQ — LangGraph ReAct Agent
===================================
Defines the agent's system prompt, tool, and graph construction.

Key design decisions:
- Tool description is loaded from env (TOOL_DESCRIPTION) → A/B testable without code changes.
- recursion_limit=8 caps the agent at 4 tool calls (each call = 2 graph edges).
- Sources are captured via a thread-local side-channel so the route layer can
  return them in the API response without changing the tool's return type.
- The agent object itself is NOT created here at module level — routes.py
  creates and caches it once at startup via create_it_agent().
"""

import threading
import logging

from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent

from app.config import settings
from .rag_chain import ask_question
from .llm_factory import get_llm
from .telemetry import get_langfuse_handler

logger = logging.getLogger("contextiq.agent")

# Initialise LLM once at module import — reused by both the agent and the RAG chain
llm = get_llm()

# --- Sources side-channel ---
# Problem: the tool must return a plain string (the agent reads it as an Observation).
#          But we also want the route layer to know which ticket IDs were retrieved.
# Solution: store sources in a thread-local so each request's thread gets its own slot.
#           threading.local() is the correct primitive for sync FastAPI route handlers
#           which run in a thread-pool (not inside the async event loop).
_sources_store = threading.local()


def it_support_lookup_func(question: str) -> str:
    """
    Calls the RAG chain and captures source ticket IDs as a thread-local side effect.
    The agent sees only the plain-string answer; the route layer reads the sources
    separately via get_last_sources().
    """
    result = ask_question(question)
    # Stash sources in thread-local storage so the route handler can retrieve them
    _sources_store.last_sources = result.get("sources", [])
    logger.info(f"Tool called | sources found: {result.get('sources', [])}")
    return result["answer"]


def get_last_sources() -> list:
    """
    Returns the source ticket IDs from the most recent tool call on this thread.
    Returns [] if the agent rejected the query without calling the tool.
    """
    return getattr(_sources_store, "last_sources", [])


# Build the StructuredTool — description drives the agent's gating decision
it_support_lookup = StructuredTool.from_function(
    func=it_support_lookup_func,
    name="it_support_lookup",
    description=settings.TOOL_DESCRIPTION,
    return_direct=True,
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
    Compiles and returns a LangGraph ReAct agent.

    Why LangGraph over AgentExecutor?
    AgentExecutor is deprecated in modern LangChain. LangGraph models the agent
    loop as a directed graph, giving explicit control over recursion depth,
    streaming events, and step-level inspection.

    recursion_limit=8 explanation:
    Each tool call traverses 2 graph edges (agent → tool → agent).
    Limit of 8 = max 4 tool invocations. Acts as a hard safety net against
    infinite reasoning loops.

    NOTE: This function is called ONCE at module import in routes.py and the
    result is cached. Graph compilation is not cheap — do not call per-request.
    """
    tools = [it_support_lookup]
    agent = create_react_agent(
        llm,
        tools,
        prompt=AGENT_SYSTEM_PROMPT,
    )
    logger.info("ReAct agent compiled and ready.")
    return agent


def run_agent_verbose(agent, query: str):
    """
    Dev/test helper: streams and prints every intermediate agent step.
    Not used in production routes.
    """
    print(f"\nQuestion: {query}")
    print("-" * 50)

    callbacks = []
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        callbacks.append(langfuse_handler)

    events = agent.stream(
        {"messages": [("user", query)]},
        stream_mode="values",
        config={
            "recursion_limit": 8,
            "callbacks": callbacks,
        },
    )

    tool_calls_count = 0
    for event in events:
        message = event["messages"][-1]

        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls_count += 1
            print(
                f" ---> THOUGHT / ACTION: called '{message.tool_calls[0]['name']}' "
                f"with args: {message.tool_calls[0]['args']}"
            )
        elif hasattr(message, "name") and message.type == "tool":
            print(f"----> OBSERVATION (Tool Result): {message.content[:200]}...")
        elif message.type == "ai" and not (
            hasattr(message, "tool_calls") and message.tool_calls
        ):
            if message.content:
                print(f"--->  FINAL ANSWER: {message.content}")

    print(f"\nTotal Tool Calls: {tool_calls_count}")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("INITIALIZING REACT AGENT")
    print("=" * 50)

    agent = create_it_agent()

    print("\n\n--- TEST 1: GENERAL KNOWLEDGE (EXPECT: NO TOOL INVOKED) ---")
    run_agent_verbose(agent, "What is the capital of France?")

    print("\n\n--- TEST 2: IT SUPPORT (EXPECT: TOOL INVOKED) ---")
    run_agent_verbose(agent, "My VPN keeps failing authentication, what do I do?")

    print("\nTests complete!")
