"""
ContextIQ — Latency Benchmark: Singleton vs. Non-Singleton ChromaDB
====================================================================
PURPOSE:
    Measure the concrete latency improvement from the ChromaDBSingleton refactor.
    This script produces the numbers for resume Bullet 2:
    "Optimized vector-search latency by X% (to Yms) via singleton refactor"

HOW IT WORKS:
    - WARM PATH  : Singleton is already initialised. Measures pure search latency.
    - COLD PATH  : Resets _client_instance to None before each call, forcing
                   a new PersistentClient() on every iteration — simulating the
                   pre-singleton behaviour.

USAGE (run from backend/ directory):
    python -m benchmarks.latency_test

AFTER RUNNING:
    1. Read the printed summary.
    2. Also check otel_traces.log — each "vector_db_search" span has exact
       start/end timestamps. Parse those for the official OTel numbers.
    3. Fill the measured values into your resume bullets.
"""

import sys
import os
import time
import statistics

# Allow imports from backend/app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.vectorstore import perform_similarity_search, ChromaDBSingleton

# ── Config ─────────────────────────────────────────────────────────────────────
QUERIES = [
    "VPN fails after password change",
    "How to reset laptop password",
    "Cannot access email on mobile",
    "Printer not connecting to WiFi",
    "Software license request process",
    "Account locked out after too many attempts",
    "Timesheet portal not loading on Chrome",
    "WiFi keeps dropping in the office",
    "Need a new monitor for my workstation",
    "Outlook not syncing emails since this morning",
]
ROUNDS = 3          # Number of full query-list passes per path
K      = 3          # Number of results to retrieve (matches production default)

# ── Warm path (Singleton) ──────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("ContextIQ Latency Benchmark")
print("=" * 60)

print("\n[1/2] Warming up singleton...")
perform_similarity_search("warmup", k=K)   # First call initialises singleton

warm_latencies = []
print(f"[1/2] Running WARM path ({len(QUERIES) * ROUNDS} queries)...")
for _ in range(ROUNDS):
    for q in QUERIES:
        t0 = time.perf_counter()
        perform_similarity_search(q, k=K)
        warm_latencies.append((time.perf_counter() - t0) * 1000)

# ── Cold path (reset singleton each iteration) ─────────────────────────────────
cold_latencies = []
print(f"\n[2/2] Running COLD path ({len(QUERIES) * ROUNDS} queries)...")
for _ in range(ROUNDS):
    for q in QUERIES:
        # Reset singleton — forces new PersistentClient() on next call
        ChromaDBSingleton._client_instance    = None
        ChromaDBSingleton._embeddings_instance = None
        t0 = time.perf_counter()
        perform_similarity_search(q, k=K)
        cold_latencies.append((time.perf_counter() - t0) * 1000)

# Re-warm singleton after cold-path resets
ChromaDBSingleton._client_instance    = None
ChromaDBSingleton._embeddings_instance = None

# ── Results ────────────────────────────────────────────────────────────────────
def p(data, pct):
    return sorted(data)[int(pct * len(data))]

warm_mean = statistics.mean(warm_latencies)
cold_mean = statistics.mean(cold_latencies)
improvement = (cold_mean - warm_mean) / cold_mean * 100

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"\nWARM (Singleton)      | Mean: {warm_mean:6.1f}ms | "
      f"P50: {p(warm_latencies, .50):6.1f}ms | "
      f"P95: {p(warm_latencies, .95):6.1f}ms")
print(f"COLD (No Singleton)   | Mean: {cold_mean:6.1f}ms | "
      f"P50: {p(cold_latencies, .50):6.1f}ms | "
      f"P95: {p(cold_latencies, .95):6.1f}ms")
print(f"\nLatency improvement   : {improvement:.0f}%  ({cold_mean:.0f}ms → {warm_mean:.0f}ms mean)")
print(f"Warm path P95         : {p(warm_latencies, .95):.0f}ms")
print("\n" + "=" * 60)
print("FILL INTO RESUME:")
print(f'  "Optimized vector-search latency by {improvement:.0f}% '
      f'(to {p(warm_latencies, .95):.0f}ms P95) via '
      f'OpenTelemetry-traced singleton refactor of ChromaDB client"')
print("=" * 60)
print("\nAlso check otel_traces.log for the official OTel span durations.")

# ── Write JSON output for fill_results.py ─────────────────────────────────────
import json

_results = {
    "cold_mean_ms": round(cold_mean, 2),
    "cold_p50_ms":  round(p(cold_latencies, .50), 2),
    "cold_p95_ms":  round(p(cold_latencies, .95), 2),
    "warm_mean_ms": round(warm_mean, 2),
    "warm_p50_ms":  round(p(warm_latencies, .50), 2),
    "warm_p95_ms":  round(p(warm_latencies, .95), 2),
    "improvement_pct": round(improvement, 1),
}

_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_latency.json")
with open(_out, "w", encoding="utf-8") as _f:
    json.dump(_results, _f, indent=2)
print(f"\nResults saved → {_out}")

