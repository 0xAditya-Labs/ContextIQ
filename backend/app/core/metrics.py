"""
ContextIQ — In-Memory Metrics Collector
========================================
Thread-safe counter tracking request count, rejection count, and latency.
Used to generate the observable numbers that back the resume bullets.

Usage:
    from app.core.metrics import metrics
    metrics.record(latency_ms=342.1, was_rejected=False)
    print(metrics.summary())

Endpoint:
    GET /metrics  → returns summary dict
    POST /metrics/reset → resets all counters (for benchmarking)
"""
from threading import Lock
import time


class SimpleMetrics:
    """
    Lock-protected in-memory metrics store.

    Why threading.Lock and not asyncio.Lock?
    FastAPI's sync route handlers run in a thread pool (not the async event loop).
    threading.Lock is the correct primitive here — asyncio.Lock would deadlock
    when acquired from a thread pool thread outside the event loop.
    """

    def __init__(self):
        self._lock = Lock()
        self.total_requests: int = 0
        self.rejected_requests: int = 0
        self.total_latency_ms: float = 0.0
        self._started_at: float = time.time()

    def record(self, latency_ms: float, was_rejected: bool) -> None:
        """Record a single completed request."""
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += latency_ms
            if was_rejected:
                self.rejected_requests += 1

    def summary(self) -> dict:
        """Return a snapshot of all metrics. Safe to call at any time."""
        with self._lock:
            total = self.total_requests
            rejected = self.rejected_requests
            it_requests = total - rejected
            avg_latency = round(self.total_latency_ms / total, 1) if total else 0.0
            rejection_pct = round((rejected / total) * 100, 1) if total else 0.0
            uptime_s = round(time.time() - self._started_at, 1)

        return {
            "total_requests": total,
            "it_requests": it_requests,
            "rejected_requests": rejected,
            "rejection_rate_pct": rejection_pct,
            "avg_latency_ms": avg_latency,
            "uptime_seconds": uptime_s,
        }

    def reset(self) -> None:
        """Reset all counters. Useful between benchmark runs."""
        with self._lock:
            self.total_requests = 0
            self.rejected_requests = 0
            self.total_latency_ms = 0.0
            self._started_at = time.time()


# Module-level singleton — imported by routes.py
metrics = SimpleMetrics()

