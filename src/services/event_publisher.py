"""Redis event publisher for notifying about successful fetches.

Publishes events to 'tg_events' channel after successful message fetch,
allowing other services (like tg_analyzer) to react automatically.
"""

import json
import logging
from datetime import datetime
from typing import Optional

import redis  # type: ignore

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publish events to Redis after successful fetch operations."""

    EVENTS_CHANNEL = "tg_events"

    def __init__(self, redis_url: str, redis_password: Optional[str] = None):
        """Initialize event publisher.

        Args:
            redis_url: Redis connection URL (redis://host:port)
            redis_password: Optional Redis password
        """
        self.redis_url = redis_url
        self.redis_password = redis_password
        self._redis_client: Optional[redis.Redis] = None

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
                "Connected to Redis for event publishing",
                extra={"redis_url": self.redis_url},
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
        logger.info("Disconnected from Redis")

    def publish_fetch_complete(
        self,
        chat: str,
        date: str,
        message_count: int,
        file_path: str,
        duration_seconds: float = 0.0,
    ) -> None:
        """Publish event after successful fetch.

        Args:
            chat: Chat name that was fetched
            date: Date of messages (YYYY-MM-DD)
            message_count: Number of messages fetched
            file_path: Path to saved JSON file
            duration_seconds: Fetch duration in seconds

        Event format (JSON):
        {
            "event": "messages_fetched",
            "chat": "ru_python",
            "date": "2025-11-08",
            "message_count": 580,
            "file_path": "/data/ru_python/2025-11-08.json",
            "duration_seconds": 15.3,
            "timestamp": "2025-11-08T10:30:00Z",
            "service": "tg_fetcher"
        }
        """
        if not self._redis_client:
            logger.warning("Not connected to Redis, skipping event publish")
            return

        event = {
            "event": "messages_fetched",
            "chat": chat,
            "date": date,
            "message_count": message_count,
            "file_path": file_path,
            "duration_seconds": round(duration_seconds, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "tg_fetcher",
        }

        try:
            event_json = json.dumps(event)
            subscribers = self._redis_client.publish(self.EVENTS_CHANNEL, event_json)

            logger.info(
                "Published event: messages_fetched",
                extra={
                    "chat": chat,
                    "date": date,
                    "message_count": message_count,
                    "subscribers": subscribers,
                    "channel": self.EVENTS_CHANNEL,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to publish event: {e}",
                extra={"event": event, "error": str(e)},
                exc_info=True,
            )

    def publish_fetch_failed(
        self,
        chat: str,
        date: str,
        error: str,
        duration_seconds: float = 0.0,
    ) -> None:
        """Publish event when fetch fails.

        Args:
            chat: Chat name that failed
            date: Date attempted
            error: Error message
            duration_seconds: Duration before failure
        """
        if not self._redis_client:
            return

        event = {
            "event": "fetch_failed",
            "chat": chat,
            "date": date,
            "error": error,
            "duration_seconds": round(duration_seconds, 2),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "tg_fetcher",
        }

        try:
            event_json = json.dumps(event)
            self._redis_client.publish(self.EVENTS_CHANNEL, event_json)

            logger.warning(
                "Published event: fetch_failed",
                extra={
                    "chat": chat,
                    "date": date,
                    "error": error,
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to publish failure event: {e}",
                extra={"event": event, "error": str(e)},
            )
