"""Retry utilities for network operations and rate limiting.

This module provides robust retry mechanisms with exponential backoff
and special handling for Telegram FloodWait errors.
"""

import asyncio
import logging
import random
from typing import Any, Callable, Optional, Type, TypeVar

from telethon.errors import FloodWaitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_with_backoff(
    operation: Callable[[], Any],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: tuple[Type[Exception], ...] = (Exception,),
    operation_name: str = "operation",
) -> Any:
    """Retry async operation with exponential backoff.

    Args:
        operation: Async callable to retry
        max_attempts: Maximum retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Exponential growth factor
        jitter: Add random jitter to delay
        retry_on: Tuple of exception types to retry on
        operation_name: Human-readable operation name for logging

    Returns:
        Operation result

    Raises:
        Last exception if all retries exhausted
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return await operation()
        except retry_on as e:
            last_exception = e

            if attempt == max_attempts:
                logger.error(
                    f"{operation_name} failed after {max_attempts} attempts",
                    extra={
                        "operation": operation_name,
                        "attempts": max_attempts,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)

            # Add jitter to prevent thundering herd
            if jitter:
                delay = delay * (0.5 + random.random())

            logger.warning(
                f"{operation_name} failed (attempt {attempt}/{max_attempts}), "
                f"retrying in {delay:.2f}s",
                extra={
                    "operation": operation_name,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "delay_seconds": delay,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            await asyncio.sleep(delay)

    # Should never reach here, but satisfy type checker
    if last_exception:
        raise last_exception
    raise RuntimeError(f"{operation_name} failed with no exception")


async def handle_flood_wait(
    operation: Callable[[], T],
    max_wait_seconds: int = 3600,
    operation_name: str = "operation",
) -> T:
    """Handle Telegram FloodWait with automatic retry.

    FloodWait errors require waiting for the specified duration.
    This function handles the wait automatically with a configurable maximum.

    Args:
        operation: Async callable that may raise FloodWaitError
        max_wait_seconds: Maximum seconds to wait for FloodWait
        operation_name: Human-readable operation name for logging

    Returns:
        Operation result

    Raises:
        FloodWaitError: If wait time exceeds max_wait_seconds
        Other exceptions from operation
    """
    while True:
        try:
            return await operation()
        except FloodWaitError as e:
            wait_seconds = e.seconds

            if wait_seconds > max_wait_seconds:
                logger.error(
                    f"{operation_name} FloodWait too long: {wait_seconds}s "
                    f"(max: {max_wait_seconds}s)",
                    extra={
                        "operation": operation_name,
                        "flood_wait_seconds": wait_seconds,
                        "max_wait_seconds": max_wait_seconds,
                    },
                )
                raise

            logger.warning(
                f"{operation_name} hit FloodWait, waiting {wait_seconds}s",
                extra={
                    "operation": operation_name,
                    "flood_wait_seconds": wait_seconds,
                },
            )

            await asyncio.sleep(wait_seconds + 1)  # +1 second safety margin


async def safe_operation(
    operation: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    max_flood_wait: int = 3600,
    operation_name: str = "operation",
    retry_on: tuple[Type[Exception], ...] = (Exception,),
) -> T:
    """Combined retry with backoff and FloodWait handling.

    This is a convenience function that combines exponential backoff
    retry with automatic FloodWait handling.

    Args:
        operation: Async callable to execute safely
        max_attempts: Maximum retry attempts for transient errors
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay cap
        max_flood_wait: Maximum seconds to wait for FloodWait
        operation_name: Human-readable operation name
        retry_on: Exception types to retry (excluding FloodWaitError)

    Returns:
        Operation result

    Raises:
        Exception from operation after exhausting retries
    """

    async def operation_with_flood_handling() -> T:
        return await handle_flood_wait(
            operation, max_wait_seconds=max_flood_wait, operation_name=operation_name
        )

    return await retry_with_backoff(
        operation=operation_with_flood_handling,
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        retry_on=retry_on,
        operation_name=operation_name,
    )


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        max_flood_wait: int = 3600,
        jitter: bool = True,
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay cap in seconds
            exponential_base: Exponential growth factor
            max_flood_wait: Maximum seconds to wait for FloodWait
            jitter: Add random jitter to delays
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.max_flood_wait = max_flood_wait
        self.jitter = jitter

    async def execute(
        self,
        operation: Callable[[], T],
        operation_name: str = "operation",
        retry_on: tuple[Type[Exception], ...] = (Exception,),
    ) -> T:
        """Execute operation with configured retry behavior.

        Args:
            operation: Async callable to execute
            operation_name: Human-readable operation name
            retry_on: Exception types to retry

        Returns:
            Operation result
        """
        return await safe_operation(
            operation=operation,
            max_attempts=self.max_attempts,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            max_flood_wait=self.max_flood_wait,
            operation_name=operation_name,
            retry_on=retry_on,
        )
