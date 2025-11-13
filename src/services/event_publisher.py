"""Redis event publisher for notifying about successful fetches.

Publishes events to 'tg_events' channel after successful message fetch,
allowing other services (like tg_analyzer) to react automatically.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, Protocol

import redis

from src.utils.correlation import get_correlation_id
from src.observability.metrics import events_published_total

logger = logging.getLogger(__name__)


class EventPublisherProtocol(Protocol):
    """Protocol for event publisher to enable dependency inversion and testing.

    Implementations should handle disabled state gracefully and avoid raising
    on publish failures. All methods are fire-and-forget (return None).
    """

    def connect(self) -> None:
        """Connect to the underlying event bus (e.g., Redis)."""
        ...

    def disconnect(self) -> None:
        """Disconnect from the event bus and release resources."""
        ...

    def publish_fetch_complete(
        self,
        chat: str,
        date: str,
        message_count: int,
        file_path: str,
        duration_seconds: float = 0.0,
        checksum_sha256: str | None = None,
        estimated_tokens_total: int | None = None,
        first_message_ts: str | None = None,
        last_message_ts: str | None = None,
        schema_version: str | None = None,
        preprocessing_version: str | None = None,
        summary_file_path: str | None = None,
        threads_file_path: str | None = None,
        participants_file_path: str | None = None,
    ) -> None:
        """Publish a completion event after a successful fetch."""
        ...

    def publish_fetch_failed(
        self,
        chat: str,
        date: str,
        error: str,
        duration_seconds: float = 0.0,
    ) -> None:
        """Publish a failure event when fetch fails."""
        ...

    def publish_fetch_skipped(
        self,
        chat: str,
        date: str,
        reason: str,
        checksum_expected: str | None = None,
        checksum_actual: str | None = None,
    ) -> None:
        """Publish a skip event when fetching is idempotently skipped."""
        ...

    def publish_fetch_started(
        self,
        chat: str,
        date: str,
        strategy: str,
    ) -> None:
        """Publish an event when a fetch begins for a date."""
        ...

    def publish_fetch_progress(
        self,
        chat: str,
        date: str,
        messages_processed: int,
        messages_fetched: int,
    ) -> None:
        """Publish a progress update during iteration."""
        ...

    def publish_fetch_stage(
        self,
        chat: str,
        date: str,
        stage: str,
    ) -> None:
        """Publish a stage change (fetching|saving|postprocess)."""
        ...


class EventPublisher:
    """Publish events to Redis after successful fetch operations."""

    def __init__(
        self,
        redis_url: str,
        redis_password: Optional[str] = None,
        enabled: bool = True,
        events_channel: str = "tg_events",
        service_name: str = "tg_fetcher",
    ):
        """Initialize event publisher.

        Args:
            redis_url: Redis connection URL (redis://host:port)
            redis_password: Optional Redis password
            enabled: If False, events are disabled and Redis won't be contacted
            events_channel: Redis Pub/Sub channel name for events
            service_name: Service name reported in event payloads
        """
        self.redis_url = redis_url
        self.redis_password = redis_password
        self._enabled = enabled
        self._redis_client: Optional[redis.Redis] = None
        self._channel = events_channel
        self._service = service_name

    def connect(self) -> None:
        """Connect to Redis."""
        if not self._enabled:
            logger.info(
                "Event publishing disabled by configuration; not connecting to Redis"
            )
            return
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

    def _build_and_publish(self, event_type: str, payload: dict) -> None:
        """Compose base event fields and publish to Redis.

        Non-fatal on errors: logs and returns.
        """
        correlation_id = get_correlation_id()
        if not self._enabled:
            logger.debug(
                "Events disabled; skip publish",
                extra={
                    "correlation_id": correlation_id,
                    "event_type": event_type,
                },
            )
            return

        if not self._redis_client:
            logger.debug(
                "Skipping publish: Redis not connected",
                extra={
                    "correlation_id": correlation_id,
                    "event_type": event_type,
                },
            )
            return

        event = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self._service,
            "correlation_id": correlation_id,
        }
        event.update(payload)

        try:
            event_json = json.dumps(event)
            # Publish with retry policy
            from src.utils.retry import retry_sync
            from src.core.config import FetcherConfig

            # Read retry settings from config env (without coupling to DI)
            cfg = FetcherConfig()
            def _do_publish() -> int:
                assert self._redis_client is not None
                return int(self._redis_client.publish(self._channel, event_json))

            subscribers = retry_sync(
                _do_publish,
                target="redis_publish",
                max_attempts=cfg.max_retry_attempts,
                base=max(0.1, cfg.retry_backoff_factor / 4),
                max_seconds=max(1.0, cfg.retry_backoff_factor * 4),
            )
            logger.info(
                "Event published",
                extra={
                    "correlation_id": correlation_id,
                    "event_type": event_type,
                    "channel": self._channel,
                    "subscribers_count": subscribers,
                    "status": "success",
                },
            )
            # metrics: success publish
            try:
                from os import getenv

                worker = getenv("HOSTNAME", "fetcher-1")
                events_published_total.labels(
                    event_type=event_type, status="success", worker=worker
                ).inc()
            except Exception:
                # metrics must never break publishing
                pass
        except Exception as e:
            logger.error(
                "Failed to publish event",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": "publish_error",
                    "error_class": type(e).__name__,
                    "event_type": event_type,
                },
                exc_info=True,
            )
            # Rate limit metrics if applicable
            try:
                from src.utils.retry import maybe_record_rate_limit

                maybe_record_rate_limit(
                    e,
                    source="redis_publish",
                    chat=payload.get("chat"),
                    date=payload.get("date"),
                )
            except Exception:
                pass
            # metrics: failure publish
            try:
                from os import getenv

                worker = getenv("HOSTNAME", "fetcher-1")
                events_published_total.labels(
                    event_type=event_type, status="failure", worker=worker
                ).inc()
            except Exception:
                pass

    def publish_fetch_complete(
        self,
        chat: str,
        date: str,
        message_count: int,
        file_path: str,
        duration_seconds: float = 0.0,
        checksum_sha256: str | None = None,
        estimated_tokens_total: int | None = None,
        first_message_ts: str | None = None,
        last_message_ts: str | None = None,
        schema_version: str | None = None,
        preprocessing_version: str | None = None,
        summary_file_path: str | None = None,
        threads_file_path: str | None = None,
        participants_file_path: str | None = None,
    ) -> None:
        """Publish event after successful fetch.

        Args:
            chat: Chat name that was fetched.
            date: Date of messages (YYYY-MM-DD).
            message_count: Number of messages fetched.
            file_path: Path to saved JSON file.
            duration_seconds: Fetch duration in seconds.
            checksum_sha256: Optional content checksum for integrity validation.
            estimated_tokens_total: Optional token estimate for downstream NLP.
            first_message_ts: ISO timestamp of first message fetched.
            last_message_ts: ISO timestamp of last message fetched.
            schema_version: Optional schema version of stored data.
            preprocessing_version: Optional preprocessing pipeline version.
            summary_file_path: Optional path to generated summary file.
            threads_file_path: Optional path to generated threads file.
            participants_file_path: Optional path to participants file.
        """
        self._build_and_publish(
            "messages_fetched",
            {
                "chat": chat,
                "date": date,
                "message_count": message_count,
                "file_path": file_path,
                "duration_seconds": round(duration_seconds, 2),
                "checksum_sha256": checksum_sha256,
                "estimated_tokens_total": estimated_tokens_total,
                "first_message_ts": first_message_ts,
                "last_message_ts": last_message_ts,
                "schema_version": schema_version,
                "preprocessing_version": preprocessing_version,
                "summary_file_path": summary_file_path,
                "threads_file_path": threads_file_path,
                "participants_file_path": participants_file_path,
            },
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
            chat: Chat name that failed.
            date: Date attempted.
            error: Error message.
            duration_seconds: Duration before failure.
        """
        self._build_and_publish(
            "fetch_failed",
            {
                "chat": chat,
                "date": date,
                "error": error,
                "duration_seconds": round(duration_seconds, 2),
            },
        )

    def publish_fetch_skipped(
        self,
        chat: str,
        date: str,
        reason: str,
        checksum_expected: str | None = None,
        checksum_actual: str | None = None,
    ) -> None:
        """Publish event when a fetch is intentionally skipped.

        Args:
            chat: Chat identifier
            date: Target date in YYYY-MM-DD
            reason: Reason for skip (e.g., already_exists_same_checksum)
            checksum_expected: Expected checksum from summary (optional)
            checksum_actual: Actual checksum of file (optional)
        """
        self._build_and_publish(
            "fetch_skipped",
            {
                "chat": chat,
                "date": date,
                "reason": reason,
                "checksum_expected": checksum_expected,
                "checksum_actual": checksum_actual,
            },
        )

    def publish_fetch_started(
        self,
        chat: str,
        date: str,
        strategy: str,
    ) -> None:
        """Publish event when fetch for a date starts.

        Args:
            chat: Chat identifier (username or numeric id)
            date: Target date in YYYY-MM-DD
            strategy: Strategy name used for this fetch
        """
        self._build_and_publish(
            "fetch_started",
            {"chat": chat, "date": date, "strategy": strategy, "stage": "fetching"},
        )

    def publish_fetch_progress(
        self,
        chat: str,
        date: str,
        messages_processed: int,
        messages_fetched: int,
    ) -> None:
        """Publish periodic progress event during message iteration.

        Args:
            chat: Chat identifier
            date: Target date in YYYY-MM-DD
            messages_processed: Total messages iterated so far
            messages_fetched: Messages included in the collection so far
        """
        self._build_and_publish(
            "fetch_progress",
            {
                "chat": chat,
                "date": date,
                "messages_processed": messages_processed,
                "messages_fetched": messages_fetched,
            },
        )

    def publish_fetch_stage(self, chat: str, date: str, stage: str) -> None:
        """Publish stage change event.

        Args:
            chat: Chat identifier
            date: Target date
            stage: One of "fetching", "saving", "postprocess"
        """
        self._build_and_publish(
            "fetch_stage",
            {"chat": chat, "date": date, "stage": stage},
        )
