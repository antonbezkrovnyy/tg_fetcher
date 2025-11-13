"""Prometheus metrics for the telegram fetcher.

Defines counters and histograms and provides a helper to start the metrics
HTTP server when enabled via configuration.
"""

from __future__ import annotations

import logging

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)


# Histograms/Counters
# Note: Keep label cardinality low. We expose chat and date where helpful.
fetch_duration_seconds = Histogram(
    "fetch_duration_seconds",
    "Total duration of a fetch operation (per chat+date)",
    labelnames=("chat", "date", "worker"),
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60, 120, 300),
)

fetch_messages_total = Counter(
    "fetch_messages_total",
    "Number of messages fetched (per chat+date)",
    labelnames=("chat", "date", "worker"),
)

# Total runs (per chat/date), helps track jobs executed
fetch_runs_total = Counter(
    "fetch_runs_total",
    "Number of fetch runs (per chat+date)",
    labelnames=("chat", "date", "worker", "strategy"),
)

fetch_errors_total = Counter(
    "fetch_errors_total",
    "Number of fetch errors by type",
    labelnames=("chat", "date", "error_type", "worker"),
)

fetch_retries_total = Counter(
    "fetch_retries_total",
    "Number of retry attempts by reason",
    labelnames=("chat", "date", "reason", "worker"),
)

last_retry_delay_seconds = Gauge(
    "last_retry_delay_seconds",
    "Delay in seconds before the last retry sleep by target",
    labelnames=("target", "worker"),
)

floodwait_wait_seconds = Histogram(
    "fetch_floodwait_wait_seconds",
    "Observed wait seconds due to rate limiting (FloodWait)",
    labelnames=("chat", "date", "worker"),
    buckets=(1, 5, 10, 20, 30, 60, 120, 300, 600, 1200),
)

rate_limit_hits_total = Counter(
    "rate_limit_hits_total",
    "Number of rate limit hits (e.g., FloodWait)",
    labelnames=("source", "reason", "worker"),
)

dedup_skipped_total = Counter(
    "dedup_skipped_total",
    "Number of messages skipped due to deduplication",
    labelnames=("chat", "date", "reason", "worker"),
)

fetch_progress_messages_current = Gauge(
    "fetch_progress_messages_current",
    "Current messages processed in active fetch run",
    labelnames=("chat", "date", "worker"),
)

# Command subscriber metrics
commands_received_total = Counter(
    "commands_received_total",
    "Number of commands received from Redis queue",
    labelnames=("queue", "worker"),
)

commands_success_total = Counter(
    "commands_success_total",
    "Number of commands successfully handled",
    labelnames=("queue", "worker"),
)

commands_failed_total = Counter(
    "commands_failed_total",
    "Number of command handling errors by type",
    labelnames=("queue", "worker", "error_type"),
)

commands_timeout_total = Counter(
    "commands_timeout_total",
    "Number of BLPOP timeouts while listening on Redis queue",
    labelnames=("queue", "worker"),
)

# Events publishing counters
events_published_total = Counter(
    "events_published_total",
    "Number of events published to Redis by type and status",
    labelnames=("event_type", "status", "worker"),
)

# Circuit breaker metrics
breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state by target (0=CLOSED, 1=OPEN, 2=HALF_OPEN)",
    labelnames=("target", "worker"),
)

breaker_open_total = Counter(
    "circuit_breaker_open_total",
    "Number of times circuit breaker transitioned to OPEN state",
    labelnames=("target", "worker", "reason"),
)

fetch_lag_seconds = Histogram(
    "fetch_lag_seconds",
    "Lag between now and the latest fetched message timestamp",
    labelnames=("chat", "date", "worker"),
    buckets=(10, 30, 60, 120, 300, 600, 1200, 1800, 3600, 7200, 14400, 28800, 86400),
)


_server_started: bool = False


def ensure_metrics_server(port: int) -> None:
    """Start Prometheus metrics HTTP server once per process.

    Args:
        port: Port to bind the metrics endpoint to.
    """
    global _server_started
    if _server_started:
        return
    try:
        start_http_server(port)
        _server_started = True
        logger.info("Prometheus metrics server started", extra={"port": port})
    except Exception as e:
        # Don't fail the service if metrics cannot be started
        logger.warning("Failed to start metrics server: %s", e, exc_info=True)
