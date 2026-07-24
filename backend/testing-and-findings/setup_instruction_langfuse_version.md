# ContextIQ: Final Evaluation & Screenshot Guide

This guide provides a step-by-step checklist of the screenshots and demonstrations you need to prepare for your manager to successfully complete your evaluation and secure your PPO. 

## Phase 1: The UI and End-to-End Flow
**Goal:** Show that you built a full-stack, enterprise-grade application.

*   **[ ] Screenshot 1: The Modern UI.** 
    *   **Action:** Open the frontend (`http://localhost:5173`). Toggle to Dark Mode.
    *   **Label/Talking Point:** "I built a sleek, non-AI-looking enterprise UI with a Light/Dark theme toggle. The Accenture logo is integrated, and the chat box is clean and responsive."
*   **[ ] Screenshot 2: A Successful Query.** 
    *   **Action:** Ask: *"My VPN keeps failing authentication, what do I do?"*
    *   **Label/Talking Point:** "The frontend successfully communicates with the FastAPI backend via CORS. The backend uses a LangGraph ReAct agent to decide if it needs to search the vector database."

## Phase 2: Langfuse Observability (LLM & Agent Tracing)
**Goal:** Prove you have production-level monitoring for LLM costs, latency, and steps.

*   **[ ] Screenshot 3: Langfuse Dashboard (Traces view).**
    *   **Action:** Go to Langfuse -> Traces. Show the list of recent queries.
    *   **Label/Talking Point:** "Langfuse tracks every single query. We can see the total latency, the token usage, and the cost of the Groq/Gemini API calls."
*   **[ ] Screenshot 4: Waterfall Visual of the ReAct Agent.**
    *   **Action:** Click into a specific trace in Langfuse. Expand the waterfall view showing the Agent -> Tool Call -> RAG Chain -> Final Output.
    *   **Label/Talking Point:** "Because we used LangGraph, Langfuse captures the exact 'thought process' of the agent. You can see exactly how long the LLM took to decide to use the tool, vs how long the tool took to run."
*   **[ ] Screenshot 5: Human Quality Scoring.**
    *   **Action:** In the Langfuse trace, add a manual score (e.g., Quality = 5).
    *   **Label/Talking Point:** "Engineers or reviewers can manually score responses in the dashboard. This is critical for A/B testing, as we can compare the average score of different chunking strategies."

## Phase 3: OpenTelemetry (Vector DB Latency)
**Goal:** Explain why Langfuse wasn't enough and how you solved it.

*   **[ ] Screenshot 6: The `otel_traces.log` file.**
    *   **Action:** Open the `otel_traces.log` file in VS Code showing the `vector_db_search` JSON spans.
    *   **Label/Talking Point:** "Langfuse only traces LangChain LLM calls. It *cannot* see the raw ChromaDB lookup time. I implemented custom OpenTelemetry spans to measure the exact millisecond latency of the Vector DB, piping it to a file so it doesn't crash the terminal."

## Phase 4: A/B Testing & Configurations
**Goal:** Demonstrate that the system is built for experimentation.

*   **[ ] Screenshot 7: The `.env` Configuration File.**
    *   **Action:** Show the `.env` file in VS Code highlighting the `DEFAULT_RETRIEVAL_STRATEGY`, `CHUNK_SIZE`, and `RAG_SYSTEM_PROMPT` variables.
    *   **Label/Talking Point:** "I moved all critical RAG variables to the `.env` file. We can seamlessly A/B test 'Metadata Chunking' vs 'Parent Ticket' strategies, or different system prompts, without touching the core code. We then use Langfuse's average score metrics to mathematically prove which variant works best."

## Phase 5: Handling Edge Cases (ReAct Intelligence)
**Goal:** Prove the agent is smart.

*   **[ ] Screenshot 8: General Knowledge Rejection.**
    *   **Action:** Ask the UI: *"What is the capital of France?"*
    *   **Label/Talking Point:** "Unlike a standard RAG pipeline that blindly searches the DB for 'capital of France', our ReAct agent realizes this is outside its tool description and refuses to search the database, saving us compute costs and database latency."
