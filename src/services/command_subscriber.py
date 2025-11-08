"""Redis command subscriber for receiving fetch commands.

Uses Redis List (queue pattern) for fair distribution across multiple fetcher workers.
Each command is processed by exactly one worker (BLPOP).
"""

import json
import logging
from datetime import datetime
from typing import Any, Callable, Optional

import redis  # type: ignore

logger = logging.getLogger(__name__)


class CommandSubscriber:
    """Subscribe to Redis commands queue and handle fetch commands.

    Uses BLPOP (blocking list pop) to ensure each command is processed
    by exactly one worker, enabling horizontal scaling of fetchers.
    """

    COMMANDS_QUEUE = "tg_commands"

    def __init__(
        self,
        redis_url: str,
        redis_password: Optional[str] = None,
        command_handler: Optional[Callable] = None,
        worker_id: str = "default",
    ):
        """Initialize command subscriber.

        Args:
            redis_url: Redis connection URL (redis://host:port)
            redis_password: Optional Redis password
            command_handler: Async function to handle commands
            worker_id: Unique identifier for this worker (for logging)
        """
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.command_handler = command_handler
        self.worker_id = worker_id
        self._redis_client: Optional[redis.Redis] = None
        self._running = False

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
                f"Connected to Redis queue: {self.COMMANDS_QUEUE}",
                extra={
                    "queue": self.COMMANDS_QUEUE,
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

    async def listen(self, timeout: int = 5) -> None:
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
            "Started listening for commands (queue pattern)...",
            extra={"worker_id": self.worker_id, "queue": self.COMMANDS_QUEUE},
        )

        try:
            while self._running:
                # BLPOP: blocks until command available or timeout
                # Only ONE worker will receive each command (queue pattern)
                result = self._redis_client.blpop(self.COMMANDS_QUEUE, timeout=timeout)

                if result:
                    queue_name, command_json = result
                    await self._handle_command(command_json)

        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
        except Exception as e:
            logger.error(f"Error in listen loop: {e}", exc_info=True)
        finally:
            self._running = False

    async def _handle_command(self, command_json: str) -> None:
        """Handle incoming Redis command.

        Args:
            command_json: JSON string with command data
        """
        try:
            # Parse command
            command_data = json.loads(command_json)
            logger.info(
                "Received command",
                extra={
                    "command": command_data.get("command"),
                    "chat": command_data.get("chat"),
                    "requested_by": command_data.get("requested_by"),
                    "worker_id": self.worker_id,
                },
            )

            # Validate command
            if command_data.get("command") != "fetch":
                logger.warning(
                    f"Unknown command: {command_data.get('command')}",
                    extra={"command_data": command_data},
                )
                return

            # Execute command
            if self.command_handler:
                await self.command_handler(command_data)
            else:
                logger.warning("No command handler registered")

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse command JSON: {e}",
                extra={"command_json": command_json},
            )
        except Exception as e:
            logger.error(
                f"Error handling command: {e}",
                extra={"command_json": command_json},
                exc_info=True,
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
