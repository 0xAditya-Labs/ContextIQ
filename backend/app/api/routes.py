"""
ContextIQ — API Routes
=======================
Defines all HTTP endpoints. Key design decisions:

1. Agent is compiled ONCE at module level (_agent) — LangGraph graph compilation
   is not free; caching it avoids repeated work on every request.

2. /metrics endpoint exposes an in-memory view of rejection rate and latency —
   these are the numbers that back the resume bullets.

3. /history endpoint keeps a rolling window of the last 50 queries for
   observability during testing and A/B experiments.

4. Sources are recovered from agent.py's thread-local side-channel so the
   frontend can display which IT tickets informed each answer.

5. Request IDs (8-char UUID prefix) are logged with every line for that request,
   making it trivial to grep a single request's trace across interleaved logs.
"""

import uuid
import time
import logging
from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter
from app.models.schemas import QueryRequest, QueryResponse
from app.core.agent import create_it_agent, get_last_sources
from app.core.telemetry import get_langfuse_handler
from app.core.metrics import metrics

logger = logging.getLogger("contextiq.routes")

router = APIRouter()

# ── Agent singleton ────────────────────────────────────────────────────────────
# create_it_agent() compiles the LangGraph graph. This runs once at import time.
# All requests share this compiled graph — it is stateless between calls.
_agent = create_it_agent()

# Marker string the agent uses when it rejects an out-of-scope query
_REJECTION_MARKER = "I'm sorry, I can only assist with"

# ── Query history (rolling window) ────────────────────────────────────────────
_query_history: deque = deque(maxlen=50)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    """Liveness probe. Also used by the React frontend as a cold-start wakeup ping."""
    return {"status": "ok"}


@router.get("/metrics")
def get_metrics():
    """
    Returns live in-memory stats: total requests, rejection rate, and avg latency.
    Use this endpoint after running the benchmark scripts to read the numbers that
    back the resume bullets.
    """
    return metrics.summary()


@router.post("/metrics/reset")
def reset_metrics():
    """
    Resets all counters to zero. Call this between benchmark runs to get clean data.
    """
    metrics.reset()
    return {"status": "reset", "message": "All counters cleared."}


@router.get("/history")
def get_history():
    """
    Returns the last 50 query-answer pairs (in-memory, resets on server restart).
    Useful for reviewing A/B test results without opening Langfuse.
    """
    return list(_query_history)


@router.post("/query", response_model=QueryResponse)
def query_agent(request: QueryRequest):
    # Short request ID for log correlation — grep this to trace one request
    req_id = str(uuid.uuid4())[:8]
    logger.info(f"[{req_id}] Query received: {request.question[:60]!r}")

    # Attach Langfuse callback if credentials are configured
    callbacks = []
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        callbacks.append(langfuse_handler)

    # Invoke the cached agent and time the full round-trip
    t_start = time.perf_counter()
    response = _agent.invoke(
        {"messages": [("user", request.question)]},
        config={
            "recursion_limit": 8,
            "callbacks": callbacks,
        },
    )
    latency_ms = (time.perf_counter() - t_start) * 1000

    # Extract the final AI message content
    final_answer = response["messages"][-1].content

    # Gemini sometimes returns a list of content blocks instead of a plain string
    if isinstance(final_answer, list):
        final_answer = " ".join(
            part.get("text", "")
            for part in final_answer
            if isinstance(part, dict) and "text" in part
        )

    # Determine if the agent rejected the query (no tool call made)
    was_rejected = _REJECTION_MARKER in final_answer

    # Record into in-memory metrics for /metrics endpoint
    metrics.record(latency_ms=latency_ms, was_rejected=was_rejected)

    # Retrieve source ticket IDs captured by the tool's thread-local side-channel
    # Returns [] if agent rejected without calling the tool
    sources = get_last_sources()

    logger.info(
        f"[{req_id}] Done | latency={latency_ms:.0f}ms | "
        f"rejected={was_rejected} | sources={sources}"
    )

    # Append to rolling history for /history endpoint
    _query_history.append({
        "request_id": req_id,
        "question": request.question,
        "answer": final_answer,
        "sources": sources,
        "latency_ms": round(latency_ms, 1),
        "was_rejected": was_rejected,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return QueryResponse(answer=final_answer, sources=sources)
