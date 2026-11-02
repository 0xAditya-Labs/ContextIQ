"""
ContextIQ — Rejection Rate Benchmark
======================================
PURPOSE:
    Measure what % of out-of-scope queries are correctly rejected by the
    doc-string tool-gating mechanism. This produces the numbers for resume Bullet 3:
    "Suppressing X% of out-of-scope API calls via doc-string tool-gating"

PREREQUISITES:
    The FastAPI server must be running locally:
        python -m app.main   (from backend/ directory)

USAGE (run from backend/ directory with the server already running):
    python -m benchmarks.rejection_test

WHAT IT MEASURES:
    - IT queries    → should NOT be rejected (tool should be called)
    - Off-topic     → should be rejected (no tool call, no DB hit)
    - Prints per-query verdicts + final summary table

TOKEN SAVINGS MATH (fill in after running this + checking Langfuse):
    Avg tokens for a full IT answer  = A  (read from Langfuse)
    Avg tokens for a rejection       = R  (read from Langfuse)
    Rejection rate                   = X% (this script)
    Overall token reduction          = X% × (A - R) / A
"""

import sys
import os
import time
import requests

# Server target
API_URL = os.getenv("API_URL", "http://localhost:8000")
QUERY_ENDPOINT  = f"{API_URL}/query"
METRICS_ENDPOINT = f"{API_URL}/metrics"
RESET_ENDPOINT  = f"{API_URL}/metrics/reset"
REJECTION_MARKER = "I'm sorry, I can only assist with"

# ── Query Sets ─────────────────────────────────────────────────────────────────
IT_QUERIES = [
    "My VPN keeps disconnecting after I changed my domain password.",
    "How do I reset my Accenture laptop password?",
    "The timesheet portal shows a login error — 401 Unauthorized.",
    "I need to request a second monitor for my workstation.",
    "The office printer is showing as offline after the Windows update.",
    "I need an Adobe Creative Cloud license for my project.",
    "I cannot send emails from Outlook since this morning.",
    "The WiFi in Conference Room B keeps dropping every 10 minutes.",
    "My laptop battery drains from 100% to 0% in under two hours.",
    "VPN authentication fails when connecting from a home network.",
    "My account got locked after too many failed password attempts.",
    "Printer says 'driver unavailable' after the IT policy update.",
    "I cannot log into the internal HR portal — it spins indefinitely.",
    "Can you help me connect my phone to the corporate WiFi?",
    "I need a software license for Tableau for data analysis work.",
]

OFF_TOPIC_QUERIES = [
    "What is the capital of France?",
    "Write me a Python function to sort a list in descending order.",
    "What is the weather forecast for Bengaluru tomorrow?",
    "Who won the FIFA World Cup in 2022?",
    "Explain quantum entanglement in simple terms.",
    "Which stocks should I invest in right now?",
    "Tell me a funny joke.",
    "Translate 'Hello, how are you?' into Spanish.",
    "What is machine learning and how does it work?",
    "Summarise today's top news headlines.",
    "What is the distance from Earth to the Moon?",
    "Help me write a cover letter for a software engineering job.",
    "What is the boiling point of water at high altitude?",
    "Who is the CEO of Microsoft?",
    "Give me a recipe for chocolate chip cookies.",
]


def query(question: str) -> dict:
    """Fire one query at the API and return (answer, latency_ms)."""
    t0 = time.perf_counter()
    try:
        r = requests.post(
            QUERY_ENDPOINT,
            json={"question": question},
            timeout=60,
        )
        r.raise_for_status()
        latency_ms = (time.perf_counter() - t0) * 1000
        return {"answer": r.json()["answer"], "latency_ms": latency_ms, "error": None}
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        return {"answer": "", "latency_ms": latency_ms, "error": str(e)}


