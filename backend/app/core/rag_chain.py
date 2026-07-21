from langchain_core.prompts import PromptTemplate
from app.config import settings
from .retrieval_strategies import get_strategy
from .vectorstore import get_vectorstore, get_ticket_lookup
from .llm_factory import get_llm

# Initialize the LLM via factory
llm = get_llm()

# Standard RAG prompt
RAG_PROMPT_TEMPLATE = """
You are an IT support AI assistant. Answer the user's question based ONLY on the following context.
If the answer cannot be found in the context, say "I don't know" and do not guess.

Context:
{context}

Question: {question}

Answer:
"""
rag_prompt = PromptTemplate.from_template(RAG_PROMPT_TEMPLATE)

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
