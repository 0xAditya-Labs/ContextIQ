from fastapi import APIRouter
from app.models.schemas import QueryRequest, QueryResponse
from app.core.agent import create_it_agent
from app.core.telemetry import get_langfuse_handler

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

@router.post("/query", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    # Initialize the agent
    agent = create_it_agent()
    
    # Configure Langfuse tracking
    callbacks = []
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        callbacks.append(langfuse_handler)
        
    # Execute the agent
    response = agent.invoke(
        {"messages": [("user", request.question)]},
        config={"callbacks": callbacks}
    )
    
    # Extract the final AI message content
    final_answer = response["messages"][-1].content
    
    # Handle cases where Gemini returns a list of blocks instead of a plain string
    if isinstance(final_answer, list):
        final_answer = " ".join([part.get("text", "") for part in final_answer if isinstance(part, dict) and "text" in part])
    
    return QueryResponse(answer=final_answer, sources=[])
