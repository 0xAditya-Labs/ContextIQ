#!/usr/bin/env bash
# ================================================================
#  ContextIQ — Benchmarking Runner (Mac / Linux)
#
#  USAGE (from backend/ directory):
#      source venv/bin/activate
#      bash benchmarks/run_benchmarks.sh
#
#  WHAT THIS SCRIPT DOES (in order):
#    1. Runs the pytest unit tests     → proves parser is correct
#    2. Runs latency_test.py           → measures singleton speedup
#    3. Waits for you to start server  → then runs rejection_test.py
#    4. Reads /metrics + otel_traces   → shows raw numbers
#
#  OUTPUT: copy the printed numbers into BENCHMARKING_RESULTS.md
# ================================================================

set -e   # Exit immediately if any command fails

PYTHON="venv/bin/python"
SERVER="http://localhost:8000"

# Colour helpers
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

separator() { echo -e "${CYAN}----------------------------------------------------------------${NC}"; }
header()    { echo -e "\n${YELLOW}$1${NC}"; }

echo ""
echo "================================================================"
echo "  ContextIQ Benchmarking Suite"
echo "================================================================"

# ── Step 1: Unit Tests ──────────────────────────────────────────────
header "[1/5]  Running unit tests (pytest)..."
echo "       These verify the ticket parser is correct before we"
echo "       benchmark retrieval on top of it."
separator

$PYTHON -m pytest tests/ -v

echo -e "${GREEN}  Tests PASSED.${NC}"

# ── Step 2: Latency Benchmark (standalone, no server needed) ────────
header "[2/5]  Running LATENCY benchmark..."
echo "       Measures: ChromaDB warm (singleton) vs cold (no-singleton)"
echo "       Does NOT need the server running."
echo "       Takes ~30 seconds."
separator

$PYTHON -m benchmarks.latency_test

echo -e "${GREEN}  Latency benchmark complete. Note the numbers above.${NC}"

# ── Step 3: Start server reminder ───────────────────────────────────
header "[3/5]  SERVER REQUIRED for next steps."
separator
echo "  Open a NEW terminal and run:"
echo "      cd backend"
echo "      source venv/bin/activate"
echo "      python -m app.main"
echo ""
echo "  Wait until you see:"
echo "      'INFO:     Application startup complete.'"
echo "  Then come back here and press Enter."
separator
read -r -p "  Press Enter when the server is ready..." _

# ── Step 4: Reset metrics + run rejection benchmark ─────────────────
header "[4/5]  Resetting server metrics and running REJECTION benchmark..."
echo "       Fires 30 queries (15 IT + 15 off-topic) at the live server."
echo "       Takes ~3-6 minutes (each query = 1 LLM round-trip)."
separator

curl -s -X POST "$SERVER/metrics/reset" > /dev/null
echo "  Server metrics reset."
echo ""

$PYTHON -m benchmarks.rejection_test

# ── Step 5: Read /metrics + OTel log ────────────────────────────────
header "[5/5]  Reading live metrics from server..."
separator
echo "  GET $SERVER/metrics"
curl -s "$SERVER/metrics" | python -m json.tool 2>/dev/null || curl -s "$SERVER/metrics"
echo ""
echo ""
echo "  Last 15 lines of otel_traces.log (vector DB spans):"
separator
if [ -f otel_traces.log ]; then
    tail -15 otel_traces.log
else
    echo "  otel_traces.log not found — run at least one query first."
fi

# ── Step 6: Auto-fill BENCHMARKING_RESULTS.md ──────────────────────
header "[6/5]  Auto-filling BENCHMARKING_RESULTS.md with measured numbers..."
echo "       Reads results_latency.json + results_rejection.json + otel_traces.log"
separator

$PYTHON -m benchmarks.fill_results

# ── Done ──────────────────────────────────────────────────────────────
echo ""
echo "================================================================"
echo -e "${GREEN}  ALL BENCHMARKS COMPLETE${NC}"
echo "================================================================"
echo "  Auto-filled numbers:"
echo "    - Latency improvement % and warm/cold P50/P95 ms"
echo "    - Rejection rate and IT accuracy %"
echo "    - OTel span P95 (from otel_traces.log)"
echo "    - Live /metrics JSON block"
echo ""
echo "  Still needs manual fill (open Langfuse dashboard):"
echo "    - Avg input tokens for IT queries       → A"
echo "    - Avg input tokens for rejected queries  → R"
echo "    - Token saving = (A - R) / A * 100%"
echo "    - Fill [FILL IN FROM LANGFUSE] sections in BENCHMARKING_RESULTS.md"
echo "================================================================"

