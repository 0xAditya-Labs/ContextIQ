"""
ContextIQ — ChromaDB Vector Store + Embeddings
===============================================
Key design decisions documented here:

1. GoogleRestEmbeddings — custom REST client bypassing the SDK.
   The langchain_google_genai SDK routes embedding calls through v1beta, where
   text-embedding-004 returns HTTP 404. Calling the stable v1 REST endpoint
   directly is the only reliable fix.

2. ChromaDBSingleton — prevents per-request disk I/O.
   PersistentClient reads from disk and acquires OS file locks on every
   instantiation. The singleton ensures this happens once at startup, not
   on every query.

3. perform_similarity_search — OTel-traced wrapper.
   Langfuse's CallbackHandler only sees LangChain operations. The raw
   chromadb call is invisible to it. The manual OTel span here lets us
   measure exact vector DB latency independently from LLM latency.
"""

import os
import logging

import requests
import chromadb
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from .ticket_parser import parse_tickets

logger = logging.getLogger("contextiq.vectorstore")


# ── Custom Embeddings ──────────────────────────────────────────────────────────

class GoogleRestEmbeddings:
    """
    LangChain-compatible embeddings that call the Google Generative AI
    REST API on the stable v1 endpoint directly.

    Why not use langchain_google_genai?
    The package's internal google-genai SDK routes through v1beta.
    Calling v1 directly via requests provides stable model access and key fallback.
    """

    DEFAULT_MODELS = [
        "models/gemini-embedding-001",
        "models/text-embedding-004",
    ]

    def __init__(self, api_key: str, fallback_api_key: str = None):
        from app.config import settings
        self.api_key          = api_key
        self.fallback_api_key = fallback_api_key
        preferred_model       = getattr(settings, "GOOGLE_EMBEDDING_MODEL", "").strip()
        self.models = [preferred_model] if preferred_model else self.DEFAULT_MODELS

    def _call_api(self, text: str, api_key: str, model: str) -> list:
        if not model.startswith("models/"):
            model = f"models/{model}"
        url = f"https://generativelanguage.googleapis.com/v1/{model}:embedContent"
        response = requests.post(
            url,
            params={"key": api_key},
            json={"model": model, "content": {"parts": [{"text": text}]}},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embedding"]["values"]

    def _embed_one(self, text: str) -> list:
        """Embed a single string; tries available models and key fallback."""
        keys = [k for k in [self.api_key, self.fallback_api_key] if k]
        last_error = None

        for model in self.models:
            for key in keys:
                try:
                    return self._call_api(text, key, model)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"Embedding call failed with model '{model}' and key '...{key[-6:]}': {e}"
                    )

        if last_error:
            raise last_error
        raise RuntimeError("No Google API keys available for embeddings.")

    def embed_documents(self, texts: list) -> list:
        return [self._embed_one(t) for t in texts]

    def embed_query(self, text: str) -> list:
        return self._embed_one(text)


# ── ChromaDB Singleton ─────────────────────────────────────────────────────────

class ChromaDBSingleton:
    """
    Class-level singleton for both the ChromaDB client and the embeddings model.

    Why singleton?
    - PersistentClient: opening the same chroma_db/ from multiple client
      instances causes file-lock conflicts and redundant disk I/O.
    - Embeddings: loading a HuggingFace model from disk takes 1-3 seconds.
      Loading it once at startup vs once per request is the difference between
      a responsive service and a painfully slow one.

    Why class-level (not module-level)?
    Class-level state survives across imports; module-level globals can be
    re-initialised if the module is reloaded. Class vars are the safer pattern
    for long-lived singletons in an ASGI server.
    """

    _client_instance     = None
    _embeddings_instance = None

    @classmethod
    def get_client(cls) -> chromadb.PersistentClient:
        if cls._client_instance is None:
            path = "./chroma_db"
            logger.info(f"Initialising ChromaDB PersistentClient at '{path}'")
            cls._client_instance = chromadb.PersistentClient(path=path)
        return cls._client_instance

    @classmethod
    def get_embeddings(cls):
        if cls._embeddings_instance is None:
            from app.config import settings

            if settings.EMBEDDING_PROVIDER == "google":
                logger.info("Initialising Google REST embeddings (text-embedding-004, v1 API)")
                cls._embeddings_instance = GoogleRestEmbeddings(
                    api_key=settings.GOOGLE_API_KEY,
                    fallback_api_key=settings.GOOGLE_API_KEY_FALLBACK or None,
                )
            else:
                from langchain_huggingface import HuggingFaceEmbeddings
                logger.info(
                    "Initialising HuggingFace embeddings (all-MiniLM-L6-v2, local)"
                )
                cls._embeddings_instance = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )

        return cls._embeddings_instance


