"""Retry helpers using tenacity for sync and async operations.

Provides standardized retry policies with exponential backoff and jitter,
structured logging, and Prometheus metrics updates. Designed to be used
in network-bound operations like Telethon and Redis publish.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Awaitable, Callable, Type

from tenacity import AsyncRetrying, RetryCallState, Retrying, stop_after_attempt, wait_random_exponential

try:
    # Optional: available when Telethon installed; we treat absence gracefully
    from telethon.errors import FloodWaitError  # type: ignore
except Exception:  # pragma: no cover
    class FloodWaitError(Exception):  # fallback placeholder
        seconds: int = 0

# Metrics imported lazily inside functions to avoid import cycles

logger = logging.getLogger(__name__)


def _before_sleep_log_and_metrics(target: str) -> Callable[[RetryCallState], None]:
    def _inner(retry_state: RetryCallState) -> None:
        try:
            e = retry_state.outcome.exception() if retry_state.outcome else None
            delay = retry_state.next_action.sleep if retry_state.next_action else None
            reason = type(e).__name__ if e else "unknown"
            logger.warning(
                "Retrying operation",
                extra={
                    "target": target,
                    "attempt_number": retry_state.attempt_number,
                    "delay": delay,
                    "reason": reason,
                },
                exc_info=True,
            )
            from src.observability.metrics import last_retry_delay_seconds  # lazy

            worker = os.getenv("HOSTNAME", "fetcher-1")
            if delay is not None:
                last_retry_delay_seconds.labels(target=target, worker=worker).set(delay)
        except Exception:
            # metrics/logging must never break retries
            pass

    return _inner


def _build_wait_policy(base: float, max_seconds: float) -> Any:
    # Decorrelated jitter via wait_random_exponential gives good spread
    return wait_random_exponential(multiplier=base, max=max_seconds)


def retry_sync(
    func: Callable[[], Any],
    *,
    target: str,
    max_attempts: int,
    base: float,
    max_seconds: float,
) -> Any:
    """Execute sync function with retry policy and metrics.

    Args:
        func: Callable with no args returning result
        target: Label for metrics/logs (e.g., "redis_publish")
        max_attempts: Max retry attempts
        base: Backoff base multiplier
        max_seconds: Max backoff cap
    """
    for attempt in Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=_build_wait_policy(base, max_seconds),
        reraise=True,
        before_sleep=_before_sleep_log_and_metrics(target),
    ):
        with attempt:
            return func()


async def retry_async(
    func: Callable[[], Awaitable[Any]],
    *,
    target: str,
    max_attempts: int,
    base: float,
    max_seconds: float,
) -> Any:
    """Execute async function with retry policy and metrics."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=_build_wait_policy(base, max_seconds),
        reraise=True,
        before_sleep=_before_sleep_log_and_metrics(target),
    ):
        with attempt:
            return await func()


def maybe_record_rate_limit(e: BaseException, *, source: str, chat: str | None, date: str | None) -> None:
    """Record FloodWait/ratelimit metrics when applicable."""
    try:
        from src.observability.metrics import floodwait_wait_seconds, rate_limit_hits_total

        worker = os.getenv("HOSTNAME", "fetcher-1")
        reason = type(e).__name__
        rate_limit_hits_total.labels(source=source, reason=reason, worker=worker).inc()
        # If FloodWaitError exposes seconds, observe histogram
        wait_seconds = getattr(e, "seconds", None)
        if wait_seconds is not None and chat and date:
            floodwait_wait_seconds.labels(chat=chat, date=date, worker=worker).observe(float(wait_seconds))
    except Exception:
        pass
