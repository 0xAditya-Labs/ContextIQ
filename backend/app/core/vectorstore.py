import os
import requests
import chromadb
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from .ticket_parser import parse_tickets


class GoogleRestEmbeddings:
    """
    Custom LangChain-compatible embeddings class that calls the Google Generative
    AI REST API directly on the stable v1 endpoint.

    WHY: The `langchain_google_genai` package internally uses the `google-genai`
    SDK which routes embedding requests through v1beta. The text-embedding-004
    model is NOT available on v1beta, causing a persistent 404 error. Calling the
    stable v1 REST endpoint directly is the only reliable workaround.
    """

    MODEL   = "models/text-embedding-004"
    API_URL = f"https://generativelanguage.googleapis.com/v1/{MODEL}:embedContent"

    def __init__(self, api_key: str, fallback_api_key: str = None):
        self.api_key          = api_key
        self.fallback_api_key = fallback_api_key

    def _call_api(self, text: str, api_key: str) -> list:
        response = requests.post(
            self.API_URL,
            params={"key": api_key},
            json={"model": self.MODEL, "content": {"parts": [{"text": text}]}},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["embedding"]["values"]

    def _embed_one(self, text: str) -> list:
        """Embed a single string, falling back to the secondary key on failure."""
        try:
            return self._call_api(text, self.api_key)
        except Exception as primary_error:
            if self.fallback_api_key:
                print(f"Primary key failed ({primary_error}), trying fallback key...")
                return self._call_api(text, self.fallback_api_key)
            raise

    def embed_documents(self, texts: list) -> list:
        return [self._embed_one(text) for text in texts]

    def embed_query(self, text: str) -> list:
        return self._embed_one(text)


class ChromaDBSingleton:
    _client_instance    = None
    _embeddings_instance = None

    @classmethod
    def get_client(cls):
        """
        SINGLETON PATTERN: avoids re-initializing DB client on every call,
        which causes repeated disk I/O and slow cold-starts.
        """
        if cls._client_instance is None:
            cls._client_instance = chromadb.PersistentClient(path="./chroma_db")
        return cls._client_instance

    @classmethod
    def get_embeddings(cls):
        """
        SINGLETON PATTERN: load the expensive embedding weights once at startup.
        Switches between Google REST embeddings (cloud, zero memory) and
        HuggingFace (local, high memory) based on EMBEDDING_PROVIDER env var.
        """
        if cls._embeddings_instance is None:
            from app.config import settings
            if settings.EMBEDDING_PROVIDER == "google":
                print("Initializing Google REST embeddings (v1 API)...")
                cls._embeddings_instance = GoogleRestEmbeddings(
                    api_key=settings.GOOGLE_API_KEY,
                    fallback_api_key=settings.GOOGLE_API_KEY_FALLBACK or None,
                )
            else:
                from langchain_huggingface import HuggingFaceEmbeddings
                print("Initializing HuggingFace embeddings model (this runs locally)...")
                cls._embeddings_instance = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2"
                )
        return cls._embeddings_instance


def prepare_and_store_documents():
    """
    Reads the dummy IT tickets using ticket_parser, chunks the text while preserving
    ticket_id in metadata, creates embeddings, and stores them into ChromaDB.

    Returns:
        dict: A lookup mapping ticket_id to its full_text.
    """
    # 1. Parse tickets
    current_dir = os.path.dirname(__file__)
    file_path   = os.path.join(current_dir, "..", "data", "dummy_it_tickets.txt")

    print(f"Loading and parsing documents from {file_path}...")
    parsed_tickets = parse_tickets(file_path)

    # Create Document objects with metadata
    documents    = []
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

    # 2. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = text_splitter.split_documents(documents)

    # 3. Embeddings (Reuse Singleton)
    embeddings   = ChromaDBSingleton.get_embeddings()
    chroma_client = ChromaDBSingleton.get_client()

    # 4. Store in Vector Database (ChromaDB)
    print("Storing chunks into ChromaDB...")
    vectorstore = Chroma(
        client=chroma_client,
        collection_name="it_tickets_collection",
        embedding_function=embeddings,
    )

    vectorstore.add_documents(chunks)
    print(f"Successfully created and stored {len(chunks)} chunks!")

    # Return the ticket lookup for the ParentDocumentStrategy
    return ticket_lookup


_ticket_lookup_cache = None


def get_ticket_lookup():
    """
    Lazy-loads and returns the ticket lookup dictionary.
    Used by the ParentDocumentStrategy to fetch full ticket texts.
    """
    global _ticket_lookup_cache
    if _ticket_lookup_cache is None:
        current_dir = os.path.dirname(__file__)
        file_path   = os.path.join(current_dir, "..", "data", "dummy_it_tickets.txt")
        parsed_tickets        = parse_tickets(file_path)
        _ticket_lookup_cache  = {t["ticket_id"]: t["full_text"] for t in parsed_tickets}
    return _ticket_lookup_cache


def get_vectorstore():
    """Returns the initialized Chroma vectorstore object."""
    chroma_client = ChromaDBSingleton.get_client()
    embeddings    = ChromaDBSingleton.get_embeddings()
    return Chroma(
        client=chroma_client,
        collection_name="it_tickets_collection",
        embedding_function=embeddings,
    )


def perform_similarity_search(question: str, k: int = 3):
    """
    Wraps the Chroma similarity_search in a manual OpenTelemetry span.

    Why this is needed:
    Langfuse (via its CallbackHandler) automatically traces LLM invocations and
    LangChain sequences, but it does NOT catch raw backend operations like this
    Chroma database query. By adding a manual OTel span here, we can measure
    the exact DB-level latency separately from the LLM processing time.
    """
    from .telemetry import tracer

    vectorstore = get_vectorstore()

    with tracer.start_as_current_span("vector_db_search") as span:
        span.set_attribute("query", question)
        span.set_attribute("k", k)
        return vectorstore.similarity_search(question, k=k)


if __name__ == "__main__":
    prepare_and_store_documents()
