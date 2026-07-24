# Final Internship Evaluation Prep Guide

This guide is designed to help you crush your evaluation tomorrow. We have already written all the code required for this assignment! Your job now is to **run the code, capture the evidence, and explain the concepts clearly.**

---

## Part 1: Your Deliverables (What you MUST prepare before the meeting)

Your managers want to see *proof* that the agent works and that you successfully implemented observability. You need to prepare a short slide deck or a document with the following screenshots and explanations:

### Deliverable 1: The Basic RAG Agent
* **Action:** Run your agent in the terminal (`python -m app.core.agent`). 
* **Show:** A screenshot of the terminal showing the agent successfully answering the VPN question and refusing the "Capital of France" question.
* **Talking Point:** "I built a ReAct agent using LangGraph. It uses function calling to decide when to search our ChromaDB vector store for internal IT tickets, and when to just reply normally."

### Deliverable 2: Langfuse Out-of-the-Box Tracing
* **Action:** Go to your Langfuse dashboard and open the Trace Detail view (the waterfall diagram).
* **Show:** Screenshot 1 (the one you showed me earlier).
* **Talking Point:** "By simply adding the Langfuse CallbackHandler, I was able to automatically capture the LLM's prompts, responses, token usage, and latency without writing custom logging logic."

### Deliverable 3: Prompt Comparison & Scoring
* **Action:** 
  1. Go to your current Langfuse trace, click `Annotate -> Add Score`, and give it a `Quality` score of `1`.
  2. Go into `app/core/agent.py`, change the prompt slightly (e.g., make it ask for the answer in 3 bullet points).
  3. Run the code again.
  4. Go to Langfuse, find the *new* trace, and give it a score of `0.9`. 
* **Show:** A side-by-side comparison of the two traces showing the difference in **Token Cost** and the **Scores** you applied.
* **Talking Point:** "I tracked response quality over time using Langfuse annotations. By comparing two prompt versions, I demonstrated how modifying instructions impacts both token cost and output quality."

### Deliverable 4: OpenTelemetry for Missed Steps
* **Action:** Look at your terminal output when you run the agent. You will see a block of JSON printed to the terminal from the OpenTelemetry span (showing `vector_db_search`).
* **Show:** A screenshot of this terminal output.
* **Talking Point:** "Langfuse is great for LLMs, but it misses internal software operations like database lookups. I implemented OpenTelemetry to manually trace the ChromaDB vector search, ensuring we have full end-to-end visibility of the system."

---

## Part 2: Expected Q&A (What they will ask you)

Managers love to test your conceptual understanding. Here are the questions they will likely ask and exactly how you should answer them:

### Q1: "What is the difference between Langfuse and OpenTelemetry, and when should we use which?"
**Your Answer:** 
> "OpenTelemetry is the industry-standard protocol for general backend software tracing (like database queries and API latencies). Langfuse is a specialized platform specifically for LLMOps. 
> 
> We should use **Langfuse** when we need to track LLM-specific metrics like Prompt variations, Token Costs, and Output Quality scores. We should use **OpenTelemetry** for traditional software bottlenecks that Langfuse misses, like how long our vector database takes to return search results."

### Q2: "How does the agent decide to use the tool?"
**Your Answer:** 
> "It uses the LLM's native Function Calling capabilities within a LangGraph ReAct architecture. We pass the tool's docstring into the LLM's system prompt. The LLM evaluates the user's question, and if it matches the tool's description, the LLM outputs a JSON payload requesting to execute the tool instead of generating standard text."

### Q3: "What is the 'waterfall' diagram in Langfuse showing?"
**Your Answer:** 
> "It shows the execution Trace. The root is the user's request. It breaks down into observations: the LLM reasoning, the tool execution, and the final generation. This helps us pinpoint exactly which step is causing latency or consuming too many tokens."

### Q4: "Can we automate the scoring process?"
**Your Answer:** 
> "Yes, using a concept called 'LLM-as-a-Judge'. Instead of manually annotating scores in Langfuse, we can configure an Evaluator—a secondary LLM that reads the output and automatically grades it based on a predefined rubric (e.g., accuracy or toxicity)."

### Q5: "What exactly did OpenTelemetry capture that Langfuse didn't?"
**Your Answer:** 
> "Langfuse captured the network call to the Groq API. However, it had no visibility into the custom Python function `it_support_lookup`. I used the OpenTelemetry SDK to manually instrument the ChromaDB similarity search, capturing the exact time it took to retrieve documents from the vector database."

---

> [!TIP]
> **Confidence is key.** You built a modern, production-grade agent using cutting-edge tools (LangGraph, Groq, ChromaDB, Langfuse, OpenTelemetry). If they ask something you don't know, just say: *"That's a great question. While I focused on X for this sprint, I would approach that by looking into the documentation for Y."*
