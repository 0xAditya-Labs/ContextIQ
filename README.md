<div align="center">
  <h1>🧠 ContextIQ</h1>
  <p><strong>A scope-gated, agentic IT support system — built to benchmark retrieval strategies and prove that query rejection is a feature, not a fallback.</strong></p>

  [![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
  [![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://reactjs.org/)
  [![LangGraph](https://img.shields.io/badge/LangGraph-1C1C1C?style=for-the-badge)](https://langchain.com/)
  [![ChromaDB](https://img.shields.io/badge/ChromaDB-FF6F00?style=for-the-badge)](https://www.trychroma.com/)
  [![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-425CC7?style=for-the-badge&logo=opentelemetry&logoColor=white)](https://opentelemetry.io/)
  [![Langfuse](https://img.shields.io/badge/Langfuse-000000?style=for-the-badge)](https://langfuse.com/)
</div>

<div align="center">
  <b><a href="https://context-iq-frontend-seven.vercel.app/">🌐 Live Demo</a></b> &nbsp;|&nbsp;
  <b><a href="https://youtu.be/iB0DpAtEWZA?si=DufV_p64cXk-fUmC">🎥 Video Demo</a></b> &nbsp;|&nbsp;
  <b><a href="https://docs.google.com/presentation/d/1YjKR_LsQPGX68dEUOVmqeWUsBH6sl-gq/edit?usp=sharing&ouid=105688022393717157912&rtpof=true&sd=true">📊 Architecture Deck</a></b>
</div>

---

## The Problem with Naive RAG

Standard RAG pipelines have a fundamental design flaw for scoped domains: they are unconditionally eager. Every query — regardless of whether it's "my VPN keeps disconnecting" or "who won the World Cup?" — pays the full cost: an embedding call, a vector DB lookup, a retrieval pass, and a full LLM generation. The result is wasted tokens on irrelevant queries and hallucinations when retrieved context doesn't match the question.

**ContextIQ's answer:** treat query rejection as a first-class architectural concern.

---

## What ContextIQ Does Differently

ContextIQ is a **LangGraph ReAct agent** that reasons before it retrieves. It evaluates every query against a strict scope gate (8 enterprise IT categories) before deciding whether to invoke the RAG pipeline. Out-of-scope queries are rejected immediately — zero vector DB calls, zero additional token spend on retrieval.

```
Query → Agent Reasons → [In-scope]  → it_support_lookup tool → ChromaDB → LLM → Answer
                      → [Out-scope] → Rejection (no DB, no extra tokens)
```

This creates a measurable and observable system: token usage, rejection rate, and DB latency are all instrumented — not estimated.

---

## System Architecture

```mermaid
flowchart TD
    User["👤 Employee\n(React Frontend)"]
    API["FastAPI\n/query endpoint\n+ request-ID logging"]
    Agent["LangGraph ReAct Agent\nrecursion_limit = 8"]
    Gate{"Scope Gate\nSystem Prompt\n+ Tool Description"}
    Tool["it_support_lookup\ntool"]
    RAG["RAG Chain\nask_question()"]
    Strategy{"Retrieval Strategy\nmetadata_chunk\nparent_document"}
    Chroma["ChromaDB\nPersistentClient\n(Singleton)"]
    LLM["LLM\nGemini Flash / Groq\ntemperature = 0"]
    Reject["❌ Rejection\nno DB hit\nno extra tokens"]
    Answer["✅ Answer\n+ source ticket IDs"]
    Langfuse["Langfuse\ntoken counts\ntool decisions\nprompt traces"]
    OTel["OpenTelemetry\nvector_db_search span\notel_traces.log"]
    Metrics["SimpleMetrics\n/metrics endpoint\nrejection_rate_pct\navg_latency_ms"]

    User -->|"POST /query"| API
    API --> Agent
    Agent --> Gate
    Gate -->|"IT query"| Tool
    Gate -->|"Off-topic"| Reject
    Tool --> RAG
    RAG --> Strategy
    Strategy -->|"similarity_search"| Chroma
    Chroma -->|"top-K chunks"| Strategy
    Strategy -->|"context"| LLM
    LLM --> Answer
    Answer --> API
    API --> Metrics

    Agent -. "CallbackHandler" .-> Langfuse
    Chroma -. "OTel span" .-> OTel

    style Reject fill:#ff6b6b,color:#fff
    style Answer fill:#51cf66,color:#fff
    style Gate fill:#ffd43b,color:#333
    style OTel fill:#425CC7,color:#fff
    style Langfuse fill:#000,color:#fff
```

### Request Lifecycle (Sequence)

```mermaid
sequenceDiagram
    participant FE as React Frontend
    participant API as FastAPI /query
    participant Agent as LangGraph Agent
    participant Tool as it_support_lookup
    participant DB as ChromaDB (Singleton)
    participant LLM as Gemini / Groq
    participant LF as Langfuse
    participant OT as OTel Log

    FE->>API: POST /query {question}
    Note over API: Pydantic validates (min 3, max 500 chars)<br/>Generates 8-char request ID
    API->>Agent: invoke({messages}, callbacks=[LangfuseHandler])
    Agent-->>LF: trace starts (tokens, prompt logged)
    
    alt IT support query
        Agent->>Tool: call it_support_lookup(question)
        Tool->>DB: perform_similarity_search(question, k=3)
        DB-->>OT: vector_db_search span (start_time, end_time)
        DB-->>Tool: top-K chunks
        Tool->>LLM: prompt = context + question
        LLM-->>Tool: answer string
        Tool-->>Agent: answer (thread-local stores sources)
        Agent-->>API: final answer
        API->>API: get_last_sources() from thread-local
    else Off-topic query
        Agent-->>API: rejection message (no tool called)
        Note over API: sources = []
    end

    API->>API: metrics.record(latency_ms, was_rejected)
    API->>API: append to _query_history deque(maxlen=50)
    Agent-->>LF: trace ends (input/output tokens recorded)
    API-->>FE: {answer, sources}
```

---

## Architecture

### Agent & Gating Layer

The agent is built with LangGraph's `create_react_agent`, which models the agent loop as an explicit directed graph rather than an opaque execution chain. This matters for three reasons:

1. **Inspectability** — every Thought → Action → Observation step is a discrete graph event, streamable and loggable.
2. **Hard safety** — `recursion_limit=8` prevents infinite tool-call loops at the graph level (each tool call traverses 2 edges: agent → tool → agent).
3. **Deprecation-proof** — LangChain's `AgentExecutor` is deprecated; LangGraph is the forward-compatible replacement.

The gating mechanism itself is a **double layer**:
- **System prompt** defines 8 strict IT categories and absolute rejection rules.
- **Tool description** (`TOOL_DESCRIPTION` env var) tells the LLM when the tool is applicable — the LLM reads this docstring as part of its reasoning.

Changing the tool description from `.env` without touching code is what makes tool-gating an A/B testable variable, not a hardcoded constraint.

### Retrieval Layer — Strategy Pattern

Two interchangeable retrieval strategies, selectable at runtime via env var or per-call override:

| Strategy | Mechanism | Token Cost | Context Quality |
|---|---|---|---|
| `metadata_chunk` | Returns raw top-K chunks directly | Low | May lose surrounding context |
| `parent_document` | Uses chunk to find ticket ID → fetches full ticket from in-memory dict | Higher | Full ticket context for LLM |

Both strategies share a common abstract interface (`RetrievalStrategy` ABC), so the RAG chain calls `strategy.retrieve()` without knowing which implementation it gets. Adding a third strategy (e.g., BM25 hybrid) requires zero changes to `rag_chain.py` — Open/Closed Principle applied.

The per-call override (`ask_question(q, strategy_name="parent_document")`) enables A/B testing from a notebook without restarting the server — a genuine advantage over a pure env-var switch.

### Vector Store Layer — Singleton + Custom Embeddings

**ChromaDB Singleton:** `ChromaDBSingleton` uses class-level variables to ensure the `PersistentClient` and embeddings model are initialized exactly once per process. Without this, each request would re-read from disk and re-acquire OS file locks on the ChromaDB directory — measurable overhead on every warm request.

**Custom REST Embeddings:** The `langchain_google_genai` SDK internally routes embedding requests through the `v1beta` endpoint. `text-embedding-004` is not available on `v1beta` — it returns HTTP 404. Rather than downgrading the model, `GoogleRestEmbeddings` calls the stable `v1` REST endpoint directly, implementing the two-method LangChain embeddings interface (`embed_documents`, `embed_query`) as a drop-in replacement. It also supports an automatic fallback to a secondary API key on failure.

### LLM Layer — Factory + Fallback Chain

`get_llm()` is a factory that returns either `ChatGroq` (Llama 3.1 8B) or `ChatGoogleGenerativeAI` (Gemini Flash) based on `LLM_PROVIDER`. The Gemini path is wrapped with `.with_fallbacks([secondary_llm])` — if the primary key hits a rate limit, LangChain transparently retries with the backup key. `temperature=0` on both providers ensures deterministic, fact-grounded answers.

---

## Observability

Langfuse and OpenTelemetry cover different layers of the stack — they are complementary, not redundant.

| | **Langfuse** | **OpenTelemetry** |
|---|---|---|
| **Layer** | LLM Application | Infrastructure |
| **Captures** | Agent reasoning, tool decisions, token counts, prompt latency | Raw vector DB search duration |
| **Blind to** | Database-level operations | LLM internals |
| **Attachment** | `CallbackHandler` in `agent.invoke(config={"callbacks": [...]})` | Manual span in `perform_similarity_search()` |
| **Output** | Langfuse Cloud dashboard | `otel_traces.log` file |

The OTel span around `similarity_search()` is what makes it possible to answer: *"Is the response slow because the LLM is slow, or because ChromaDB is slow?"* Without it, latency is an unattributed black box.

**OTel Singleton Note:** The `TracerProvider` is initialized at module import time (`tracer = setup_opentelemetry()`). If initialized inside a function, each request would register a new global provider without shutting down the old one — leaking `BatchSpanProcessor` background threads. Python's module import cache (`sys.modules`) ensures `setup_opentelemetry()` runs exactly once per process.

![Langfuse Trace](docs/assets/langfuse.png)
![OpenTelemetry Span](docs/assets/otel.png)

---

## A/B Testing Surface

Every behavioral variable is controllable from `.env` — no code changes required:

```bash
# Swap the LLM backend
LLM_PROVIDER=groq               # or: gemini

# Swap embeddings (cloud vs local)
EMBEDDING_PROVIDER=google       # or: huggingface

# Swap retrieval strategy
DEFAULT_RETRIEVAL_STRATEGY=parent_document  # or: metadata_chunk

# Tune chunking
CHUNK_SIZE=400
CHUNK_OVERLAP=50
K_RESULTS=3

# A/B test the gating boundary (changes agent behavior without restart)
TOOL_DESCRIPTION="Use this tool ONLY for VPN, passwords, timesheets..."

# A/B test the answer generation prompt
RAG_SYSTEM_PROMPT="You are an IT support AI. Answer based ONLY on context..."
```

Results are scored in Langfuse: token counts, latency, and prompt quality scores are logged per trace, making comparisons across strategy configurations quantitative rather than subjective.

---

## Project Structure

```
ContextIQ/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app, CORS, startup auto-ingestion hook
│   │   ├── config.py                   # Settings class — single source of truth for all env vars
│   │   ├── api/
│   │   │   └── routes.py               # /health /query /metrics /metrics/reset /history
│   │   ├── core/
│   │   │   ├── agent.py                # LangGraph ReAct agent, system prompt, tool + sources side-channel
│   │   │   ├── llm_factory.py          # Factory: Gemini or Groq with automatic fallback key chain
│   │   │   ├── metrics.py              # Thread-safe in-memory metrics (rejection_rate, avg_latency)
│   │   │   ├── rag_chain.py            # RAG orchestrator: strategy → retrieval → prompt → LLM
│   │   │   ├── retrieval_strategies.py # Strategy ABC + MetadataChunk + ParentDocument implementations
│   │   │   ├── telemetry.py            # Langfuse CallbackHandler + OTel TracerProvider (module singleton)
│   │   │   ├── ticket_parser.py        # Parses .txt knowledge base → structured dicts
│   │   │   └── vectorstore.py          # ChromaDB singleton + custom REST embeddings + OTel-traced search
│   │   ├── data/
│   │   │   └── dummy_it_tickets.txt    # Flat-file knowledge base: structured IT support tickets
│   │   └── models/
│   │       └── schemas.py              # Pydantic: QueryRequest (validated) + QueryResponse
│   ├── benchmarks/
│   │   ├── latency_test.py             # Warm vs cold ChromaDB path — measures singleton improvement %
│   │   ├── rejection_test.py           # 30 queries (15 IT + 15 off-topic) — measures rejection rate %
│   │   ├── fill_results.py             # Auto-fills BENCHMARKING_RESULTS.md from JSON + OTel log + /metrics
│   │   ├── run_benchmarks.bat          # Windows: runs all 3 scripts in order, auto-fills results doc
│   │   └── run_benchmarks.sh           # Mac/Linux: same pipeline with colour output
│   ├── tests/
│   │   └── test_ticket_parser.py       # 10 pytest cases: count, fields, CRLF, empty, FileNotFoundError
│   ├── Dockerfile                      # python:3.11-slim, non-root user, cache-friendly COPY layers
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx                     # Root: message state, theme toggle, /health wakeup ping on mount
│       ├── api/client.js               # sendQuery() — typed fetch wrapper with error normalisation
│       └── components/
│           ├── ChatWindow.jsx          # Message list with auto-scroll (useRef + useEffect)
│           ├── InputBox.jsx            # Controlled form — disabled during in-flight requests
│           └── MessageBubble.jsx       # User/assistant bubble with optional source ticket display
└── docs/assets/                        # Screenshots referenced in README
```

---

## Deployment

### Backend → Render

The backend deploys to Render's free tier with two self-healing behaviors built in:

**1. Auto-ingestion on cold deploy:** `chroma_db/` is gitignored (too large to version). On first Render deploy, it doesn't exist. The `@app.on_event("startup")` hook detects its absence and runs `prepare_and_store_documents()` automatically — parse → chunk → embed → store. Subsequent restarts skip this.

**2. Frontend wakeup ping:** Render free tier idles after 15 minutes. `App.jsx` fires `GET /health` on mount via `useEffect`. This starts the backend warm-up before the user types their first query, converting a ~50s cold-start wait into near-zero perceived latency.

```
# Render Web Service
Root Directory:  backend/
Build Command:   pip install -r requirements.txt
Start Command:   uvicorn app.main:app --host 0.0.0.0 --port 10000
```

Required environment variables on Render:
```
GOOGLE_API_KEY, GOOGLE_API_KEY_FALLBACK
GROQ_API_KEY
LLM_PROVIDER, EMBEDDING_PROVIDER
LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY
DEFAULT_RETRIEVAL_STRATEGY, CHUNK_SIZE, CHUNK_OVERLAP, K_RESULTS
TOOL_DESCRIPTION, RAG_SYSTEM_PROMPT
```

### Frontend → Vercel

```
Root Directory:  frontend/
Build Command:   npm run build
```

Set `VITE_API_URL` to your Render service URL (e.g., `https://contextiq-api.onrender.com`).

---

## Benchmarking

The performance claims in this project are measured, not estimated. Two benchmark scripts produce the numbers:

| Script | What it measures | Output |
|--------|-----------------|--------|
| `latency_test.py` | ChromaDB warm (singleton) vs cold (re-init per request) | Latency improvement %, P50/P95 ms |
| `rejection_test.py` | 15 IT + 15 off-topic queries against the live server | Rejection rate %, IT accuracy %, latency saved per rejection |

Run the full pipeline from `backend/`:
```bash
# Windows
venv\Scripts\activate
benchmarks\run_benchmarks.bat

# Mac / Linux
source venv/bin/activate
bash benchmarks/run_benchmarks.sh
```

The runner automatically:
1. Runs 10 pytest unit tests
2. Runs the latency benchmark → writes `benchmarks/results_latency.json`
3. Prompts you to start the server, then runs the rejection benchmark → writes `benchmarks/results_rejection.json`
4. Reads `/metrics` endpoint + `otel_traces.log`
5. **Auto-fills** `BENCHMARKING_RESULTS.md` with real numbers from all sources

---

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys. Then:

```bash
# First run: build the vector database from the knowledge base
python -m app.core.vectorstore

# Start the API server
python -m app.main
# → http://localhost:8000
# → Swagger UI at http://localhost:8000/docs
```

> The `chroma_db/` directory is gitignored. It must be generated locally via the ingestion step above before the agent can answer queries. On subsequent runs, the existing DB is reused.

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local` (or leave unset — it defaults to `localhost:8000`).

---

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness probe; React frontend pings this on mount to warm up Render |
| `POST` | `/query` | Main endpoint — runs the agent, returns `{answer, sources}` |
| `GET` | `/metrics` | Live stats: `total_requests`, `rejection_rate_pct`, `avg_latency_ms` |
| `POST` | `/metrics/reset` | Resets all counters — call between benchmark runs for clean data |
| `GET` | `/history` | Last 50 query-answer pairs (rolling in-memory window) |
| `GET` | `/docs` | FastAPI auto-generated Swagger UI |

---

## Design Decisions & Known Trade-offs

| Decision | Trade-off Accepted |
|---|---|
| ReAct agent over direct RAG chain | +1 LLM call per query (reasoning step); justified by token savings on rejections at scale |
| ChromaDB over managed vector DB (Pinecone) | Single-node, no horizontal scaling; appropriate for prototype scope |
| Custom REST embeddings over SDK | Tighter coupling to Google API contract; necessary to access `text-embedding-004` on stable v1 |
| Module-level OTel init over per-request | Less flexible; necessary to prevent TracerProvider memory leaks in long-running ASGI process |
| Render free tier | 50s cold starts; mitigated by frontend wakeup ping |
| `temperature=0` | Answers can feel robotic; correct trade-off for a fact-retrieval, not creative, task |

---

<div align="center">
  <i>Built during the Accenture Advanced Application Engineering Internship (AEH Batch)</i>
</div>
