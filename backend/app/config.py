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

# Instantiate a single settings object to be imported across the application
settings = Settings()