# ── Ingestion Pipeline ─────────────────────────────────────────────────────────

def prepare_and_store_documents() -> dict:
    """
    Full ingestion pipeline:
      parse .txt → create Documents → chunk → embed → store in ChromaDB.

    Returns:
        dict: ticket_id → full_text mapping (used by ParentDocumentStrategy).

    Called automatically by main.py's startup_event if chroma_db/ is absent.
    """
    current_dir = os.path.dirname(__file__)
    file_path   = os.path.join(current_dir, "..", "data", "dummy_it_tickets.txt")

    logger.info(f"Parsing tickets from {file_path}")
    parsed_tickets = parse_tickets(file_path)

    documents     = []
    ticket_lookup = {}

    for ticket in parsed_tickets:
        doc = Document(
            page_content=ticket["full_text"],
            metadata={
                "ticket_id": ticket["ticket_id"],
                "category":  ticket["category"],
            },
        )
        documents.append(doc)
        ticket_lookup[ticket["ticket_id"]] = ticket["full_text"]

    from app.config import settings

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = text_splitter.split_documents(documents)
    logger.info(f"Created {len(chunks)} chunks from {len(parsed_tickets)} tickets")

    embeddings    = ChromaDBSingleton.get_embeddings()
    chroma_client = ChromaDBSingleton.get_client()

    vectorstore = Chroma(
        client=chroma_client,
        collection_name="it_tickets_collection",
        embedding_function=embeddings,
    )
    vectorstore.add_documents(chunks)
    logger.info(f"Stored {len(chunks)} chunks in ChromaDB collection 'it_tickets_collection'")

    return ticket_lookup


# ── Lazy ticket lookup ─────────────────────────────────────────────────────────

_ticket_lookup_cache: dict | None = None


def get_ticket_lookup() -> dict:
    """
    Lazy-loads and caches the ticket_id → full_text mapping.
    Used by ParentDocumentStrategy to fetch complete ticket text.
    """
    global _ticket_lookup_cache
    if _ticket_lookup_cache is None:
        current_dir = os.path.dirname(__file__)
        file_path   = os.path.join(current_dir, "..", "data", "dummy_it_tickets.txt")
        parsed      = parse_tickets(file_path)
        _ticket_lookup_cache = {t["ticket_id"]: t["full_text"] for t in parsed}
        logger.debug(f"Ticket lookup cached: {len(_ticket_lookup_cache)} entries")
    return _ticket_lookup_cache


# ── Vectorstore accessor ───────────────────────────────────────────────────────

def get_vectorstore() -> Chroma:
    """Returns a Chroma vectorstore object backed by the singleton client."""
    return Chroma(
        client=ChromaDBSingleton.get_client(),
        collection_name="it_tickets_collection",
        embedding_function=ChromaDBSingleton.get_embeddings(),
    )


# ── OTel-traced similarity search ─────────────────────────────────────────────

def perform_similarity_search(question: str, k: int = 3) -> list:
    """
    Runs chromadb similarity_search wrapped in a manual OpenTelemetry span.

    Why manual OTel (not just Langfuse)?
    Langfuse's CallbackHandler captures LangChain-managed operations.
    A raw chromadb call is invisible to it. The OTel span here gives us the
    exact DB-level latency so we can separate "LLM was slow" from "DB was slow".

    The span attributes (query text, k) are written to otel_traces.log and
    can be parsed to extract the concrete latency numbers for the resume.
    """
    from .telemetry import tracer

    vectorstore = get_vectorstore()

    with tracer.start_as_current_span("vector_db_search") as span:
        span.set_attribute("query", question)
        span.set_attribute("k", k)
        results = vectorstore.similarity_search(question, k=k)
        span.set_attribute("results_count", len(results))
        return results


if __name__ == "__main__":
    prepare_and_store_documents()
