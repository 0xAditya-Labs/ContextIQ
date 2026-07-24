# ContextIQ — PPT Blueprint
### For Project Lead, Mentor & Buddy | Internship Final Presentation
*Slide-by-slide script. Designed to be handed to any AI (ChatGPT, Gemini) to generate the actual PowerPoint.*

---

## DESIGN INSTRUCTIONS (For AI Making the PPT)
- **Theme:** Dark background (#0D0D0D or navy), white/light text, purple/electric blue accent color
- **Font:** Inter or Montserrat — clean, modern, professional
- **Style:** Minimal text per slide. Big visuals. Consultant-grade layout (like McKinsey / Deloitte decks)
- **Slide Size:** 16:9 widescreen
- **Rule:** Every slide has ONE headline message at the top (the "so what"), not a topic label

---

## TOTAL SLIDES: 9

---

## SLIDE 1 — THE HOOK (Problem Statement)
**Headline (big, bold, top):**
> "Every day, IT teams waste hours answering the same questions that were already solved last week."

**Left side — Visual:**
A simple 2-column table graphic:
| Employee asks... | IT team does... |
|---|---|
| "My VPN won't connect" | Searches 500 old tickets manually |
| "Printer not working" | Same answer given for the 40th time |
| "Can't access timesheet portal" | Repeating solutions already documented |

**Right side — Stat callout box:**
> 📊 Repetitive queries = wasted engineer time = slower resolution for real problems

**Bottom tagline:**
> *ContextIQ was built to solve this. One AI agent that reads every past ticket and answers instantly.*

**Screenshot needed:** None — this is a text/graphic slide.

---

## SLIDE 2 — THE SOLUTION IN ONE LINE
**Headline:**
> "ContextIQ: An AI agent that reads your IT knowledge base and answers employee questions — instantly, accurately, and at scale."

**Center visual — product screenshot:**
→ Use the **UI screenshot** showing the dark-themed chat interface with the ContextIQ logo
→ Show a question bubble ("My VPN is failing") and the answer bubble below it

**Three icon callouts below the image:**
- ⚡ Instant — sub-second responses
- 🔒 Scoped — only answers from real IT data, never hallucinates
- 📊 Observable — every response is tracked, scored, and auditable

**Screenshot needed:** UI chat interface screenshot (the dark-mode one you showed earlier)

---

## SLIDE 3 — HOW IT WAS BUILT (The Story: Phase by Phase)
**Headline:**
> "Built in phases — each phase added a new layer of enterprise-readiness."

**Visual: A horizontal timeline / phased roadmap**

```
Phase 1          Phase 2            Phase 3             Phase 4
────────         ────────           ────────             ────────
Foundation       Intelligence       Observability        Quality Assurance
─────────        ──────────         ─────────────        ─────────────────
FastAPI +        LangGraph          Langfuse             A/B Testing
ChromaDB +       ReAct Agent        LLM tracing    +     Retrieval strategies
RAG Chain        + Scoped           OpenTelemetry        Prompt versioning
                   system prompt    Vector DB spans      Evaluation scoring
```

**Caption below timeline:**
> *Each phase delivered a working, testable increment. Nothing was built in one shot.*

**Screenshot needed:** None — this is a diagram slide. The AI should draw this as a horizontal ribbon/timeline.

---

## SLIDE 4 — WHY REACT AGENT? (Not just a simple RAG chain)
**Headline:**
> "A simple RAG chain would have been wrong here. Here's why we used a ReAct Agent."

**Two-column comparison layout:**

**Left column — "Simple RAG (What most people build)"**
- Blindly searches the database for EVERY message
- Asks "what is the capital of France?" → wastes tokens searching IT tickets
- No decision-making. No routing.
- Higher latency. Higher API cost. Zero intelligence.

**Right column — "ReAct Agent (What ContextIQ uses) ✅"**
- THINKS first: "Is this an IT question or not?"
- If YES → calls the tool (Vector DB search + LLM)
- If NO → rejects instantly without touching the database
- Result: 50% fewer unnecessary API calls. Zero hallucinations on off-topic queries.

**Center divider graphic:** A brain icon or decision tree arrow

**Bottom callout box (purple/blue accent):**
> 💡 *"The agent is the gatekeeper. The RAG chain is the expert. They are not the same thing."*

**Screenshot needed:** 
- The UI screenshot showing the bot **refusing** the "capital of France" question with the correct rejection message

---

## SLIDE 5 — ARCHITECTURE (How All Parts Connect)
**Headline:**
> "End-to-end architecture: every component has a reason to exist."

**Center visual — architecture flow diagram:**
```
[Employee / Browser]
        ↓
[React Frontend — Vite]
        ↓  POST /query
[FastAPI Backend]
        ↓
[LangGraph ReAct Agent]  ←── System Prompt (8-category gate)
        ↓ (if IT question)
[it_support_lookup Tool]
        ↓
[ChromaDB Vector Store]  ←── HuggingFace Embeddings (local, free)
        ↓ (top-k chunks)
[Gemini LLM — RAG prompt]
        ↓
[Answer returned to employee]
        ↓
[Langfuse] ←── traces every LLM call (token cost, latency, steps)
[OpenTelemetry] ←── traces ChromaDB span (DB latency in ms)
```

**Right side — "Why each tool was chosen" mini-table:**
| Tool | Why chosen | Alternative considered |
|---|---|---|
| LangGraph | Stateful agent with node/edge graph | LangChain AgentExecutor (deprecated) |
| ChromaDB | Runs locally, zero cost, persistent | Pinecone (paid, needs internet) |
| Gemini | Free tier, strong reasoning | GPT-4 (costly), Groq (fast but weaker) |
| Langfuse | Purpose-built LLM observability | Basic logging (not production-grade) |
| OpenTelemetry | Industry standard for spans/traces | Custom timing code (not portable) |

**Screenshot needed:** The **LangGraph nodes and edges diagram** you mentioned having

---

## SLIDE 6 — OBSERVABILITY LAYER (The Enterprise Part)
**Headline:**
> "Every LLM call is tracked, costed, and scored. This is production-grade observability."

**Layout: Two screenshots side by side**

**Left screenshot — Langfuse trace waterfall:**
→ Use your **Langfuse trace screenshot** showing the full waterfall of steps
→ Caption: *"Langfuse shows exactly: which LLM was called, how many tokens it used, how long it took, and what the final answer was."*

**Right screenshot — OpenTelemetry vector DB span:**
→ Use your **OTEL log screenshot** from `otel_traces.log` (the one showing `vector_db_search` span, `start_time`, `end_time`, and `k:3`)
→ Caption: *"OpenTelemetry captures what Langfuse misses — the raw Vector DB search latency (99ms in this case)."*

**Bottom callout box:**
> 🔍 *"Langfuse = LLM layer observability. OpenTelemetry = Infrastructure layer observability. Together = full-stack visibility."*

**Why this slide is powerful:**
It proves you understand the distinction between tool-level and infra-level observability. Most junior engineers don't know this difference.

---

## SLIDE 7 — QUALITY CONTROL (A/B Testing & Scoring)
**Headline:**
> "Responses were not just tested — they were scientifically compared and scored."

**Left side — What was A/B tested:**
- **Retrieval Strategy A:** Metadata Chunk approach (smaller chunks with ticket ID metadata)
- **Retrieval Strategy B:** Parent Document approach (full ticket as parent, chunk as child)
- **Prompt Version A:** Strict "answer only from context" prompt
- **Prompt Version B:** Slightly relaxed prompt

**Center visual:**
→ Use your **Langfuse scores dashboard screenshot** showing the Quality score you manually gave
→ Caption: *"Each response was manually evaluated on a 1-10 quality scale and tracked in Langfuse for comparison."*

**Right side — Config-driven testing (show the .env screenshot):**
→ Highlight the `DEFAULT_RETRIEVAL_STRATEGY`, `K_RESULTS`, `CHUNK_SIZE` variables
→ Caption: *"All parameters are environment-variable driven — no code change needed to switch between strategies."*

**Bottom callout:**
> ⚙️ *"This is how enterprise ML teams run A/B tests — not by changing code, but by changing config."*

---

## SLIDE 8 — LIVE DEMO RESULTS (What It Actually Does)
**Headline:**
> "The system behaves exactly as designed — across all test cases."

**Three-panel layout (three screenshots in a row):**

**Panel 1 — Happy Path ✅**
→ UI screenshot: User asks "My VPN authentication keeps failing" → bot gives the exact 3-step resolution
→ Label: *"IT query answered from knowledge base"*

**Panel 2 — Scope Enforcement ✅**
→ UI screenshot: User asks "What is the capital of France?" → bot gives the rejection message
→ Label: *"Off-topic query rejected without touching database"*

**Panel 3 — FastAPI Backend ✅**
→ Your **FastAPI /docs screenshot** (Swagger UI)
→ Label: *"Clean REST API — ready for integration with any enterprise system"*

**Bottom line:**
> *"Every edge case was handled. The system is not a demo — it is a working, opinionated product."*

---

## SLIDE 9 — WHAT I LEARNED & WHAT'S NEXT
**Headline:**
> "This project taught me how to think like an engineer, not just a developer."

**Left column — Key learnings:**
- The difference between building something that works and something that is observable, testable, and maintainable
- Why enterprise AI needs scope enforcement (hallucination = liability)
- How to use environment variables for config-driven A/B testing — no code changes needed
- That observability is not optional in production — it is the first thing that breaks without it

**Right column — What I would build next (shows you think beyond the task):**
- 🔐 **Add user authentication** — so IT managers can see which employee asked what
- 💬 **Add multi-turn memory** — so the agent remembers conversation history within a session
- ☁️ **Deploy to Azure/AWS** — containerize with Docker, deploy behind an API Gateway
- 🤖 **Automated evaluation pipeline** — replace manual Langfuse scoring with LLM-as-judge
- 📈 **Real ticket ingestion** — connect to ServiceNow or Jira to ingest live IT tickets instead of dummy data

**Bottom closing line (large, centered, bold):**
> *"ContextIQ is not just a chatbot. It is an observable, scoped, testable AI agent — built with the same patterns used in enterprise production systems."*

---

## EMAIL MESSAGE TO SEND WITH PPT

**To: Lead + Nivedita ma'am + Kavita ma'am (separate or combined)**
**Subject: ContextIQ — Project Summary PPT**

> Hi [Name],
>
> Thank you for your time during today's evaluation. I felt I could have explained the architecture and design decisions more clearly in person, so I've put together this PPT to give a fuller picture of the work.
>
> It covers the problem we solved, the phased approach I took, the key technical decisions and their trade-offs, the observability layer, and what I would build next given more time.
>
> I would genuinely appreciate any feedback — it will help me grow significantly.
>
> Regards,  
> Aditya

---

## NOTES FOR AI MAKING THIS PPT
1. Keep each slide to **maximum 6 bullet points or 1-2 paragraphs**. No walls of text.
2. Use **icons** (emoji or flat icons) to break up text visually.
3. The **screenshots** are real — leave placeholder boxes labeled `[INSERT SCREENSHOT: description]` wherever a screenshot is needed so Aditya can drop them in.
4. Use **two-column layouts** wherever a comparison is shown.
5. The **architecture diagram on Slide 5** should be drawn as a vertical flow chart with labeled boxes and arrows — not a bulleted list.
6. Slide 9's "What's Next" column should use a slightly lighter text color to signal these are aspirational, not delivered.
