"""
ContextIQ — Benchmark Results Auto-Filler
==========================================
This script:
  1. Reads latency results from benchmarks/results_latency.json
  2. Reads rejection results from benchmarks/results_rejection.json
  3. Parses otel_traces.log for vector_db_search spans → real OTel latency
  4. Hits /metrics endpoint for live server stats
  5. Replaces [FILL IN] placeholders in BENCHMARKING_RESULTS.md with real numbers

Run AFTER the benchmark scripts have produced their JSON output files.
Called automatically by run_benchmarks.bat / run_benchmarks.sh.
"""

import json
import os
import re
import sys
import statistics
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────────────
BACKEND_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR   = os.path.join(BACKEND_DIR, "benchmarks")
OTEL_LOG      = os.path.join(BACKEND_DIR, "otel_traces.log")
SERVER_URL    = os.getenv("API_URL", "http://localhost:8000")

RESULTS_MD    = os.path.join(
    BACKEND_DIR, "..", "not_to_be_pushed_on_github",
    "post-break", "BENCHMARKING_RESULTS.md"
)

LATENCY_JSON  = os.path.join(RESULTS_DIR, "results_latency.json")
REJECTION_JSON = os.path.join(RESULTS_DIR, "results_rejection.json")


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path: str) -> dict:
    if not os.path.exists(path):
        print(f"  [WARN] {os.path.basename(path)} not found — skipping.")
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_otel_latencies(log_path: str) -> list[float]:
    """
    Parses otel_traces.log and extracts latency in ms for every
    'vector_db_search' span using ISO 8601 start_time / end_time strings.

    Span format:
        "name": "vector_db_search"
        "start_time": "2026-07-23T23:48:56.525695Z"
        "end_time":   "2026-07-23T23:48:56.608560Z"
    """
    if not os.path.exists(log_path):
        print("  [WARN] otel_traces.log not found — skipping OTel parsing.")
        return []

    latencies_ms = []

    with open(log_path, encoding="utf-8") as f:
        content = f.read()

    # Split on span boundaries — each span is a JSON block starting with '{'
    raw_spans = re.split(r'\n(?=\{)', content.strip())

    for raw in raw_spans:
        raw = raw.strip()
        if not raw:
            continue
        try:
            span = json.loads(raw)
        except json.JSONDecodeError:
            continue

        if span.get("name") != "vector_db_search":
            continue

        start_str = span.get("start_time", "")
        end_str   = span.get("end_time", "")
        if not start_str or not end_str:
            continue

        try:
            # Parse ISO 8601 with microseconds
            fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
            t_start = datetime.strptime(start_str, fmt).replace(tzinfo=timezone.utc)
            t_end   = datetime.strptime(end_str,   fmt).replace(tzinfo=timezone.utc)
            latency_ms = (t_end - t_start).total_seconds() * 1000
            if latency_ms > 0:
                latencies_ms.append(latency_ms)
        except ValueError:
            continue

    return latencies_ms


