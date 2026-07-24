import os
from dotenv import load_dotenv

# Load environment variables from a .env file located in the same directory or parent directories
# override=True ensures that it reads from .env even if the terminal has a cached variable
load_dotenv(override=True)

class Settings:
    def __init__(self):
        # Fetch environment variables using os.getenv. If the variable is not found, it returns None.
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
        self.GOOGLE_API_KEY_FALLBACK = os.getenv("GOOGLE_API_KEY_FALLBACK", "").strip()
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
        
        # LLM Provider Configuration
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
        
        # Embeddings Provider Configuration
        self.EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "google").lower().strip()
        
        # RAG Configurations
        self.DEFAULT_RETRIEVAL_STRATEGY = os.getenv("DEFAULT_RETRIEVAL_STRATEGY", "similarity")
        self.K_RESULTS = int(os.getenv("K_RESULTS", 3))
        self.CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 400))
        self.CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))
        
        self.TOOL_DESCRIPTION = os.getenv("TOOL_DESCRIPTION", "Use this tool to answer questions about internal IT support issues. Just give the user the answer.")
        self.RAG_SYSTEM_PROMPT = os.getenv("RAG_SYSTEM_PROMPT", "You are an IT support AI assistant. Answer the user's question based ONLY on the following context.\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:")

# Instantiate a single settings object to be imported across the application
settings = Settings()
