"""
Retry logic and error handling utilities
"""

import asyncio
import logging
import os
from functools import wraps

from telethon.errors import FloodWaitError, RPCError
from tenacity import (
    after_log,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Configuration from environment
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
MIN_RETRY_WAIT = int(os.getenv("MIN_RETRY_WAIT", "1"))
MAX_RETRY_WAIT = int(os.getenv("MAX_RETRY_WAIT", "60"))


def is_retryable_error(exception):
    """Determine if error is retryable"""
    # Network errors, temporary API issues
    retryable_types = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )

    # FloodWait is handled separately
    if isinstance(exception, FloodWaitError):
        return False

    # Some RPC errors are retryable
    if isinstance(exception, RPCError):
        # Temporary errors
        if exception.code in [500, 503, -503]:
            return True
        return False

    return isinstance(exception, retryable_types)


def retry_on_error(func):
    """
    Decorator for automatic retry with exponential backoff
    Handles both sync and async functions
    """

    @retry(
        retry=retry_if_exception_type(lambda e: is_retryable_error(e)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=MIN_RETRY_WAIT, max=MAX_RETRY_WAIT),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except FloodWaitError as e:
            # FloodWait needs special handling - log and re-raise
            logger.warning(
                f"FloodWait error: must wait {e.seconds} seconds",
                extra={"error_type": "FloodWaitError", "wait_seconds": e.seconds},
            )
            raise
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {e}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise

    @retry(
        retry=retry_if_exception_type(lambda e: is_retryable_error(e)),
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=MIN_RETRY_WAIT, max=MAX_RETRY_WAIT),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        after=after_log(logger, logging.INFO),
    )
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Error in {func.__name__}: {e}",
                extra={
                    "function": func.__name__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )
            raise

    # Return appropriate wrapper based on function type
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def handle_flood_wait(max_wait: int = 300):
    """
    Decorator for handling Telegram FloodWaitError specifically.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                wait_time = e.seconds

                if wait_time > max_wait:
                    logger.error(
                        f"Flood wait time {wait_time}s exceeds max_wait {max_wait}s. Giving up."
                    )
                    raise

                logger.warning(
                    f"Flood wait triggered. Waiting {wait_time}s before retry."
                )
                await asyncio.sleep(wait_time)

                # Retry once after flood wait
                return await func(*args, **kwargs)

        return wrapper

    return decorator


async def handle_flood_wait_direct(func, *args, **kwargs):
    """
    Execute function with FloodWait handling (direct call version)
    Automatically waits if FloodWaitError is raised
    """
    while True:
        try:
            return await func(*args, **kwargs)
        except FloodWaitError as e:
            wait_time = e.seconds + 5  # Add 5 seconds buffer
            logger.warning(
                f"FloodWait encountered. Waiting {wait_time} seconds...",
                extra={
                    "wait_seconds": wait_time,
                    "function": (
                        func.__name__ if hasattr(func, "__name__") else str(func)
                    ),
                },
            )
            await asyncio.sleep(wait_time)
            logger.info("Resuming after FloodWait")
            # Loop will retry automatically


# Additional utility functions for testing compatibility


def calculate_backoff(
    attempt: int, base: float, multiplier: float, max_delay: float, jitter: bool = True
) -> float:
    """Calculate delay for exponential backoff with optional jitter."""
    import random

    delay = base * (multiplier ** (attempt - 1))
    delay = min(delay, max_delay)

    if jitter:
        # Add ±25% jitter to prevent thundering herd
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
        delay = max(0, delay)  # Ensure non-negative

    return delay


def should_retry_exception(exception: Exception) -> bool:
    """Determine if an exception should be retried (default policy)."""
    # Network errors - should retry
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True

    # Telegram rate limiting - should retry with delay
    if isinstance(exception, FloodWaitError):
        return True

    # Authentication errors - should not retry
    try:
        from telethon.errors import AuthKeyError

        if isinstance(exception, AuthKeyError):
            return False
    except ImportError:
        pass

    # Other RPC errors - depends on specific error
    if isinstance(exception, RPCError):
        # Can add more specific logic here
        return False

    # Unknown errors - don't retry by default
    return False


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retry_on_exceptions=None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

        # Convert list to tuple if needed
        if isinstance(retry_on_exceptions, list):
            retry_on_exceptions = tuple(retry_on_exceptions)

        self.retry_on_exceptions = retry_on_exceptions or (
            ConnectionError,
            TimeoutError,
            FloodWaitError,
        )

    def should_retry(self, exception: Exception) -> bool:
        """Determine if an exception should trigger a retry."""
        # Never retry authentication errors
        try:
            from telethon.errors import AuthKeyError

            if isinstance(exception, AuthKeyError):
                return False
        except ImportError:
            pass

        # Always retry network and temporary errors
        if isinstance(exception, self.retry_on_exceptions):
            return True

        # Don't retry by default
        return False


class RateLimiter:
    """Enhanced rate limiter for API requests"""

    def __init__(
        self,
        requests_per_second: float = None,
        calls_per_second: float = None,
        burst_size: int = 5,
    ):
        # Support both parameter names for backward compatibility
        rate = (
            calls_per_second
            or requests_per_second
            or float(os.getenv("REQUESTS_PER_SECOND", "1.0"))
        )

        self.calls_per_second = rate
        self.burst_size = burst_size
        self.min_interval = 1.0 / rate if rate > 0 else 0
        self.last_request_time = 0
        self.tokens = burst_size

        logger.info(f"Rate limiter initialized: {rate} req/s, burst: {burst_size}")

    async def acquire(self):
        """Wait if necessary to respect rate limit"""
        if self.min_interval <= 0:
            return

        import time

        now = time.time()

        # Token bucket algorithm for burst handling
        time_passed = now - self.last_request_time
        self.tokens = min(
            self.burst_size, self.tokens + time_passed * self.calls_per_second
        )

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            self.last_request_time = now
            return

        # Need to wait
        wait_time = (1.0 - self.tokens) / self.calls_per_second
        logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
        await asyncio.sleep(wait_time)

        self.tokens = 0.0
        self.last_request_time = time.time()


# Enhanced retry decorator for tests
def retry_on_error_enhanced(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple = None,
):
    """Enhanced decorator for adding retry logic to async functions."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            retry_exceptions = exceptions or (ConnectionError, TimeoutError)
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    # Check if we should retry this exception
                    if not isinstance(e, retry_exceptions):
                        logger.warning(f"Non-retryable error in {func.__name__}: {e}")
                        raise

                    if attempt >= max_attempts:
                        logger.error(
                            f"Max retry attempts ({max_attempts}) reached for {func.__name__}"
                        )
                        raise

                    delay = calculate_backoff(
                        attempt,
                        backoff_factor,
                        2.0,  # multiplier
                        max_delay,
                        jitter=True,
                    )

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )

                    await asyncio.sleep(delay)

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator
