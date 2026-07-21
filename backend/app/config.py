import os
from dotenv import load_dotenv

# Load environment variables from a .env file located in the same directory or parent directories
load_dotenv()

class Settings:
    def __init__(self):
        # Fetch environment variables using os.getenv. If the variable is not found, it returns None.
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
        
        # LLM Provider Configuration
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()
        self.GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        
        # Retrieval strategy for RAG. Defaults to 'metadata_chunk'.
        # Valid values: 'metadata_chunk' or 'parent_document'
        self.DEFAULT_RETRIEVAL_STRATEGY = os.getenv("RETRIEVAL_STRATEGY", "metadata_chunk")

# Instantiate a single settings object to be imported across the application
settings = Settings()
