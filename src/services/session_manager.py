"""Telegram session management."""

from pathlib import Path
from typing import Any, Optional

from telethon import TelegramClient

from src.core.circuit_breaker import BreakerConfig, CircuitBreaker
from src.core.config import FetcherConfig
from src.core.exceptions import BreakerOpenError
from src.core.retry import safe_operation
from src.observability.logging_config import get_logger

logger = get_logger(__name__)


class SessionManager:
    """Manages Telegram client sessions.

    Handles session creation, persistence, and client lifecycle.
    """

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        session_dir: Path,
    ):
        """Initialize SessionManager.

        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: Phone number for authentication
            session_dir: Directory to store session files
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self._client: Optional[TelegramClient] = None
        # Remove + from phone for safe filename
        safe_phone = phone.replace("+", "")
        self._session_file = self.session_dir / f"session_{safe_phone}.session"
        # Circuit breaker to prevent hot-looping on Telethon issues
        self._breaker = CircuitBreaker(
            BreakerConfig(target="telethon", worker="session")
        )

    async def get_client(self) -> TelegramClient:
        """Get or create Telegram client.

        Returns:
            Connected TelegramClient instance
        """
        if self._client is None:
            # Mask phone for logs to avoid PII leakage
            masked_phone = (
                self.phone[:3] + "***" + self.phone[-4:]
                if len(self.phone) >= 7
                else "***"
            )
            logger.info(
                "Creating Telegram client",
                extra={"phone": masked_phone, "session_file": str(self._session_file)},
            )

            # Create client with session file
            self._client = TelegramClient(
                str(self._session_file),
                self.api_id,
                self.api_hash,
            )
            client = self._client

            # Connect and authenticate with retry
            cfg = FetcherConfig()
            try:
                # Circuit breaker guard for connect
                if not self._breaker.allow_call():
                    raise BreakerOpenError(
                        "Circuit breaker is OPEN for telethon connect"
                    )
                assert client is not None
                await safe_operation(
                    lambda: client.connect(),
                    operation_name="telethon_connect",
                    max_attempts=cfg.max_retry_attempts,
                    base_delay=max(0.1, cfg.retry_backoff_factor / 4),
                    max_delay=max(1.0, cfg.retry_backoff_factor * 4),
                )
                self._breaker.record_success()
            except Exception as e:
                # Count as breaker failure for non-rate-limit generic errors
                self._breaker.record_failure(reason=type(e).__name__)
                raise

            if not await client.is_user_authorized():
                logger.info("User not authorized, starting auth process")
                # Retriable send_code_request (in case of transient errors)
                try:
                    if not self._breaker.allow_call():
                        raise BreakerOpenError(
                            "Circuit breaker is OPEN for telethon send_code"
                        )
                    await safe_operation(
                        lambda: client.send_code_request(self.phone),
                        operation_name="telethon_send_code",
                        max_attempts=cfg.max_retry_attempts,
                        base_delay=max(0.1, cfg.retry_backoff_factor / 4),
                        max_delay=max(1.0, cfg.retry_backoff_factor * 4),
                    )
                    self._breaker.record_success()
                except Exception as e:
                    self._breaker.record_failure(reason=type(e).__name__)
                    raise

                # In production, this would need to handle code input
                # For MVP, assuming session already exists or manual intervention
                logger.warning(
                    "Session not authorized. Please run auth setup first.",
                    extra={"phone": masked_phone},
                )
                raise RuntimeError(
                    f"Session for {masked_phone} is not authorized. "
                    "Please authorize the session first."
                )

            logger.info("Telegram client connected and authorized")

        assert self._client is not None
        return self._client

    async def close(self) -> None:
        """Close the Telegram client connection."""
        if self._client is not None:
            logger.info("Closing Telegram client")
            await self._client.disconnect()
            self._client = None

    async def __aenter__(self) -> TelegramClient:
        """Async context manager entry.

        Returns:
            Connected and authorized TelegramClient instance
        """
        return await self.get_client()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        await self.close()
