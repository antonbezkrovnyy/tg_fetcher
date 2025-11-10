"""Custom exception types for better error handling and categorization.

Provides domain-specific exceptions for Telegram operations with proper context.
"""

from typing import Optional


class TelegramError(Exception):
    """Base exception for all Telegram-related errors."""

    def __init__(self, message: str, correlation_id: Optional[str] = None):
        """Initialize Telegram error.

        Args:
            message: Error message
            correlation_id: Optional correlation ID for tracing
        """
        self.correlation_id = correlation_id
        super().__init__(message)


class TelegramAuthError(TelegramError):
    """Telegram authentication failed.

    Raised when:
    - Invalid API credentials
    - Session expired
    - Phone number not authorized
    """

    def __init__(
        self,
        message: str,
        phone: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize auth error.

        Args:
            message: Error message
            phone: Phone number that failed auth
            correlation_id: Optional correlation ID for tracing
        """
        self.phone = phone
        super().__init__(message, correlation_id)


class FloodWaitError(TelegramError):
    """Telegram rate limit hit (FloodWait).

    Raised when Telegram API returns rate limit error.
    Should wait for `wait_seconds` before retrying.
    """

    def __init__(
        self,
        message: str,
        wait_seconds: int,
        chat: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize flood wait error.

        Args:
            message: Error message
            wait_seconds: Seconds to wait before retry
            chat: Chat that triggered rate limit
            correlation_id: Optional correlation ID for tracing
        """
        self.wait_seconds = wait_seconds
        self.chat = chat
        super().__init__(message, correlation_id)


class NetworkError(TelegramError):
    """Network connection error.

    Raised when:
    - Connection timeout
    - Connection refused
    - DNS resolution failed
    """

    def __init__(
        self,
        message: str,
        retry_count: int = 0,
        correlation_id: Optional[str] = None,
    ):
        """Initialize network error.

        Args:
            message: Error message
            retry_count: Current retry attempt number
            correlation_id: Optional correlation ID for tracing
        """
        self.retry_count = retry_count
        super().__init__(message, correlation_id)


class ChatNotFoundError(TelegramError):
    """Chat/channel not found or inaccessible.

    Raised when:
    - Chat doesn't exist
    - Chat is private and bot has no access
    - Chat username is invalid
    """

    def __init__(
        self,
        message: str,
        chat: str,
        correlation_id: Optional[str] = None,
    ):
        """Initialize chat not found error.

        Args:
            message: Error message
            chat: Chat identifier that wasn't found
            correlation_id: Optional correlation ID for tracing
        """
        self.chat = chat
        super().__init__(message, correlation_id)


class DataValidationError(TelegramError):
    """Message data validation failed.

    Raised when:
    - Pydantic validation error
    - Invalid message schema
    - Missing required fields
    """

    def __init__(
        self,
        message: str,
        validation_errors: Optional[list] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize data validation error.

        Args:
            message: Error message
            validation_errors: List of validation errors from Pydantic
            correlation_id: Optional correlation ID for tracing
        """
        self.validation_errors = validation_errors or []
        super().__init__(message, correlation_id)
