"""Core retry utilities and FloodWait handling (async).

This module provides a simple, dependency-light retry/backoff implementation
and FloodWait handling compatible with unit tests under tests/unit/test_retry_logic.py.

It intentionally avoids external dependencies (e.g., tenacity) to keep
signatures and behavior predictable for tests. Production code can still use
helpers in src.utils.retry; over time we can unify the implementations.
"""

from __future__ import annotations

import asyncio
import logging
import random
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Tuple, Type

logger = logging.getLogger(__name__)


def _get_flood_seconds(exc: BaseException) -> int:
    """Best-effort extraction of wait seconds from a FloodWait-like exception.

    Telethon FloodWaitError typically exposes `.seconds` and tests construct it
    with `capture` positional arg; custom wrappers may expose `wait_seconds`.
    """
    for attr in ("seconds", "capture", "wait_seconds"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
        if isinstance(val, (float,)):
            return int(val)
    return 0


async def retry_with_backoff(
    operation: Callable[[], Awaitable[Any]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    operation_name: str | None = None,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> Any:
    """Retry async operation with exponential backoff and optional jitter.

    Args:
        operation: Async callable to execute
        max_attempts: Max number of attempts (including first)
        base_delay: Base delay before first retry
        exponential_base: Exponent for backoff growth
        max_delay: Max cap for any single delay
        jitter: If True, apply +-50% randomization to delay
        retry_on: Exception types to retry on; others are propagated immediately
        operation_name: Optional label for logs
        on_retry: Optional callback invoked on every retry attempt as
            on_retry(attempt, delay, exception)
    """
    attempt = 0
    while True:
        try:
            attempt += 1
            return await operation()
        except retry_on as e:
            if attempt >= max_attempts:
                raise
            # Compute delay
            base = base_delay * (exponential_base ** (attempt - 1))
            delay = min(max_delay, base)
            if jitter:
                # +-50% randomness
                delay = random.uniform(0.5 * delay, 1.5 * delay)
            # Log with operation name for test assertion
            name = operation_name or "operation"
            logger.warning(
                "Retrying %s",
                name,
                extra={
                    "attempt": attempt,
                    "delay": round(delay, 4),
                    "error_class": type(e).__name__,
                },
            )
            if on_retry is not None:
                with suppress(Exception):
                    on_retry(attempt, delay, e)
            await asyncio.sleep(delay)


async def handle_flood_wait(
    operation: Callable[[], Awaitable[Any]],
    *,
    max_wait_seconds: int = 3600,
    safety_margin_seconds: int = 1,
    on_flood: Callable[[int, int], None] | None = None,
) -> Any:
    """Execute operation handling FloodWait-like exceptions by sleeping then retrying.

    Retries indefinitely until success or when the indicated wait exceeds
    max_wait_seconds; then the exception is propagated.
    """
    while True:
        try:
            return await operation()
        except Exception as e:
            wait = _get_flood_seconds(e)
            if wait > 0:
                if wait > max_wait_seconds:
                    raise
                sleep_for = wait + safety_margin_seconds
                if on_flood is not None:
                    with suppress(Exception):
                        on_flood(wait, sleep_for)
                await asyncio.sleep(sleep_for)
                continue
            # Not a FloodWait-type error; propagate
            raise


async def safe_operation(  # noqa: C901 - orchestrator combining floodwait + retry logic
    operation: Callable[[], Awaitable[Any]],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exponential_base: float = 2.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    max_flood_wait: int = 3600,
    operation_name: str | None = None,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
    on_flood: Callable[[int, int], None] | None = None,
) -> Any:
    """Combine FloodWait handling and retry with backoff for other errors.

    FloodWait-type exceptions (with .seconds/.capture/.wait_seconds) are handled by
    sleeping and retrying. Other exceptions listed in `retry_on` are retried with
    backoff/jitter up to `max_attempts`.
    """
    attempt = 0
    while True:
        try:
            attempt += 1
            return await operation()
        except Exception as e:
            # Check FloodWait-style first
            wait = _get_flood_seconds(e)
            if wait > 0:
                if wait > max_flood_wait:
                    raise
                sleep_for = wait + 1
                if on_flood is not None:
                    with suppress(Exception):
                        on_flood(wait, sleep_for)
                await asyncio.sleep(sleep_for)
                continue
            # Then handle retryable classes
            if not isinstance(e, retry_on):
                raise
            if attempt >= max_attempts:
                raise
            base = base_delay * (exponential_base ** (attempt - 1))
            delay = min(max_delay, base)
            if jitter:
                delay = random.uniform(0.5 * delay, 1.5 * delay)
            name = operation_name or "operation"
            logger.warning(
                "Retrying %s",
                name,
                extra={
                    "attempt": attempt,
                    "delay": round(delay, 4),
                    "error_class": type(e).__name__,
                },
            )
            if on_retry is not None:
                with suppress(Exception):
                    on_retry(attempt, delay, e)
            await asyncio.sleep(delay)


@dataclass
class RetryConfig:
    """Configuration for retry/backoff used in tests and simple flows."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    max_flood_wait: int = 3600
    jitter: bool = True

    async def execute(
        self,
        operation: Callable[[], Awaitable[Any]],
        *,
        operation_name: str | None = None,
        retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    ) -> Any:
        """Execute operation with configured retry/backoff.

        Args:
            operation: Async callable to execute
            operation_name: Optional label for logging
            retry_on: Exception types to retry on

        Returns:
            The result of the operation when it succeeds
        """
        return await safe_operation(
            operation,
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            exponential_base=self.exponential_base,
            max_delay=self.max_delay,
            jitter=self.jitter,
            retry_on=retry_on,
            max_flood_wait=self.max_flood_wait,
            operation_name=operation_name,
        )
