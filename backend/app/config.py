import os
from dotenv import load_dotenv

# Load environment variables from a .env file.
# override=True ensures .env always wins over any cached terminal variables.
load_dotenv(override=True)


class Settings:
    """
    Single source of truth for all configuration values.
    Every env var is read here exactly once; all other modules import `settings`.

    Defaults are chosen to work out-of-the-box for local development.
    Override any value in .env without touching code.
    """

    def __init__(self):
        # ── API Keys ────────────────────────────────────────────────────────────
        self.GOOGLE_API_KEY          = os.getenv("GOOGLE_API_KEY", "").strip()
        self.GOOGLE_API_KEY_FALLBACK = os.getenv("GOOGLE_API_KEY_FALLBACK", "").strip()
        self.GROQ_API_KEY            = os.getenv("GROQ_API_KEY", "").strip()

        # ── Observability ───────────────────────────────────────────────────────
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "").strip()

        # ── LLM ─────────────────────────────────────────────────────────────────
        # LLM_PROVIDER: "gemini" | "groq"
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower().strip()

        # ── Embeddings ──────────────────────────────────────────────────────────
        # EMBEDDING_PROVIDER: "google" (cloud, zero RAM) | "huggingface" (local, ~400MB RAM)
        self.EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "google").lower().strip()
        self.GOOGLE_EMBEDDING_MODEL = os.getenv(
            "GOOGLE_EMBEDDING_MODEL", "models/gemini-embedding-001"
        ).strip()

        # ── Retrieval / RAG ─────────────────────────────────────────────────────
        # DEFAULT_RETRIEVAL_STRATEGY: "metadata_chunk" | "parent_document"
        self.DEFAULT_RETRIEVAL_STRATEGY = os.getenv(
            "DEFAULT_RETRIEVAL_STRATEGY", "metadata_chunk"
        )
        self.K_RESULTS    = int(os.getenv("K_RESULTS", 3))
        self.CHUNK_SIZE   = int(os.getenv("CHUNK_SIZE", 400))
        self.CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 50))

        # ── Agent behaviour (A/B testable without code changes) ─────────────────
        self.TOOL_DESCRIPTION = os.getenv(
            "TOOL_DESCRIPTION",
            (
                "Use this tool ONLY to answer questions about Accenture internal IT "
                "support issues, strictly limited to: VPN connectivity, password resets, "
                "timesheet/portal login errors, laptop/hardware requests, printer setup, "
                "software license requests, email access, and WiFi/network issues. "
                "Do NOT use this tool for general knowledge, coding help, or any "
                "non-IT topic."
            ),
        )
        self.RAG_SYSTEM_PROMPT = os.getenv(
            "RAG_SYSTEM_PROMPT",
            (
                "You are an IT support AI assistant for Accenture. "
                "Answer the user's question based ONLY on the following context. "
                "Do not use any external knowledge.\n\n"
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "Answer:"
            ),
        )

        # ── Security ────────────────────────────────────────────────────────────
        # CORS_ORIGINS: comma-separated list of allowed origins.
        # Defaults to "*" for local dev. In production set to your exact Vercel URL:
        #   CORS_ORIGINS=https://context-iq-frontend-seven.vercel.app
        _raw_origins = os.getenv("CORS_ORIGINS", "*")
        self.CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",")]

        # ── Logging ─────────────────────────────────────────────────────────────
        # LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper().strip()


# Instantiate once — all modules do `from app.config import settings`
settings = Settings()
