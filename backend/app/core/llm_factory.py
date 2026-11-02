"""
ContextIQ — LLM Factory
=========================
Single place to initialise the language model. All other modules call get_llm()
and never import ChatGoogleGenerativeAI or ChatGroq directly.

WHY A FACTORY?
- Switching LLM provider = change one env var (LLM_PROVIDER=groq), restart server.
  No code changes, no redeployment of logic.
- Fallback key: if the primary Gemini key hits rate limits, the chain transparently
  retries with a second key via .with_fallbacks(). The caller never knows.
- temperature=0 on all providers: deterministic output for support answers.
  A VPN reset procedure should not vary between calls.

SUPPORTED PROVIDERS (set LLM_PROVIDER in .env):
  "gemini"  → Google Gemini Flash (default)
  "groq"    → Llama 3.1 8B via Groq (fast, free tier)

CALLED BY:
  agent.py      → llm = get_llm()        (builds the ReAct agent)
  rag_chain.py  → llm = get_llm()        (answers after retrieval)
  Both call at module import — one LLM instance per process.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from app.config import settings


def get_llm():
    """
    Factory function to initialize and return the LLM based on the LLM_PROVIDER
    environment variable. This allows seamless switching between Gemini and Groq.
    """
    provider = settings.LLM_PROVIDER
    
    if provider == "groq":
        # Check if key exists
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in your .env file!")
            
        return ChatGroq(
            model="llama-3.1-8b-instant",  # Switched to 8B because 70B is exhausted and decommissioned. The docstring now contains anti-hallucination instructions.
            temperature=0,
            api_key=settings.GROQ_API_KEY
        )
    
    elif provider == "gemini":
        main_llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            temperature=0,
            google_api_key=settings.GOOGLE_API_KEY
        )
        if settings.GOOGLE_API_KEY_FALLBACK:
            fallback_llm = ChatGoogleGenerativeAI(
                model="gemini-3.5-flash",
                temperature=0,
                google_api_key=settings.GOOGLE_API_KEY_FALLBACK
            )
            return main_llm.with_fallbacks([fallback_llm])
        return main_llm
        
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{provider}'. Valid options are 'gemini' or 'groq'.")
