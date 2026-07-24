# ContextIQ: Live Screen Recording Script

**Target Duration:** 4 - 5 minutes
**Format:** Screen recording of your actual project running (UI, Terminal, Code, Langfuse). Do NOT read from the PPT.
**Goal:** Prove you understand the underlying engineering (LangGraph, ReAct, OTel singleton bug) and can explain it clearly.

---

### 1. The Framing [0:00 - 0:15]
*(Visual: Have the ContextIQ React frontend open in your browser)*

"Hi, I'm Aditya. This is ContextIQ, a RAG agent for IT support that I built during my internship. Today, I'm going to give you a quick walkthrough of what it does, and more importantly, how it's built under the hood."

### 2. Frontend Demo [0:15 - 1:00]
*(Visual: Type in a VPN question into the UI. Hit send.)*

"Let's start with a standard IT query. I'll ask about a failing VPN connection. 
As you can see, it quickly returns a structured answer based *only* on past IT tickets."

*(Visual: Type in: 'What is the capital of France?'. Hit send.)*

"But here is where it gets interesting. If I ask it for the capital of France, it immediately refuses. 
It doesn't hallucinate, and it doesn't waste time searching the database. This happens because ContextIQ is strictly scoped to 8 IT categories. It acts as a gatekeeper, which is critical for an enterprise system where hallucination is a liability."

### 3. Architecture & Explainability [1:00 - 2:00]
*(Visual: Switch screen to show the LangGraph node diagram image or your PPT slide 6/architecture diagram)*

"To understand *why* it can refuse that question, we have to look at the architecture. 
This is not a simple RAG chain that blindly searches a database for every prompt. 

This is a **ReAct Agent** built with **LangGraph**. 
When a user asks a question, it hits the `Agent Node`. The agent pauses and *thinks*. It evaluates the user's prompt against the tools it has available. 

If the question is about IT, it decides to route to the `Retrieval Tool`, pulls the data from ChromaDB, and generates an answer. If the question is off-topic, the agent decides *not* to use any tools and just returns a direct refusal. This stateful decision-making is what makes it intelligent."

### 4. Terminal Logs - Proving the 'Thought' Process [2:00 - 3:00]
*(Visual: Switch to your VS Code terminal running the FastAPI backend. Scroll to a recent query log showing Thought/Action/Observation)*

"Let's look at the terminal to see this in action. 

When I asked the VPN question, look right here. 
First, we see the **Thought**: The agent reasons that it needs to search the IT knowledge base. 
Next, the **Action**: It explicitly decides to call the `retrieval_tool`. 
And finally, the **Observation**: It gets the ticket chunks back from the database.

*How* does it know to use that tool? In the code, I wrote a strict docstring for the retrieval tool. The LLM reads that exact description at runtime to make its routing decision. It's entirely prompt-engineered at the tool level."

### 5. The Engineering Fix - OTel Singleton [3:00 - 4:00]
*(Visual: Switch to VS Code, open `backend/app/core/telemetry.py` or show the JSON OTel span in the terminal)*

"Building this wasn't without challenges, especially regarding observability. 

I needed OpenTelemetry to track database latency, but initially, my traces were breaking. Every time a query ran, my FastAPI app was instantiating a brand new TracerProvider. It was causing memory leaks and dropping spans. 

The fix was implementing a **Singleton pattern** for the telemetry initialization. I ensured that the `TracerProvider` and `BatchSpanProcessor` were only created once during the FastAPI startup lifecycle. 
*(Highlight the setup code on screen if you have it open)*
Because of that fix, we now get perfectly clean traces, showing us exactly how many milliseconds the Vector DB search took."

### 6. Langfuse Dashboard [4:00 - 4:40]
*(Visual: Open browser to the Langfuse dashboard, click into a specific trace)*

"And finally, the LLM observability layer. This is Langfuse. 
Here, I can see the exact trace of the conversation. I can see that the prompt cost us exactly 1,301 tokens, and the completion took 140 tokens. I can see the total latency was about 10 seconds.

But notice, Langfuse only tracks the LLM wrapper. It doesn't know how long the ChromaDB search took. That is exactly why I had to build that OpenTelemetry layer alongside it—to get true full-stack visibility."

### 7. Close [4:40 - 4:55]
*(Visual: Back to the ContextIQ UI or a clean screen)*

"If I had more time, the next steps would be adding user authentication so IT managers could track query history per employee, and swapping the dummy data for a live ServiceNow integration. 

That's ContextIQ. Thank you for your time."
