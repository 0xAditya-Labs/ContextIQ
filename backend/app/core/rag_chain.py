import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Import our singleton Chroma client
from .vectorstore import ChromaDBSingleton

def prepare_and_store_documents():
    """
    Reads the dummy IT tickets, chunks the text, creates embeddings, 
    and stores them into ChromaDB using the singleton pattern.
    """
    
    # 1. Load the data
    # Locate dummy_it_tickets.txt relative to this script
    current_dir = os.path.dirname(__file__)
    file_path = os.path.join(current_dir, "..", "data", "dummy_it_tickets.txt")
    
    print(f"Loading documents from {file_path}...")
    loader = TextLoader(file_path)
    documents = loader.load()

    # 2. Chunking
    # CONCEPT: "Chunking" means taking a large document and chopping it up into smaller, bite-sized 
    # pieces (chunks) that an AI model can easily process. Large language models have a limit to 
    # how much text they can "read" at once (context window), so chunking is necessary.
    # 
    # OVERLAP: We use chunk_overlap to prevent losing context at chunk boundaries. If an important 
    # concept or sentence is split right down the middle between two chunks, having a slight overlap 
    # ensures both chunks share a bit of that context, keeping ideas intact.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50
    )
    chunks = text_splitter.split_documents(documents)

    # 3. Embeddings
    # CONCEPT: "Embeddings" translate human text into lists of numbers (vectors) that computers can 
    # mathematically compare. Sentences with similar meanings will have similar numbers. This lets 
    # the system search for information based on its actual meaning, not just exact keyword matches.
    #
    # This specific model runs locally on your machine, which means there is no API cost 
    # and your data is not sent to external servers.
    print("Initializing embeddings model (this runs locally, no API cost)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # 4. Store in Vector Database (ChromaDB)
    # We retrieve the singleton Chroma client so we don't re-initialize the DB engine pointlessly.
    chroma_client = ChromaDBSingleton.get_client()
    
    print("Storing chunks into ChromaDB...")
    # We initialize the Chroma vectorstore with our persistent client.
    # If the collection doesn't exist, it will be created.
    vectorstore = Chroma(
        client=chroma_client,
        collection_name="it_tickets_collection",
        embedding_function=embeddings,
    )
    
    # Add the chunks into the vector database
    vectorstore.add_documents(chunks)

    # 5. Print out results
    print(f"Successfully created and stored {len(chunks)} chunks!")

if __name__ == "__main__":
    prepare_and_store_documents()
