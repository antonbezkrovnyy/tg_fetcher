"""Custom exception types for better error handling and categorization.

Provides domain-specific exceptions for Telegram operations with proper context.
"""

from typing import Optional


class TelegramError(Exception):
    """Base exception for all Telegram-related errors."""

    def __init__(  # noqa: B042
        self,
        message: str,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize Telegram error with message and optional correlation id."""
        super().__init__(message)
        self.correlation_id = correlation_id


class TelegramAuthError(TelegramError):
    """Telegram authentication failed.

    Raised when:
    - Invalid API credentials
    - Session expired
    - Phone number not authorized
    """

    def __init__(  # noqa: B042
        self,
        message: str,
        phone: Optional[str] = None,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize auth error.

        Args:
            message: Error message
            phone: Phone number that failed auth
            correlation_id: Optional correlation ID for tracing
        """
        super().__init__(message, correlation_id=correlation_id)
        self.phone = phone


class FloodWaitError(TelegramError):
    """Telegram rate limit hit (FloodWait).

    Raised when Telegram API returns rate limit error.
    Should wait for `wait_seconds` before retrying.
    """

    def __init__(  # noqa: B042
        self,
        message: str,
        wait_seconds: int,
        chat: Optional[str] = None,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize flood wait error.

        Args:
            message: Error message
            wait_seconds: Seconds to wait before retry
            chat: Chat that triggered rate limit
            correlation_id: Optional correlation ID for tracing
        """
        super().__init__(message, correlation_id=correlation_id)
        self.wait_seconds = wait_seconds
        self.chat = chat


class NetworkError(TelegramError):
    """Network connection error.

    Raised when:
    - Connection timeout
    - Connection refused
    - DNS resolution failed
    """

    def __init__(  # noqa: B042
        self,
        message: str,
        retry_count: int = 0,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize network error.

        Args:
            message: Error message
            retry_count: Current retry attempt number
            correlation_id: Optional correlation ID for tracing
        """
        super().__init__(message, correlation_id=correlation_id)
        self.retry_count = retry_count


class ChatNotFoundError(TelegramError):
    """Chat/channel not found or inaccessible.

    Raised when:
    - Chat doesn't exist
    - Chat is private and bot has no access
    - Chat username is invalid
    """

    def __init__(  # noqa: B042
        self,
        message: str,
        chat: str,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize chat not found error.

        Args:
            message: Error message
            chat: Chat identifier that wasn't found
            correlation_id: Optional correlation ID for tracing
        """
        super().__init__(message, correlation_id=correlation_id)
        self.chat = chat


class DataValidationError(TelegramError):
    """Message data validation failed.

    Raised when:
    - Pydantic validation error
    - Invalid message schema
    - Missing required fields
    """

    def __init__(  # noqa: B042
        self,
        message: str,
        validation_errors: Optional[list] = None,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize data validation error.

        Args:
            message: Error message
            validation_errors: List of validation errors from Pydantic
            correlation_id: Optional correlation ID for tracing
        """
        ve = validation_errors or []
        self.validation_errors = ve
        super().__init__(message, correlation_id=correlation_id)


class BreakerOpenError(TelegramError):
    """Operation blocked by an open circuit breaker.

    Raised when attempting to execute a protected operation while the
    circuit breaker is in OPEN state.
    """

    def __init__(  # noqa: B042
        self,
        message: str,
        *,
        correlation_id: Optional[str] = None,
    ) -> None:
        """Initialize breaker open error.

        Args:
            message: Error message
            correlation_id: Optional correlation ID for tracing
        """
        super().__init__(message, correlation_id=correlation_id)