def fetch_metrics() -> dict:
    """Hits GET /metrics on the running server. Returns {} if unreachable."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{SERVER_URL}/metrics", timeout=3) as r:
            return json.loads(r.read())
    except Exception:
        print("  [WARN] Server not reachable — skipping live /metrics fetch.")
        return {}


def pct(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    return sorted(data)[int(p * len(data))]


def replace_placeholder(md: str, key: str, value: str) -> str:
    """Replace a specific [FILL IN: key] or bare [FILL IN] placeholder."""
    # Named placeholder: [FILL IN: key]
    md = md.replace(f"[FILL IN: {key}]", value)
    return md


def fill_table_row(md: str, row_label: str, value: str) -> str:
    """
    Replace `[FILL IN]` in a markdown table row that contains row_label.
    Handles the first occurrence of [FILL IN] on that row only.
    """
    lines = md.split("\n")
    for i, line in enumerate(lines):
        if row_label in line and "[FILL IN]" in line:
            lines[i] = line.replace("[FILL IN]", f"**{value}**", 1)
            break
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  ContextIQ — Auto-filling BENCHMARKING_RESULTS.md")
    print("=" * 60)

    if not os.path.exists(RESULTS_MD):
        print(f"  ERROR: Cannot find BENCHMARKING_RESULTS.md at:\n  {RESULTS_MD}")
        sys.exit(1)

    with open(RESULTS_MD, encoding="utf-8") as f:
        md = f.read()

    changes = []

    # ── 1. Latency results ─────────────────────────────────────────
    lat = load_json(LATENCY_JSON)
    if lat:
        cold_mean = lat.get("cold_mean_ms", 0)
        warm_mean = lat.get("warm_mean_ms", 0)
        warm_p50  = lat.get("warm_p50_ms",  0)
        warm_p95  = lat.get("warm_p95_ms",  0)
        cold_p50  = lat.get("cold_p50_ms",  0)
        cold_p95  = lat.get("cold_p95_ms",  0)
        improvement = lat.get("improvement_pct", 0)

        md = fill_table_row(md, "Mean latency",    f"COLD (no singleton)")  # skip — handled below
        md = fill_table_row(md, "Cold", f"{cold_mean:.0f}ms | {cold_p50:.0f}ms | {cold_p95:.0f}ms")

        # Target specific rows in the results table
        for row, val in [
            ("COLD (no singleton)", f"{cold_mean:.0f}ms | {cold_p50:.0f}ms | {cold_p95:.0f}ms"),
            ("WARM (singleton)",    f"{warm_mean:.0f}ms | {warm_p50:.0f}ms | {warm_p95:.0f}ms"),
            ("Improvement",         f"**{improvement:.0f}%**"),
        ]:
            old_md = md
            # Replace [FILL IN] on the line that contains this row label
            lines = md.split("\n")
            for i, line in enumerate(lines):
                if row in line and "[FILL IN]" in line:
                    # Replace all [FILL IN] on this line
                    lines[i] = re.sub(r'\[FILL IN\]', val, line, count=1)
                    break
            md = "\n".join(lines)
            if md != old_md:
                changes.append(f"Latency row '{row}' → {val}")

        # Warm P95 standalone line
        old_md = md
        lines = md.split("\n")
        for i, line in enumerate(lines):
            if "Warm path P95" in line and "[FILL IN]" in line:
                lines[i] = re.sub(r'\[FILL IN\]', f"{warm_p95:.0f}ms", line, count=1)
                break
        md = "\n".join(lines)
        if md != old_md:
            changes.append(f"Warm P95 → {warm_p95:.0f}ms")

        # OTel column
        otel_lats = parse_otel_latencies(OTEL_LOG)
        if otel_lats:
            otel_p95 = pct(otel_lats, 0.95)
            otel_mean = statistics.mean(otel_lats)
            print(f"  OTel spans found: {len(otel_lats)} | mean={otel_mean:.1f}ms | P95={otel_p95:.1f}ms")
            lines = md.split("\n")
            for i, line in enumerate(lines):
                if "OTel span P95" in line and "[FILL IN]" in line:
                    lines[i] = re.sub(r'\[FILL IN\]', f"{otel_p95:.0f}ms", line, count=1)
                    break
            md = "\n".join(lines)
            changes.append(f"OTel P95 → {otel_p95:.0f}ms")
        else:
            print("  [INFO] No vector_db_search spans found in OTel log yet.")

    # ── 2. Rejection results ───────────────────────────────────────
    rej = load_json(REJECTION_JSON)
    if rej:
        it_correct   = rej.get("it_answered_correctly", 0)
        it_total     = rej.get("it_total", 15)
        ot_rejected  = rej.get("ot_rejected_correctly", 0)
        ot_total     = rej.get("ot_total", 15)
        rej_rate     = rej.get("rejection_rate_pct", 0)
        it_accuracy  = rej.get("it_accuracy_pct", 0)
        it_avg_ms    = rej.get("it_avg_latency_ms", 0)
        ot_avg_ms    = rej.get("ot_avg_latency_ms", 0)
        saved_ms     = rej.get("latency_saved_ms", 0)

        rows = [
            ("IT queries answered correctly", f"{it_correct}/{it_total} ({it_accuracy:.0f}%)"),
            ("Off-topic queries rejected",    f"{ot_rejected}/{ot_total} ({rej_rate:.0f}%)"),
            ("Rejection rate",                f"**{rej_rate:.0f}%**"),
            ("Avg latency — IT",              f"{it_avg_ms:.0f}ms"),
            ("Avg latency — Rejected",        f"{ot_avg_ms:.0f}ms"),
            ("Latency saved per rejection",   f"{saved_ms:.0f}ms"),
        ]
        for row_label, val in rows:
            lines = md.split("\n")
            for i, line in enumerate(lines):
                if row_label in line and "[FILL IN]" in line:
                    lines[i] = re.sub(r'\[FILL IN\]', val, line, count=1)
                    break
            new_md = "\n".join(lines)
            if new_md != md:
                changes.append(f"Rejection row '{row_label}' → {val}")
            md = new_md

    # ── 3. Live /metrics ───────────────────────────────────────────
    srv = fetch_metrics()
    if srv:
        srv_json_block = json.dumps(srv, indent=2)
        # Replace the placeholder JSON block in the doc
        md = re.sub(
            r'```json\n\s*\{\n\s*"total_requests".*?\}\n```',
            f"```json\n{srv_json_block}\n```",
            md,
            flags=re.DOTALL,
        )
        changes.append("Live /metrics JSON block updated")

    # ── Write back ─────────────────────────────────────────────────
    if changes:
        with open(RESULTS_MD, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"\n  Updated BENCHMARKING_RESULTS.md with {len(changes)} values:")
        for c in changes:
            print(f"    ✓ {c}")
    else:
        print("\n  [WARN] No placeholders were filled. Check that JSON result files exist.")

    print("\n  Remaining [FILL IN FROM LANGFUSE] items must be filled manually.")
    print("  See the Langfuse section in BENCHMARKING_RESULTS.md for instructions.")
    print("=" * 60)


if __name__ == "__main__":
    main()