def print_header(title: str):
    print(f"\n{'=' * 65}")
    print(f"  {title}")
    print(f"{'=' * 65}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  ContextIQ Rejection Rate Benchmark")
    print("=" * 65)
    print(f"  Target: {API_URL}")

    # Reset server-side metrics first
    try:
        requests.post(RESET_ENDPOINT, timeout=5)
        print("  Server metrics reset ✓")
    except Exception:
        print("  Warning: could not reset server metrics (server might be cold)")

    # ── IT Queries ──────────────────────────────────────────────────────────────
    print_header("IT QUERIES (expect: NOT rejected, tool called)")
    it_results = []
    for q in IT_QUERIES:
        res = query(q)
        was_rejected = REJECTION_MARKER in res["answer"]
        status = "❌ WRONGLY REJECTED" if was_rejected else "✅ Answered"
        it_results.append({"rejected": was_rejected, "latency_ms": res["latency_ms"]})
        print(f"  [{status:22s}] ({res['latency_ms']:6.0f}ms) {q[:55]}")

    # ── Off-topic Queries ───────────────────────────────────────────────────────
    print_header("OFF-TOPIC QUERIES (expect: rejected, no tool call)")
    ot_results = []
    for q in OFF_TOPIC_QUERIES:
        res = query(q)
        was_rejected = REJECTION_MARKER in res["answer"]
        status = "✅ Rejected correctly" if was_rejected else "❌ SHOULD HAVE REJECTED"
        ot_results.append({"rejected": was_rejected, "latency_ms": res["latency_ms"]})
        print(f"  [{status:22s}] ({res['latency_ms']:6.0f}ms) {q[:55]}")

    # ── Summary ─────────────────────────────────────────────────────────────────
    it_wrong   = sum(1 for r in it_results if r["rejected"])
    ot_correct = sum(1 for r in ot_results if r["rejected"])

    it_avg_ms = sum(r["latency_ms"] for r in it_results) / len(it_results)
    ot_avg_ms = sum(r["latency_ms"] for r in ot_results) / len(ot_results)

    rejection_rate = ot_correct / len(ot_results) * 100
    it_accuracy    = (len(it_results) - it_wrong) / len(it_results) * 100

    print("\n" + "=" * 65)
    print("SUMMARY")
    print("=" * 65)
    print(f"  IT queries answered correctly  : {len(it_results) - it_wrong}/{len(it_results)} ({it_accuracy:.0f}%)")
    print(f"  Off-topic queries rejected     : {ot_correct}/{len(ot_results)} ({rejection_rate:.0f}%)")
    print(f"  Avg latency — IT queries       : {it_avg_ms:.0f}ms")
    print(f"  Avg latency — Rejected queries : {ot_avg_ms:.0f}ms")
    print(f"  Latency saved per rejection    : {it_avg_ms - ot_avg_ms:.0f}ms")

    # Token savings estimate
    print("\n  TOKEN SAVINGS ESTIMATE")
    print("  (fill in A and R from Langfuse, then read the result)")
    print("  A = avg tokens for a full IT answer (from Langfuse)")
    print("  R = avg tokens for a rejection      (from Langfuse)")
    print(f"  Rejection rate = {rejection_rate:.0f}%")
    print(f"  Formula: overall_reduction = {rejection_rate:.0f}% × (A - R) / A")

    print("\n  FILL INTO RESUME:")
    print(f'  "Decreased LLM input-token usage by [A-R]/A×{rejection_rate:.0f}% '
          f'via doc-string tool-gating, suppressing {rejection_rate:.0f}% '
          f'of out-of-scope API calls before vector DB access"')

    # Also print server-side metrics
    try:
        srv = requests.get(METRICS_ENDPOINT, timeout=5).json()
        print(f"\n  Server /metrics: {srv}")
    except Exception:
        pass

    print("=" * 65)

    # ── Write JSON output for fill_results.py ───────────────────────────────
    import json

    _results = {
        "it_answered_correctly": len(it_results) - it_wrong,
        "it_total":              len(it_results),
        "ot_rejected_correctly": ot_correct,
        "ot_total":              len(ot_results),
        "rejection_rate_pct":    round(rejection_rate, 1),
        "it_accuracy_pct":       round(it_accuracy, 1),
        "it_avg_latency_ms":     round(it_avg_ms, 2),
        "ot_avg_latency_ms":     round(ot_avg_ms, 2),
        "latency_saved_ms":      round(it_avg_ms - ot_avg_ms, 2),
    }

    _out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_rejection.json")
    with open(_out, "w", encoding="utf-8") as _f:
        json.dump(_results, _f, indent=2)
    print(f"\nResults saved → {_out}")

