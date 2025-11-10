"""Correlation ID utilities for request tracing.

Provides context management for correlation IDs across async request lifecycle.
"""

import contextvars
import uuid
from typing import Optional

# Context variable for storing correlation ID
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


def generate_correlation_id() -> str:
    """Generate a new correlation ID.

    Returns:
        UUID4 string for correlation tracking
    """
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context.

    Returns:
        Current correlation ID or None if not set
    """
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in current context.

    Args:
        correlation_id: Correlation ID to set
    """
    _correlation_id.set(correlation_id)


def ensure_correlation_id() -> str:
    """Get existing or generate new correlation ID.

    Returns:
        Correlation ID (existing or newly generated)
    """
    current_id = get_correlation_id()
    if current_id is None:
        current_id = generate_correlation_id()
        set_correlation_id(current_id)
    return current_id


class CorrelationContext:
    """Context manager for correlation ID tracking.

    Usage:
        with CorrelationContext() as correlation_id:
            logger.info("Processing", extra={"correlation_id": correlation_id})

        # Or with custom ID:
        with CorrelationContext("custom-id") as correlation_id:
            logger.info("Processing", extra={"correlation_id": correlation_id})
    """

    def __init__(self, correlation_id: Optional[str] = None):
        """Initialize correlation context.

        Args:
            correlation_id: Optional custom correlation ID, generates new if None
        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self.token: Optional[contextvars.Token] = None

    def __enter__(self) -> str:
        """Enter context, set correlation ID.

        Returns:
            Correlation ID for this context
        """
        self.token = _correlation_id.set(self.correlation_id)
        return self.correlation_id

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context, reset correlation ID.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        if self.token is not None:
            _correlation_id.reset(self.token)
