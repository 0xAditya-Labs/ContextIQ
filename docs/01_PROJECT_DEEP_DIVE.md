# ContextIQ — Complete Deep-Dive Documentation
> For someone understanding the project **from scratch**, in full depth.

---

## Table of Contents
1. [What is ContextIQ? (The Problem & The Vision)](#1-what-is-contextiq)
2. [Why ReAct Agent instead of plain RAG?](#2-why-react-agent-not-plain-rag)
3. [Full Architecture — Layer by Layer](#3-full-architecture)
4. [File Structure — Every File Explained](#4-file-structure)
5. [Key Design Patterns Used](#5-design-patterns)
6. [Observability Stack](#6-observability-stack)
7. [A/B Testing & Config-Driven Design](#7-ab-testing--config-driven-design)
8. [Deployment Strategy](#8-deployment-strategy)
9. [Code Issues / Messy Parts To Clean](#9-code-issues--messy-parts)

---

## 1. What is ContextIQ?

### The Real-World Problem
In large enterprises like Accenture, IT helpdesk teams are flooded with repetitive tickets:
- "How do I reset my VPN password?"
- "My laptop won't connect to the office WiFi."
- "Timesheet portal is throwing a login error."

A naïve solution would be a simple chatbot that searches a knowledge base. But naïve chatbots have two critical production problems:
1. **Hallucination on out-of-scope questions** — Ask it "What is the capital of France?" and it will happily answer, burning tokens and trust.
2. **Token waste** — Every query hits the vector DB and the LLM, even for irrelevant questions.

### The ContextIQ Solution
ContextIQ is an **agentic IT support system** that thinks before it acts:
- It uses a **LangGraph ReAct agent** with a strict system prompt defining 8 IT categories.
- If the query is in-scope → it calls the `it_support_lookup` tool → which runs a RAG pipeline → ChromaDB similarity search → LLM answer.
- If the query is out-of-scope → the agent rejects it **immediately**, without ever touching the vector DB or burning any LLM tokens on retrieval.

### Tech Stack at a Glance
| Layer | Technology |
|---|---|
| Agent Framework | LangGraph (ReAct) |
| LLM (switchable) | Gemini Flash / Llama 3.1 8B via Groq |
| Vector DB | ChromaDB (persistent, local) |
| Embeddings | Google text-embedding-004 (REST v1) / HuggingFace MiniLM |
| Backend API | FastAPI + Uvicorn |
| Observability (LLM) | Langfuse |
| Observability (Infra) | OpenTelemetry (OTel) |
| Frontend | React + Vite |
| Deployment | Vercel (frontend) + Render (backend) |

---

## 2. Why ReAct Agent, Not Plain RAG?

This is the **most important architectural decision** in the project. Understanding this is the core of everything.

### What is Standard RAG?
```
User Query → Embed Query → Similarity Search in Vector DB → Stuff Context into LLM Prompt → Answer
```
**Problem:** Every single query, regardless of topic, hits the vector DB and the LLM. There is no gating. Ask "Who is Elon Musk?" and it will still search the IT tickets database, find some irrelevant chunks, and hallucinate an answer.

### What is a ReAct Agent?
ReAct stands for **Reasoning + Acting**. The agent:
1. **Reasons** about the input — reads the system prompt and tool descriptions.
2. **Decides** whether to use a tool or not.
3. **Acts** by calling the tool (or refusing to).
4. **Observes** the tool result and forms a final answer.

```
User Query
    ↓
LangGraph ReAct Agent (reads system prompt with 8 IT categories)
    ↓
    ├── [Out-of-scope] → Immediate rejection message (no DB call, no token burn)
    └── [In-scope]    → calls it_support_lookup tool
                            ↓
                        RAG Chain (retrieval_strategies.py)
                            ↓
                        ChromaDB similarity search
                            ↓
                        LLM generates answer from context
                            ↓
                        Final answer returned to user
```

### The "Doc-String Tool-Gating" Mechanism (Key Resume Point)
The tool `it_support_lookup` is defined as a `StructuredTool` with a **description loaded from `.env`**. The agent's LLM reads this description to decide when to call the tool. The system prompt further reinforces the 8-category restriction. This double-layer of gating (system prompt + tool docstring) is what suppresses out-of-scope API calls.

---

## 3. Full Architecture

### Data Flow — Happy Path (IT Question)
```
[React Frontend]
    │  POST /query { "question": "VPN keeps failing" }
    ↓
[FastAPI /query route]  (routes.py)
    │  Creates agent, attaches Langfuse callback
    ↓
[LangGraph ReAct Agent]  (agent.py)
    │  Reads system prompt → decides to call tool
    ↓
[it_support_lookup tool]  (agent.py → rag_chain.py)
    │  Calls ask_question()
    ↓
[RetrievalStrategy]  (retrieval_strategies.py)
    │  Either MetadataChunkStrategy or ParentDocumentStrategy
    ↓
[perform_similarity_search()]  (vectorstore.py)
    │  Wrapped in OTel span for latency measurement
    ↓
[ChromaDB]  (chroma_db/ directory)
    │  Returns top-K similar ticket chunks
    ↓
[LLM via llm_factory.py]  (Gemini or Groq)
    │  Generates answer using retrieved context
    ↓
[FastAPI response]  { "answer": "...", "sources": [] }
    ↓
[React Frontend displays answer]
```

### Data Flow — Rejection Path (Non-IT Question)
```
[React Frontend]
    │  POST /query { "question": "What is the capital of France?" }
    ↓
[FastAPI /query route]
    ↓
[LangGraph ReAct Agent]
    │  Reads system prompt → NOT in 8 categories → NO tool call
    ↓
[Agent returns fixed rejection message]  (no DB, no extra LLM cost beyond the decision)
    ↓
[FastAPI response]  { "answer": "I'm sorry, I can only assist with..." }
```

---

## 4. File Structure

```
ContextIQ/
├── backend/
│   ├── app/
│   │   ├── main.py                  ← FastAPI app entry point
│   │   ├── config.py                ← Settings class (all env vars in one place)
│   │   ├── api/
│   │   │   └── routes.py            ← API endpoint definitions (/health, /query)
│   │   ├── core/
│   │   │   ├── agent.py             ← LangGraph ReAct agent + system prompt
│   │   │   ├── llm_factory.py       ← Factory: returns Gemini or Groq LLM
│   │   │   ├── rag_chain.py         ← Orchestrates retrieval + LLM prompting
│   │   │   ├── retrieval_strategies.py ← Strategy pattern: MetadataChunk vs ParentDocument
│   │   │   ├── telemetry.py         ← Langfuse + OpenTelemetry setup
│   │   │   ├── ticket_parser.py     ← Parses raw .txt file into structured dicts
│   │   │   └── vectorstore.py       ← ChromaDB singleton + embedding + search
│   │   ├── data/
│   │   │   └── dummy_it_tickets.txt ← The raw knowledge base (IT tickets)
│   │   └── models/
│   │       └── schemas.py           ← Pydantic models (QueryRequest, QueryResponse)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx                  ← Root component: state, theme, wakeup ping
│       ├── api/
│       │   └── client.js            ← sendQuery() function (fetch wrapper)
│       └── components/
│           ├── ChatWindow.jsx       ← Renders message list, auto-scrolls
│           ├── InputBox.jsx         ← Controlled input form
│           └── MessageBubble.jsx    ← Single message bubble (user vs assistant)
├── docs/assets/                     ← Screenshots for README
├── README.md
└── .gitignore
```

---

### Every File Explained in Detail

#### `backend/app/main.py` — The App Entry Point
- Creates the FastAPI application instance.
- Registers CORS middleware (allows the React frontend on a different port/domain to call the API).
- Has a **`@app.on_event("startup")` hook**: on Render (cloud), the `chroma_db/` folder doesn't exist (it's in `.gitignore`). This hook detects that and **auto-ingests** the dummy tickets on first startup. On subsequent restarts, it skips ingestion.
- Attaches the API router from `routes.py`.

#### `backend/app/config.py` — Settings / Config
- A `Settings` class that reads **all** environment variables from `.env` in one place.
- Uses `dotenv` with `override=True` so `.env` always wins over cached terminal variables.
- Key settings: `LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `DEFAULT_RETRIEVAL_STRATEGY`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `K_RESULTS`, `TOOL_DESCRIPTION`, `RAG_SYSTEM_PROMPT`.
- A single `settings` object is imported everywhere — this is the **Single Source of Truth** pattern.

#### `backend/app/api/routes.py` — API Routes
- Defines two endpoints:
  - `GET /health` → returns `{"status": "ok"}`. Used by the frontend's wakeup ping.
  - `POST /query` → accepts `QueryRequest` (Pydantic model), creates the agent, invokes it, and returns `QueryResponse`.
- **Known issue**: `create_it_agent()` is called fresh on every request (not cached). This creates a new agent object every time but re-uses the singleton LLM/DB connections underneath.

#### `backend/app/core/agent.py` — The Brain
- Defines the `AGENT_SYSTEM_PROMPT` string: 8 strict IT categories + absolute rules.
- Creates `it_support_lookup` as a `StructuredTool` whose description is loaded from `settings.TOOL_DESCRIPTION` (making it A/B testable without code changes).
- `create_it_agent()` calls `create_react_agent(llm, tools, prompt=AGENT_SYSTEM_PROMPT)` from LangGraph.
- `recursion_limit=8` prevents infinite agent loops (each tool call = 2 recursion steps, so limit=8 means max 4 tool calls).
- `run_agent_verbose()` is a dev/testing helper that streams events and prints intermediate steps.

#### `backend/app/core/llm_factory.py` — LLM Factory
- `get_llm()` reads `LLM_PROVIDER` from config.
- If `"groq"` → returns `ChatGroq` with `llama-3.1-8b-instant`, `temperature=0`.
- If `"gemini"` → returns `ChatGoogleGenerativeAI` with `gemini-3.5-flash`, and sets up a **fallback LLM** (second API key) using `.with_fallbacks()`. This means if the primary key hits a rate limit, it automatically retries with the backup key.
- `temperature=0` ensures deterministic, factual answers (no creative variation).

#### `backend/app/core/rag_chain.py` — RAG Orchestrator
- `ask_question(question, strategy_name=None)` is the main function.
- Resolves the strategy from config (or override per-call for A/B testing).
- Gets vectorstore and ticket_lookup from their respective singletons.
- Calls `strategy.retrieve()` to get context + source ticket IDs.
- Builds the prompt using `PromptTemplate` loaded from the `RAG_SYSTEM_PROMPT` env var.
- Calls `llm.invoke(prompt_value)` and wraps errors gracefully.
- Returns a structured dict: `{answer, sources, categories, strategy_used}`.

#### `backend/app/core/retrieval_strategies.py` — Strategy Pattern
- Defines an abstract `RetrievalStrategy` ABC with a `retrieve()` method.
- **`MetadataChunkStrategy`**: returns the raw text chunks from similarity search. Fast, token-efficient, but may miss broader context.
- **`ParentDocumentStrategy`**: uses chunk search to find ticket IDs, then fetches the **entire parent ticket** from `ticket_lookup`. Better context, more tokens.
- `get_strategy(name)` is a factory function that instantiates the right one.
- This pattern means you can add a third strategy (e.g. `HybridBM25Strategy`) without touching any other file.

#### `backend/app/core/vectorstore.py` — ChromaDB + Embeddings
- **`GoogleRestEmbeddings`**: A custom class that calls the Google Generative AI REST API on the **stable v1 endpoint** directly (not through the SDK). This was necessary because the `langchain_google_genai` SDK was routing embedding calls through `v1beta`, where `text-embedding-004` is unavailable (404 error). This is a genuine bug workaround.
- **`ChromaDBSingleton`**: Implements the Singleton pattern for both the ChromaDB client and the embeddings model. Prevents repeated disk I/O and model re-loading on every request.
- `prepare_and_store_documents()`: The ingestion pipeline — parse → chunk → embed → store.
- `get_ticket_lookup()`: Lazy-loads a dict of `{ticket_id: full_text}` for `ParentDocumentStrategy`.
- `perform_similarity_search()`: Wraps ChromaDB's `similarity_search` in an **OTel span** for latency measurement.

#### `backend/app/core/telemetry.py` — Observability
- `get_langfuse_handler()`: Creates a Langfuse `CallbackHandler`. Only initializes if keys are set in `.env` (graceful degradation).
- `setup_opentelemetry()`: Creates an OTel `TracerProvider` and a `BatchSpanProcessor` that writes spans to a file (`otel_traces.log`) instead of stdout (cleaner terminal).
- Registers `atexit` to flush and shut down cleanly.
- The module-level `tracer = setup_opentelemetry()` means OTel is initialized **once** at import time (Singleton behavior).

#### `backend/app/core/ticket_parser.py` — Data Ingestion
- `parse_tickets(filepath)`: Reads the raw `.txt` file, splits by blank lines (each ticket is a block), and parses key-value pairs (`Ticket ID:`, `Category:`, `Issue:`, `Resolution:`).
- Handles Windows (`\r\n`) and Unix (`\n`) line endings.
- Returns a list of dicts: `[{ticket_id, category, issue, resolution, full_text}]`.

#### `backend/app/data/dummy_it_tickets.txt` — Knowledge Base
- The raw data source. Contains structured IT support tickets in plain text format.
- Each ticket has a Ticket ID, Category, Issue, and Resolution.
- This is the only "database" the RAG system knows about.

#### `backend/app/models/schemas.py` — Pydantic Models
- `QueryRequest`: `{ question: str }` — what the frontend sends.
- `QueryResponse`: `{ answer: str, sources: Optional[List[str]] }` — what the backend returns.
- Pydantic handles automatic JSON validation, serialization, and OpenAPI schema generation.

#### `frontend/src/App.jsx` — Root Component
- Manages global state: `messages` array and `isLoading` boolean.
- **Wakeup ping**: On mount (`useEffect([], [])`), fires a `GET /health` to wake up the Render backend (which spins down after 15 minutes idle on free tier).
- **Theme toggle**: Switches `data-theme` attribute on `<html>` between `"dark"` and `"light"` for CSS variable switching.
- `handleSendMessage()`: Appends user message immediately (optimistic UI), calls `sendQuery()`, then appends the AI response.

#### `frontend/src/api/client.js` — API Client
- `sendQuery(question)`: A simple `fetch` wrapper that POSTs to `/query` and returns parsed JSON.
- Handles errors gracefully: returns a safe fallback message instead of crashing the UI.
- `API_BASE_URL` comes from `VITE_API_URL` env var (set in Vercel), defaulting to `localhost:8000` for local dev.

#### `frontend/src/components/ChatWindow.jsx` — Message List
- Renders all messages using `MessageBubble` components.
- Uses `useRef` + `useEffect` to auto-scroll to the bottom after every new message (`bottomRef.current?.scrollIntoView({ behavior: 'smooth' })`).
- Shows an empty-state welcome message when `messages.length === 0`.

#### `frontend/src/components/MessageBubble.jsx` — Single Message
- Renders a single chat bubble. Applies different CSS classes for user vs assistant messages.
- If the message has `sources`, renders them as a list below the answer.

#### `frontend/src/components/InputBox.jsx` — Input Form
- Controlled component: `text` state updates on every keystroke.
- On submit: prevents page reload, calls `onSend(text.trim())`, clears input.
- Disabled while `isLoading` is true.

---

## 5. Design Patterns

| Pattern | Where Used | Why |
|---|---|---|
| **Singleton** | `ChromaDBSingleton` (vectorstore.py), `tracer` (telemetry.py) | Prevents repeated disk I/O and model loading; avoids TracerProvider memory leak |
| **Strategy** | `RetrievalStrategy` ABC + `MetadataChunkStrategy` / `ParentDocumentStrategy` | Swap retrieval algorithms at runtime without changing RAG chain code |
| **Factory** | `get_llm()` (llm_factory.py), `get_strategy()` (retrieval_strategies.py) | Decouple object creation from usage; enables hot-swapping |
| **Dependency Injection** | `ask_question(strategy_name=None)` in rag_chain.py | Good defaults in prod, explicit overrides in tests — best of both worlds |
| **Config-Driven / 12-Factor** | `config.py` + `.env` | All behavior controlled by environment — no code changes needed for A/B tests |
| **ReAct (Reasoning + Acting)** | LangGraph agent in agent.py | Agent thinks before acting; rejects out-of-scope queries without touching DB |

---

## 6. Observability Stack

### Two Layers of Observability (This is Key)

#### Layer 1: Langfuse (LLM Application Layer)
- **What it tracks**: LLM token usage, prompt content, response latency, agent reasoning traces.
- **How it works**: `CallbackHandler` is passed in `config={"callbacks": [langfuse_handler]}` to the agent's `.invoke()` call. LangChain automatically fires events (chain start, LLM start, tool call, chain end) to Langfuse.
- **Limitation**: Langfuse only sees what happens *inside* LangChain. It is **blind** to raw database operations.

#### Layer 2: OpenTelemetry (Infrastructure Layer)
- **What it tracks**: Exact vector DB latency — how long ChromaDB takes to perform the similarity search, independent of the LLM.
- **How it works**: `perform_similarity_search()` manually wraps the `similarity_search()` call in `with tracer.start_as_current_span("vector_db_search")`. This creates a span with the query text and K value as attributes.
- **Why this matters**: OTel lets you separate "was the response slow because of the LLM?" from "was it slow because ChromaDB was slow?" This is the kind of observability that matters in production.
- **Singleton fix**: The `TracerProvider` is created once at module import time. Without this, every FastAPI request that imported `telemetry.py` could have registered a new provider, causing memory leaks.

---

## 7. A/B Testing & Config-Driven Design

Everything configurable via `.env` — **zero code changes required**:

```
# Switch LLM
LLM_PROVIDER=groq              # or gemini

# Switch Retrieval Strategy
DEFAULT_RETRIEVAL_STRATEGY=parent_document   # or metadata_chunk

# Switch Embeddings
EMBEDDING_PROVIDER=google      # or huggingface

# Tune Chunking
CHUNK_SIZE=400
CHUNK_OVERLAP=50
K_RESULTS=3

# A/B test tool descriptions (this is the "doc-string tool-gating")
TOOL_DESCRIPTION=Use this tool ONLY for VPN, passwords, timesheets...
RAG_SYSTEM_PROMPT=You are an IT support AI...
```

---

## 8. Deployment Strategy

### Backend → Render (Free Tier)
- Free tier **spins down** after 15 min of inactivity.
- `chroma_db/` is in `.gitignore` → Render doesn't have it on first deploy.
- **Solution**: `startup_event` in `main.py` auto-ingests tickets if `chroma_db/` doesn't exist.
- Cold start: ~50-90 seconds (spin-up + ingestion).

### Frontend → Vercel
- `VITE_API_URL` env var points to the Render backend URL.
- **Wakeup ping**: `App.jsx` fires `GET /health` on page load → starts warming up the Render backend before the user even types a question.

---

## 9. Code Issues / Messy Parts To Clean

### 🔴 High Priority
1. **`create_it_agent()` called on every request** in `routes.py` (line 15):
   ```python
   agent = create_it_agent()  # This runs on EVERY POST /query
   ```
   The agent itself should be created once at startup and reused. The per-request overhead is small but unnecessary. **Fix**: Initialize agent at module level or in the startup event.

2. **`allow_origins=["*"]`** in `main.py` (line 34):
   In production, this should be the exact Vercel URL, e.g.:
   ```python
   allow_origins=["https://context-iq-frontend-seven.vercel.app"]
   ```

3. **`llm = get_llm()` called at module level** in both `agent.py` (line 9) AND `rag_chain.py` (line 8):
   This means two LLM instances are created at import time. Both should use the same singleton instance.

### 🟡 Medium Priority
4. **`routes.py` ignores the structured response from `rag_chain.py`**: `ask_question()` returns `{answer, sources, categories, strategy_used}` but `routes.py` calls `agent.invoke()` directly (bypassing `rag_chain`) and returns `sources=[]`. The rich source/category data from the RAG chain is never surfaced to the frontend.

5. **`otel_traces.log` file handle**: The file is opened in `telemetry.py` and never explicitly closed (only via `atexit`). A `contextlib.ExitStack` or `with` block would be cleaner.

6. **`.env` file is committed** (`backend/.env` appears in the file tree). This must be confirmed gitignored. Check `.gitignore` includes `.env`.

### 🟢 Low Priority / Quick Wins
7. **No `__init__.py` files** in `app/core/`, `app/api/` etc. — Python finds modules fine with the `app.` prefix pattern, but adding them makes imports explicit.
8. **`schemas.py`** has `sources: Optional[List[str]] = []` — this should be `sources: List[str] = []` in Pydantic v2 (the `Optional` wrapper is redundant when a default is given).
9. **Frontend error state** in `ChatWindow.jsx` has no visual error differentiation — an error message looks the same as a normal assistant message.

