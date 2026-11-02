@echo off
REM ================================================================
REM  ContextIQ — Benchmarking Runner (Windows)
REM  
REM  USAGE (from backend/ directory):
REM      venv\Scripts\activate
REM      benchmarks\run_benchmarks.bat
REM  
REM  WHAT THIS SCRIPT DOES (in order):
REM    1. Runs the pytest unit tests     → proves parser is correct
REM    2. Runs latency_test.py           → measures singleton speedup
REM    3. Waits for you to start server  → then runs rejection_test.py
REM    4. Reads /metrics + otel_traces   → shows raw numbers
REM  
REM  OUTPUT: copy the printed numbers into BENCHMARKING_RESULTS.md
REM ================================================================

setlocal
set PYTHON=venv\Scripts\python.exe
set SERVER=http://localhost:8000

echo.
echo ================================================================
echo  ContextIQ Benchmarking Suite
echo ================================================================

REM ── Step 1: Unit Tests ──────────────────────────────────────────
echo.
echo [1/5]  Running unit tests (pytest)...
echo        These verify the ticket parser is correct before we
echo        benchmark retrieval on top of it.
echo ----------------------------------------------------------------
%PYTHON% -m pytest tests/ -v
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Tests failed. Fix before running benchmarks.
    pause
    exit /b 1
)
echo  Tests PASSED.

REM ── Step 2: Latency Benchmark (standalone, no server needed) ────
echo.
echo [2/5]  Running LATENCY benchmark...
echo        Measures: ChromaDB warm (singleton) vs cold (no-singleton)
echo        Does NOT need the server running.
echo        Takes ~30 seconds.
echo ----------------------------------------------------------------
%PYTHON% -m benchmarks.latency_test
echo  Latency benchmark complete. Note the numbers above.

REM ── Step 3: Start server reminder ───────────────────────────────
echo.
echo [3/5]  SERVER REQUIRED for next steps.
echo ----------------------------------------------------------------
echo  Open a NEW terminal and run:
echo      cd backend
echo      venv\Scripts\activate
echo      python -m app.main
echo.
echo  Wait until you see:
echo      "INFO:     Application startup complete."
echo  Then come back here and press any key.
echo ----------------------------------------------------------------
pause

REM ── Step 4: Reset metrics + run rejection benchmark ─────────────
echo.
echo [4/5]  Resetting server metrics and running REJECTION benchmark...
echo        Fires 30 queries (15 IT + 15 off-topic) at the live server.
echo        Takes ~3-6 minutes (each query = 1 LLM round-trip).
echo ----------------------------------------------------------------
curl -s -X POST %SERVER%/metrics/reset > nul
echo  Server metrics reset.
echo.
%PYTHON% -m benchmarks.rejection_test

REM ── Step 5: Read /metrics + OTel log ────────────────────────────
echo.
echo [5/5]  Reading live metrics from server...
echo ----------------------------------------------------------------
echo  GET %SERVER%/metrics
curl -s %SERVER%/metrics
echo.
echo.
echo  Last 15 lines of otel_traces.log (vector DB spans):
echo ----------------------------------------------------------------
powershell -Command "if (Test-Path otel_traces.log) { Get-Content otel_traces.log -Tail 15 } else { Write-Host 'otel_traces.log not found — run at least one query first.' }"

REM ── Step 6: Auto-fill BENCHMARKING_RESULTS.md ───────────────────
echo.
echo [6/5]  Auto-filling BENCHMARKING_RESULTS.md with measured numbers...
echo        Reads results_latency.json + results_rejection.json + otel_traces.log
echo ----------------------------------------------------------------
%PYTHON% -m benchmarks.fill_results

REM ── Done ─────────────────────────────────────────────────────────
echo.
echo ================================================================
echo  ALL BENCHMARKS COMPLETE
echo ================================================================
echo  Auto-filled numbers:
echo    - Latency improvement %% and warm/cold P50/P95 ms
echo    - Rejection rate and IT accuracy %%
echo    - OTel span P95 (from otel_traces.log)
echo    - Live /metrics JSON block
echo.
echo  Still needs manual fill (open Langfuse dashboard):
echo    - Avg input tokens for IT queries     (call this A)
echo    - Avg input tokens for rejected queries (call this R)
echo    - Token saving = (A - R) / A * 100%%
echo    - Fill [FILL IN FROM LANGFUSE] sections in BENCHMARKING_RESULTS.md
echo ================================================================
pause
endlocal

