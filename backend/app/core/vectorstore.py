import os
import chromadb
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from .ticket_parser import parse_tickets

class ChromaDBSingleton:
    _instance = None

    @classmethod
    def get_client(cls):
        # SINGLETON PATTERN: avoids re-initializing DB client on every call, 
        # which causes repeated disk I/O and slow cold-starts.
        if cls._instance is None:
            # We initialize the PersistentClient. 
            # Note: newer chromadb uses `path` rather than `persist_directory`.
            cls._instance = chromadb.PersistentClient(path="./chroma_db")
        return cls._instance

def prepare_and_store_documents():
    """
    Reads the dummy IT tickets using ticket_parser, chunks the text while preserving 
    ticket_id in metadata, creates embeddings, and stores them into ChromaDB.
    
    Returns:
        dict: A lookup mapping ticket_id to its full_text.
    """
    
    # 1. Parse tickets
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "..", "data", "dummy_it_tickets.txt")
    
    print(f"Loading and parsing documents from {file_path}...")
    parsed_tickets = parse_tickets(file_path)
    
    # Create Document objects with metadata
    documents = []
    ticket_lookup = {}
    
    for ticket in parsed_tickets:
        doc = Document(
            page_content=ticket["full_text"],
            metadata={
                "ticket_id": ticket["ticket_id"],
                "category": ticket["category"]
            }
        )
        documents.append(doc)
        ticket_lookup[ticket["ticket_id"]] = ticket["full_text"]

    # 2. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)

    # 3. Embeddings
    print("Initializing embeddings model (this runs locally, no API cost)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # 4. Store in Vector Database (ChromaDB)
    chroma_client = ChromaDBSingleton.get_client()
    
    print("Storing chunks into ChromaDB...")
    vectorstore = Chroma(
        client=chroma_client,
        collection_name="it_tickets_collection",
        embedding_function=embeddings,
    )
    
    # Add the chunks into the vector database
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
        file_path = os.path.join(current_dir, "..", "data", "dummy_it_tickets.txt")
        parsed_tickets = parse_tickets(file_path)
        _ticket_lookup_cache = {t["ticket_id"]: t["full_text"] for t in parsed_tickets}
    return _ticket_lookup_cache

def get_vectorstore():
    """
    Returns the initialized Chroma vectorstore object.
    """
    chroma_client = ChromaDBSingleton.get_client()
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    return Chroma(
        client=chroma_client,
        collection_name="it_tickets_collection",
        embedding_function=embeddings,
    )

if __name__ == "__main__":
    prepare_and_store_documents()
