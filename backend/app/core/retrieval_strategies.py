from abc import ABC, abstractmethod

class RetrievalStrategy(ABC):
    """
    Abstract base class for retrieval strategies (Strategy design pattern).
    This allows us to interchange retrieval algorithms dynamically without 
    modifying the core RAG execution code.
    """
    
    @abstractmethod
    def retrieve(self, question: str, vectorstore, ticket_lookup: dict) -> dict:
        """
        Executes the retrieval logic.
        
        Args:
            question (str): The user's query.
            vectorstore: The initialized ChromaDB vectorstore.
            ticket_lookup (dict): A mapping of ticket_id to full ticket text.
            
        Returns:
            dict: {"context": str, "source_ticket_ids": list[str]}
        """
        pass

from app.config import settings
from .vectorstore import perform_similarity_search

class MetadataChunkStrategy(RetrievalStrategy):
    """
    Retrieves the most similar raw chunks and returns them directly as context.
    Pros: Faster, uses less context window.
    Cons: Might lose broader context surrounding the chunk.
    """
    def retrieve(self, question: str, vectorstore, ticket_lookup: dict) -> dict:
        # Perform similarity search to get top K chunks using our OTel-traced wrapper
        chunks = perform_similarity_search(question, k=settings.K_RESULTS)
        
        # Combine the chunk text as context
        context = "\n\n".join([chunk.page_content for chunk in chunks])
        
        # Extract unique source ticket IDs and categories from the chunk metadata
        source_ticket_ids = list(set([
            chunk.metadata.get("ticket_id") 
            for chunk in chunks 
            if chunk.metadata.get("ticket_id")
        ]))
        
        source_categories = list(set([
            chunk.metadata.get("category")
            for chunk in chunks
            if chunk.metadata.get("category")
        ]))
        
        return {
            "context": context,
            "source_ticket_ids": source_ticket_ids,
            "source_categories": source_categories
        }

class ParentDocumentStrategy(RetrievalStrategy):
    """
    Retrieves similar chunks, but then returns the *entire parent ticket* as context.
    Pros: LLM sees the complete ticket, reducing hallucinations and missed details.
    Cons: Consumes more context window, potentially slower generation.
    """
    def retrieve(self, question: str, vectorstore, ticket_lookup: dict) -> dict:
        # Perform similarity search to get top K chunks using our OTel-traced wrapper
        chunks = perform_similarity_search(question, k=settings.K_RESULTS)
        
        # Extract unique source ticket IDs and categories
        source_ticket_ids = list(set([
            chunk.metadata.get("ticket_id") 
            for chunk in chunks 
            if chunk.metadata.get("ticket_id")
        ]))
        
        source_categories = list(set([
            chunk.metadata.get("category")
            for chunk in chunks
            if chunk.metadata.get("category")
        ]))
        
        # Fetch the FULL text for those tickets from the lookup dictionary
        # This replaces the chunked snippet with the complete ticket.
        full_texts = [
            ticket_lookup[ticket_id] 
            for ticket_id in source_ticket_ids 
            if ticket_id in ticket_lookup
        ]
        
        # Combine the full ticket texts as context
        context = "\n\n---\n\n".join(full_texts)
        
        return {
            "context": context,
            "source_ticket_ids": source_ticket_ids,
            "source_categories": source_categories
        }

def get_strategy(strategy_name: str) -> RetrievalStrategy:
    """
    Factory function to instantiate the requested strategy.
    """
    if strategy_name == "metadata_chunk":
        return MetadataChunkStrategy()
    elif strategy_name == "parent_document":
        return ParentDocumentStrategy()
    else:
        raise ValueError(f"Unknown retrieval strategy: '{strategy_name}'. "
                         "Valid options are: 'metadata_chunk', 'parent_document'")
