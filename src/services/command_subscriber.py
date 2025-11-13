"""Redis command subscriber for receiving fetch commands.

Uses Redis List (queue pattern) for fair distribution across multiple fetcher workers.
Each command is processed by exactly one worker (BLPOP).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Optional

import redis

logger = logging.getLogger(__name__)


class CommandSubscriber:
    """Subscribe to Redis commands queue and handle fetch commands.

    Uses BLPOP (blocking list pop) to ensure each command is processed
    by exactly one worker, enabling horizontal scaling of fetchers.
    """

    def __init__(
        self,
        redis_url: str,
        redis_password: Optional[str] = None,
        command_handler: Optional[Callable] = None,
        worker_id: str = "default",
        *,
        commands_queue: str = "tg_commands",
        blpop_timeout: int = 5,
        metrics: Optional[Any] = None,
    ):
        """Initialize command subscriber.

        Args:
            redis_url: Redis connection URL (redis://host:port)
            redis_password: Optional Redis password
            command_handler: Async function to handle commands
            worker_id: Unique identifier for this worker (for logging)
            commands_queue: Redis list name for commands (queue pattern)
            blpop_timeout: BLPOP timeout in seconds for listen loop
            metrics: Metrics adapter for observability (optional)
        """
        # Local import to avoid circular imports at module import time
        from src.observability.metrics_adapter import MetricsAdapter, NoopMetricsAdapter

        self.redis_url = redis_url
        self.redis_password = redis_password
        self.command_handler = command_handler
        self.worker_id = worker_id
        self._queue = commands_queue
        self._blpop_timeout = blpop_timeout
        # Using Any for Redis client to avoid mypy stub mismatches across redis/aioredis
        self._redis_client: Any = None
        self._running = False
        # Metrics adapter (Prometheus or Noop)
        self._metrics: MetricsAdapter = (
            metrics if metrics is not None else NoopMetricsAdapter()
        )

    def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                password=self.redis_password,
                decode_responses=True,
            )
            # Test connection
            self._redis_client.ping()
            logger.info(
                f"Connected to Redis queue: {self._queue}",
                extra={
                    "queue": self._queue,
                    "redis_url": self.redis_url,
                    "worker_id": self.worker_id,
                },
            )
        except Exception as e:
            logger.error(
                f"Failed to connect to Redis: {e}",
                extra={"error": str(e), "redis_url": self.redis_url},
            )
            raise

    def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis_client:
            self._redis_client.close()
        logger.info("Disconnected from Redis", extra={"worker_id": self.worker_id})

    async def listen(self, timeout: Optional[int] = None) -> None:  # noqa: C901
        """Listen for commands from Redis queue using BLPOP.

        Uses blocking list pop (BLPOP) to ensure each command is processed
        by exactly one worker. This enables horizontal scaling.

        Command format (JSON):
        {
            "command": "fetch",
            "chat": "ru_python",
            "days_back": 1,
            "limit": 1000,
            "strategy": "recent",
            "requested_by": "scheduler",
            "timestamp": "2025-11-08T10:30:00Z"
        }

        Args:
            timeout: BLPOP timeout in seconds (default: 5)
        """
        if not self._redis_client:
            raise RuntimeError("Not connected to Redis. Call connect() first.")

        self._running = True
        logger.info(
            "Started listening for commands",
            extra={
                "worker_id": self.worker_id,
                "queue": self._queue,
                "pattern": "queue (BLPOP)",
                "timeout": timeout if timeout is not None else self._blpop_timeout,
            },
        )

        try:
            while self._running:
                # BLPOP: blocks until command available or timeout
                # Only ONE worker will receive each command (queue pattern)
                # Pass queue as a list to align with redis-py signature;
                # client typed as Any to bypass stub issues
                effective_timeout = (
                    timeout if timeout is not None else self._blpop_timeout
                )
                result = self._redis_client.blpop(
                    [self._queue], timeout=effective_timeout
                )

                if result:
                    queue_name, command_json = result
                    # Metrics: command received
                    try:
                        self._metrics.inc_command_received(
                            queue=self._queue, worker=self.worker_id
                        )
                    except Exception:
                        logger.debug(
                            "inc_command_received failed (non-fatal)", exc_info=True
                        )
                    await self._handle_command(command_json)
                else:
                    # Heartbeat on timeout to indicate liveness
                    logger.debug(
                        "BLPOP timeout; no command received",
                        extra={
                            "worker_id": self.worker_id,
                            "queue": self._queue,
                            "timeout": effective_timeout,
                        },
                    )
                    # Metrics: timeout occurred
                    try:
                        self._metrics.inc_command_timeout(
                            queue=self._queue, worker=self.worker_id
                        )
                    except Exception:
                        logger.debug(
                            "inc_command_timeout failed (non-fatal)", exc_info=True
                        )

        except KeyboardInterrupt:
            logger.info(
                "Received interrupt signal",
                extra={"worker_id": self.worker_id, "reason": "keyboard_interrupt"},
            )
        except Exception as e:
            logger.error(f"Error in listen loop: {e}", exc_info=True)
        finally:
            self._running = False

    async def _handle_command(self, command_json: str) -> None:  # noqa: C901
        """Handle incoming Redis command with validation and error handling.

        Args:
            command_json: JSON string with command data
        """
        start_time = datetime.utcnow()

        try:
            # Parse command
            command_data = json.loads(command_json)
            logger.info(
                "Received command from queue",
                extra={
                    "worker_id": self.worker_id,
                    "command": command_data.get("command"),
                    "chat": command_data.get("chat"),
                    "mode": command_data.get("mode"),
                    "date": command_data.get("date"),
                    "requested_by": command_data.get("requested_by"),
                    "timestamp": command_data.get("timestamp"),
                },
            )

            # Validate command
            if command_data.get("command") != "fetch":
                logger.warning(
                    "Unknown command type",
                    extra={
                        "worker_id": self.worker_id,
                        "error_type": "validation_error",
                        "command_type": command_data.get("command"),
                        "command_data": command_data,
                    },
                )
                # Metrics: unknown/unsupported command
                try:
                    self._metrics.inc_command_failed(
                        queue=self._queue,
                        worker=self.worker_id,
                        error_type="unknown_command",
                    )
                except Exception:
                    logger.debug(
                        "inc_command_failed(unknown_command) failed", exc_info=True
                    )
                return

            # Execute command
            if self.command_handler:
                await self.command_handler(command_data)

                # Log success
                duration = (datetime.utcnow() - start_time).total_seconds()
                logger.info(
                    "Command executed successfully",
                    extra={
                        "worker_id": self.worker_id,
                        "command": "fetch",
                        "chat": command_data.get("chat"),
                        "duration_seconds": round(duration, 2),
                        "status": "success",
                    },
                )
                # Metrics: success
                try:
                    self._metrics.inc_command_success(
                        queue=self._queue, worker=self.worker_id
                    )
                except Exception:
                    logger.debug(
                        "inc_command_success failed (non-fatal)", exc_info=True
                    )
            else:
                logger.warning(
                    "No command handler registered",
                    extra={"worker_id": self.worker_id, "error_type": "config_error"},
                )

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse command JSON",
                extra={
                    "worker_id": self.worker_id,
                    "error_type": "json_decode_error",
                    "command_json": command_json[:200],  # First 200 chars
                    "error": str(e),
                },
                exc_info=True,
            )
            # Metrics: JSON decode failed
            try:
                self._metrics.inc_command_failed(
                    queue=self._queue,
                    worker=self.worker_id,
                    error_type="json_decode_error",
                )
            except Exception:
                logger.debug(
                    "inc_command_failed(json_decode_error) failed", exc_info=True
                )
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(
                "Error handling command",
                extra={
                    "worker_id": self.worker_id,
                    "error_type": "command_handler_error",
                    "error_class": type(e).__name__,
                    "command_json": command_json[:200],
                    "duration_seconds": round(duration, 2),
                    "status": "failed",
                },
                exc_info=True,
            )
            # Metrics: command handling failed
            try:
                self._metrics.inc_command_failed(
                    queue=self._queue,
                    worker=self.worker_id,
                    error_type="command_handler_error",
                )
            except Exception:
                logger.debug(
                    "inc_command_failed(command_handler_error) failed", exc_info=True
                )

    def stop(self) -> None:
        """Stop listening for commands."""
        self._running = False
        logger.info("Stopping command subscriber...")


def create_fetch_command(
    chat: str,
    days_back: int = 1,
    limit: int = 1000,
    strategy: str = "recent",
    requested_by: str = "manual",
) -> dict[str, Any]:
    """Create a fetch command dict with all CLI parameters.

    Args:
        chat: Chat name to fetch
        days_back: Number of days to fetch
        limit: Max messages per day
        strategy: Fetch strategy (recent, full, incremental)
        requested_by: Who requested the fetch

    Returns:
        Command dict ready to be pushed to Redis queue
    """
    return {
        "command": "fetch",
        "chat": chat,
        "days_back": days_back,
        "limit": limit,
        "strategy": strategy,
        "requested_by": requested_by,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
