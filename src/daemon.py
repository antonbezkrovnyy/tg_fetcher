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
from src.observability.logging_config import get_logger, setup_logging
from src.services.command_subscriber import CommandSubscriber
from src.services.event_publisher import EventPublisher
from src.services.fetcher_service import FetcherService


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
        """Handle fetch command from Redis.

        Args:
            command: Command dict with fetch parameters
        """
        chat = command.get("chat")
        days_back = command.get("days_back", 1)
        limit = command.get("limit", 1000)
        strategy = command.get("strategy", "recent")
        requested_by = command.get("requested_by", "unknown")

        if not chat:
            self.logger.error(
                "Command missing 'chat' parameter", extra={"command": command}
            )
            return

        self.logger.info(
            f"Processing fetch command for {chat}",
            extra={
                "chat": chat,
                "days_back": days_back,
                "limit": limit,
                "strategy": strategy,
                "requested_by": requested_by,
                "worker_id": self.worker_id,
            },
        )

        start_time = datetime.utcnow()

        try:
            # Execute fetch for each requested day
            for day_offset in range(days_back):
                fetch_date = (datetime.utcnow() - timedelta(days=day_offset)).strftime(
                    "%Y-%m-%d"
                )

                self.logger.info(
                    f"Fetching {chat} for {fetch_date}",
                    extra={
                        "chat": chat,
                        "date": fetch_date,
                        "worker_id": self.worker_id,
                    },
                )

                # Create fetcher service
                service = FetcherService(self.config)

                # Fetch specified chat using new single chat method
                result = await service.fetch_single_chat(chat)

                if result and self.event_publisher:
                    # Publish success event
                    duration = (datetime.utcnow() - start_time).total_seconds()

                    self.event_publisher.publish_fetch_complete(
                        chat=chat,
                        date=fetch_date,
                        message_count=result.get("message_count", 0),
                        file_path=result.get("file_path", ""),
                        duration_seconds=duration,
                    )

                    self.logger.info(
                        f"Fetch completed successfully for {chat}/{fetch_date}",
                        extra={
                            "chat": chat,
                            "date": fetch_date,
                            "message_count": result.get("message_count", 0),
                            "duration_seconds": round(duration, 2),
                            "worker_id": self.worker_id,
                        },
                    )
                else:
                    raise Exception("Fetch returned no result")

        except Exception as e:
            # Publish failure event
            duration = (datetime.utcnow() - start_time).total_seconds()

            if self.event_publisher:
                self.event_publisher.publish_fetch_failed(
                    chat=chat,
                    date=fetch_date,
                    error=str(e),
                    duration_seconds=duration,
                )

            self.logger.error(
                f"Fetch failed for {chat}",
                extra={
                    "chat": chat,
                    "error": str(e),
                    "worker_id": self.worker_id,
                },
                exc_info=True,
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
