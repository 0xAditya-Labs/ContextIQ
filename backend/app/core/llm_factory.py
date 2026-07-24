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
        return ChatGoogleGenerativeAI(
            model="gemini-3.5-flash",
            temperature=0,
            api_key=settings.GOOGLE_API_KEY
        )
        
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{provider}'. Valid options are 'gemini' or 'groq'.")
