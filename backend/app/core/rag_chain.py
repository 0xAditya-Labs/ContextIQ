"""
ContextIQ — RAG Chain
======================
This module is the INNER layer that does actual retrieval + LLM answer generation.
It is called by agent.py's tool function (it_support_lookup_func), NOT by routes.py directly.

Call chain:
  routes.py  →  agent.py (_agent.invoke)
             →  it_support_lookup_func (tool)
             →  ask_question (THIS FILE)
             →  retrieval_strategies.py (get chunks from ChromaDB)
             →  llm.invoke (get final answer from Gemini/Groq)

Design note:
  ask_question() is completely stateless — it takes a question string and
  returns a dict. The agent and route layers own state (metrics, sources, history).
  This makes it independently testable and easy to A/B test retrieval strategies.
"""

from langchain_core.prompts import PromptTemplate
from app.config import settings
from .retrieval_strategies import get_strategy
from .vectorstore import get_vectorstore, get_ticket_lookup
from .llm_factory import get_llm

# ── Module-level singletons ────────────────────────────────────────────────────
# LLM is initialised once at import time — creating it per-request is expensive
# (auth handshake, object allocation). This is safe because ChatGoogleGenerativeAI
# and ChatGroq are stateless between calls.
llm = get_llm()

# RAG prompt template — loaded from env so it can be swapped without redeploying.
# {context} and {question} are the two slots filled per request.
rag_prompt = PromptTemplate.from_template(settings.RAG_SYSTEM_PROMPT)


def ask_question(question: str, strategy_name: str = None) -> dict:
    """
    Retrieves context using a specific strategy and answers the question using an LLM.
    
    DEPENDENCY INJECTION PATTERN:
    By accepting strategy_name as a parameter with a config-driven default, we get the best 
    of both worlds:
    1. Good Defaults: In production, we don't have to specify the strategy on every single API call;
       it falls back to config.DEFAULT_RETRIEVAL_STRATEGY.
    2. Testability/Swappability: We can explicitly override it per-call during testing (e.g. A/B testing, 
       evaluating metrics in Langfuse) without having to restart the application or permanently change 
       the .env file! This is vastly superior to a pure env-var-only switch, which locks the entire app 
       into one strategy at runtime.
    """
    # 1. Resolve strategy
    if strategy_name is None:
        strategy_name = settings.DEFAULT_RETRIEVAL_STRATEGY
        
    strategy = get_strategy(strategy_name)
    
    # 2. Get dependencies
    vectorstore = get_vectorstore()
    ticket_lookup = get_ticket_lookup()
    
    # 3. Execute retrieval strategy
    retrieval_result = strategy.retrieve(question, vectorstore, ticket_lookup)
    context = retrieval_result["context"]
    source_ticket_ids = retrieval_result["source_ticket_ids"]
    source_categories = retrieval_result.get("source_categories", [])
    
    # 4. Prompt Gemini
    prompt_value = rag_prompt.invoke({"context": context, "question": question})
    
    try:
        response = llm.invoke(prompt_value)
        answer = response.content
    except Exception as e:
        answer = f"Error: Gemini models are down from Google side only. Details: {str(e)}"

    # 5. Return structured result
    return {
        "answer": answer,
        "sources": source_ticket_ids,
        "categories": source_categories,
        "strategy_used": strategy_name
    }

if __name__ == "__main__":
    # Test the function directly
    print(ask_question("how to reset my password of my laptop?"))
