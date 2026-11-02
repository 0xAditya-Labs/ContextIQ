"""
ContextIQ — FastAPI Application Entry Point
============================================
Responsibilities:
  1. Configure structured logging (replaces print() across the codebase).
  2. Register CORS middleware (env-var driven, not hardcoded "*").
  3. Auto-ingest the vector database on cold deploy (chroma_db/ is gitignored).
  4. Mount all API routes.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings

# ── Logging setup ──────────────────────────────────────────────────────────────
# Configure before any other import that might log.
# LOG_LEVEL is read from env so production can suppress debug noise with
#   LOG_LEVEL=WARNING
# without any code changes.
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("contextiq.main")

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ContextIQ IT Support API",
    description=(
        "Scope-gated LangGraph ReAct agent for enterprise IT support. "
        "See /docs for interactive API documentation."
    ),
    version="1.0.0",
)


# ── Startup: auto-ingest ChromaDB if missing ───────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """
    On Render (and any fresh clone), chroma_db/ does not exist because it is
    gitignored. This hook detects the missing directory and runs the full
    ingestion pipeline automatically so the service is self-healing on first deploy.

    On subsequent restarts the existing DB is reused — ingestion is skipped.
    """
    current_dir = os.path.dirname(__file__)
    db_path = os.path.join(current_dir, "..", "chroma_db")

    if not os.path.exists(db_path):
        logger.info("chroma_db/ not found — running first-time ingestion...")
        from app.core.vectorstore import prepare_and_store_documents
        prepare_and_store_documents()
        logger.info("Ingestion complete. Vector store is ready.")
    else:
        logger.info("chroma_db/ found — skipping ingestion.")


# ── CORS ───────────────────────────────────────────────────────────────────────
# allow_origins is driven by CORS_ORIGINS env var (see config.py).
# Defaults to ["*"] for local dev. In production set:
#   CORS_ORIGINS=https://context-iq-frontend-seven.vercel.app
#
# Why CORS is needed:
# Browsers block cross-origin requests by default. The React app on Vercel
# (port 443) calling the FastAPI backend on Render (different domain) triggers
# this. CORSMiddleware adds the Access-Control-Allow-Origin header so the
# browser permits the request.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────
app.include_router(router)

logger.info(
    f"ContextIQ starting | LLM={settings.LLM_PROVIDER} | "
    f"Embeddings={settings.EMBEDDING_PROVIDER} | "
    f"Strategy={settings.DEFAULT_RETRIEVAL_STRATEGY} | "
    f"CORS={settings.CORS_ORIGINS}"
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
