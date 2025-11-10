"""Daemon mode for Telegram Fetcher Service.

Runs continuously, listening for fetch commands from Redis queue.
Supports horizontal scaling - multiple workers can run simultaneously.
"""

import asyncio
import os
import signal
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

from pydantic import ValidationError

from src.core.config import FetcherConfig
from src.core.exceptions import (
    ChatNotFoundError,
    FloodWaitError,
    NetworkError,
    TelegramAuthError,
)
from src.observability.logging_config import get_logger, setup_logging
from src.services.command_subscriber import CommandSubscriber
from src.services.event_publisher import EventPublisher
from src.services.fetcher_service import FetcherService
from src.utils.correlation import CorrelationContext, ensure_correlation_id


class FetcherDaemon:
    """Daemon that listens for Redis commands and executes fetch operations."""

    def __init__(self, config: FetcherConfig):
        """Initialize daemon.

        Args:
            config: Fetcher configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.running = False

        # Worker ID for logging and monitoring
        self.worker_id = os.getenv("HOSTNAME", "fetcher-1")

        # Redis clients
        self.command_subscriber: CommandSubscriber | None = None
        self.event_publisher: EventPublisher | None = None

    async def start(self) -> None:
        """Start daemon and listen for commands."""
        self.logger.info(
            "Starting Fetcher Daemon",
            extra={
                "worker_id": self.worker_id,
                "redis_url": self.config.redis_url,
                "chats_configured": len(self.config.telegram_chats),
            },
        )

        # Setup Redis connections
        try:
            # Command subscriber (queue pattern - fair distribution)
            self.command_subscriber = CommandSubscriber(
                redis_url=self.config.redis_url,
                redis_password=self.config.redis_password,
                command_handler=self._handle_fetch_command,
                worker_id=self.worker_id,
            )
            self.command_subscriber.connect()

            # Event publisher (broadcast pattern)
            self.event_publisher = EventPublisher(
                redis_url=self.config.redis_url,
                redis_password=self.config.redis_password,
            )
            self.event_publisher.connect()

            self.logger.info("Redis connections established")

        except Exception as e:
            self.logger.error(f"Failed to setup Redis: {e}", exc_info=True)
            raise

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        self.running = True

        # Start listening for commands
        try:
            await self.command_subscriber.listen(timeout=5)
        except Exception as e:
            self.logger.error(f"Error in daemon listen loop: {e}", exc_info=True)
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop daemon gracefully."""
        if not self.running:
            return

        self.logger.info("Stopping Fetcher Daemon...")
        self.running = False

        # Cleanup Redis connections
        if self.command_subscriber:
            self.command_subscriber.stop()
            self.command_subscriber.disconnect()

        if self.event_publisher:
            self.event_publisher.disconnect()

        self.logger.info("Fetcher Daemon stopped")

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False

    async def _handle_fetch_command(self, command: Dict[str, Any]) -> None:
        """Handle fetch command from Redis with full tracing and error handling.

        Args:
            command: Command dict with fetch parameters
        """
        # Generate correlation ID for this command
        with CorrelationContext() as correlation_id:
            chat = command.get("chat")
            days_back = command.get("days_back", 1)
            limit = command.get("limit", 1000)
            strategy = command.get("strategy", "recent")
            requested_by = command.get("requested_by", "unknown")
            date_str = command.get("date")

            # Validation
            if not chat:
                self.logger.error(
                    "Command validation failed: missing 'chat' parameter",
                    extra={
                        "correlation_id": correlation_id,
                        "command": command,
                        "worker_id": self.worker_id,
                        "error_type": "validation_error",
                    },
                )
                return

            self.logger.info(
                "Processing fetch command",
                extra={
                    "correlation_id": correlation_id,
                    "chat": chat,
                    "days_back": days_back,
                    "limit": limit,
                    "strategy": strategy,
                    "requested_by": requested_by,
                    "worker_id": self.worker_id,
                    "mode": "date" if date_str else "recent",
                    "date": date_str,
                },
            )

            start_time = datetime.utcnow()

            try:
                # Execute fetch for each requested day
                for day_offset in range(days_back):
                    fetch_date = (
                        datetime.utcnow() - timedelta(days=day_offset)
                    ).strftime("%Y-%m-%d")

                    self.logger.info(
                        "Starting fetch operation",
                        extra={
                            "correlation_id": correlation_id,
                            "chat": chat,
                            "date": fetch_date,
                            "day_offset": day_offset,
                            "worker_id": self.worker_id,
                        },
                    )

                    # Create fetcher service config for this request
                    fetch_config = self.config.model_copy(deep=True)
                    if date_str:
                        fetch_config.fetch_mode = "date"
                        fetch_config.fetch_date = date_str
                    service = FetcherService(fetch_config)

                    # Fetch with the specified date or calculated fetch_date
                    actual_date = date_str if date_str else fetch_date
                    result = await service.fetch_single_chat(chat, actual_date)

                    if result and self.event_publisher:
                        # Publish success event
                        duration = (datetime.utcnow() - start_time).total_seconds()

                        self.event_publisher.publish_fetch_complete(
                            chat=chat,
                            date=actual_date,
                            message_count=result.get("message_count", 0),
                            file_path=result.get("file_path", ""),
                            duration_seconds=duration,
                        )

                        self.logger.info(
                            "Fetch completed successfully",
                            extra={
                                "correlation_id": correlation_id,
                                "chat": chat,
                                "date": actual_date,
                                "message_count": result.get("message_count", 0),
                                "duration_seconds": round(duration, 2),
                                "worker_id": self.worker_id,
                                "status": "success",
                            },
                        )
                    else:
                        raise Exception("Fetch returned no result")

            except TelegramAuthError as e:
                # Auth errors - don't retry
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.logger.error(
                    "Telegram authentication failed",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": "auth_error",
                        "chat": chat,
                        "phone": getattr(e, "phone", None),
                        "worker_id": self.worker_id,
                        "duration_seconds": round(duration, 2),
                        "status": "failed",
                    },
                    exc_info=True,
                )

                if self.event_publisher:
                    self.event_publisher.publish_fetch_failed(
                        chat=chat,
                        date=date_str or fetch_date,
                        error=f"auth_error: {str(e)}",
                        duration_seconds=duration,
                    )

            except FloodWaitError as e:
                # Rate limit - log and wait
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.logger.warning(
                    "Telegram rate limit hit",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": "rate_limit",
                        "chat": chat,
                        "wait_seconds": e.wait_seconds,
                        "worker_id": self.worker_id,
                        "duration_seconds": round(duration, 2),
                        "status": "rate_limited",
                    },
                )

                # Should implement retry with backoff here
                # For now, just publish failure event
                if self.event_publisher:
                    self.event_publisher.publish_fetch_failed(
                        chat=chat,
                        date=date_str or fetch_date,
                        error=f"rate_limit: wait {e.wait_seconds}s",
                        duration_seconds=duration,
                    )

            except NetworkError as e:
                # Network errors - can retry
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.logger.error(
                    "Network error during fetch",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": "network_error",
                        "chat": chat,
                        "retry_count": e.retry_count,
                        "worker_id": self.worker_id,
                        "duration_seconds": round(duration, 2),
                        "status": "failed",
                    },
                    exc_info=True,
                )

                if self.event_publisher:
                    self.event_publisher.publish_fetch_failed(
                        chat=chat,
                        date=date_str or fetch_date,
                        error=f"network_error: {str(e)}",
                        duration_seconds=duration,
                    )

            except ChatNotFoundError as e:
                # Chat doesn't exist - don't retry
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.logger.error(
                    "Chat not found",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": "chat_not_found",
                        "chat": chat,
                        "worker_id": self.worker_id,
                        "duration_seconds": round(duration, 2),
                        "status": "failed",
                    },
                    exc_info=True,
                )

                if self.event_publisher:
                    self.event_publisher.publish_fetch_failed(
                        chat=chat,
                        date=date_str or fetch_date,
                        error=f"chat_not_found: {str(e)}",
                        duration_seconds=duration,
                    )

            except Exception as e:
                # Unknown errors - log with full context
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.logger.error(
                    "Unexpected error during fetch",
                    extra={
                        "correlation_id": correlation_id,
                        "error_type": "unknown_error",
                        "chat": chat,
                        "error_class": type(e).__name__,
                        "worker_id": self.worker_id,
                        "duration_seconds": round(duration, 2),
                        "status": "failed",
                    },
                    exc_info=True,
                )

                if self.event_publisher:
                    self.event_publisher.publish_fetch_failed(
                        chat=chat,
                        date=date_str or fetch_date,
                        error=f"{type(e).__name__}: {str(e)}",
                        duration_seconds=duration,
                    )


async def main() -> int:
    """Main entry point for daemon mode.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load configuration
        config = FetcherConfig()
        config.validate_mode_requirements()

    except ValidationError as e:
        print(f"Configuration validation error:\n{e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Failed to load configuration: {e}", file=sys.stderr)
        return 1

    # Setup logging
    setup_logging(
        level=config.log_level,
        log_format=config.log_format,
        service_name="telegram-fetcher-daemon",
        loki_url=config.loki_url,
    )

    # Create and start daemon
    daemon = FetcherDaemon(config)

    try:
        await daemon.start()
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return 0
    except Exception as e:
        print(f"Fatal error in daemon: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
