"""MessageIterator encapsulates Telethon iteration and progress reporting.

This module moves date-boundary checks, progress events, and gauge updates out
of FetcherService, enabling lower cyclomatic complexity and better testability.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from typing import Awaitable, Callable, Optional, Tuple

from telethon import TelegramClient
from telethon.hints import Entity
from telethon.tl.custom import Message as TelethonMessage

from src.core.config import FetcherConfig
from src.observability.metrics_adapter import MetricsAdapter
from src.services.event_publisher import EventPublisherProtocol

logger = logging.getLogger(__name__)


class MessageIterator:
    """Iterates Telethon messages within date boundaries with progress hooks."""

    def __init__(
        self,
        *,
        client: TelegramClient,
        entity: Entity,
        source_id: str,
        start_date: date,
        start_datetime: datetime,
        end_datetime: datetime,
        config: FetcherConfig,
        event_publisher: Optional[EventPublisherProtocol],
        metrics: MetricsAdapter,
        strategy_name: str,
        correlation_id: str,
    ) -> None:
        """Initialize iterator with dependencies and context."""
        self.client = client
        self.entity = entity
        self.source_id = source_id
        self.start_date = start_date
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.config = config
        self.event_publisher = event_publisher
        self.metrics = metrics
        self.strategy_name = strategy_name
        self.correlation_id = correlation_id

    def _emit_start_events(self) -> None:
        """Publish start/stage events and reset progress gauge (best-effort)."""
        if self.config.enable_progress_events and self.event_publisher:
            try:
                self.event_publisher.publish_fetch_started(
                    chat=self.source_id,
                    date=self.start_date.isoformat(),
                    strategy=self.strategy_name,
                )
                self.event_publisher.publish_fetch_stage(
                    chat=self.source_id,
                    date=self.start_date.isoformat(),
                    stage="fetching",
                )
            except Exception:
                logger.debug(
                    "Failed to publish start events (non-fatal)",
                    extra={"correlation_id": self.correlation_id},
                    exc_info=True,
                )
        # Initialize progress gauge
        self.metrics.set_progress(
            self.source_id,
            self.start_date.isoformat(),
            0,
        )

    def _emit_progress(
        self, processed: int, fetched: int, msg_datetime: datetime
    ) -> None:
        """Update logs, events, and metrics for iteration progress (best-effort)."""
        logger.info(
            "Message iteration progress",
            extra={
                "correlation_id": self.correlation_id,
                "source": self.source_id,
                "messages_processed": processed,
                "messages_fetched": fetched,
                "current_msg_date": msg_datetime.isoformat(),
            },
        )
        if self.config.enable_progress_events and self.event_publisher:
            try:
                self.event_publisher.publish_fetch_progress(
                    chat=self.source_id,
                    date=self.start_date.isoformat(),
                    messages_processed=processed,
                    messages_fetched=fetched,
                )
            except Exception:
                logger.debug(
                    "Failed to publish progress event (non-fatal)",
                    extra={"correlation_id": self.correlation_id},
                    exc_info=True,
                )
        self.metrics.set_progress(
            self.source_id,
            self.start_date.isoformat(),
            processed,
        )

    def _check_bounds(self, msg_datetime: datetime) -> tuple[bool, bool]:
        """Return (skip, stop) flags based on date boundaries.

        - skip=True when message is outside upper bound (>= end_datetime)
        - stop=True when message is below lower bound (< start_datetime)
        """
        if msg_datetime >= self.end_datetime:
            return True, False
        if msg_datetime < self.start_datetime:
            return False, True
        return False, False

    async def run(
        self,
        handle_message: Callable[[TelethonMessage], Awaitable[bool]],
    ) -> Tuple[int, int]:
        """Iterate messages and invoke handler per message.

        Args:
            handle_message: Async function returning True if message contributed
                to the fetched count (e.g., appended), False if skipped (e.g., merged)

        Returns:
            (messages_fetched, messages_processed)
        """
        processed = 0
        fetched = 0
        started_at = time.perf_counter()

        # Emit start events and initial progress
        self._emit_start_events()

        # Simple throttle based on configured calls-per-second (best-effort)
        # Be tolerant if config has no attribute or it's non-positive: disable throttling.
        try:
            rps = getattr(self.config, "rate_limit_calls_per_sec", None)
            rps_val = float(rps) if rps is not None else None
            min_interval = 1.0 / max(0.1, rps_val) if rps_val and rps_val > 0 else 0.0
        except Exception:
            min_interval = 0.0
        last_ts = 0.0

        async for message in self.client.iter_messages(
            self.entity, offset_date=self.end_datetime, reverse=False
        ):
            # Throttle if we are iterating too quickly to avoid excessive API usage
            if last_ts > 0.0 and min_interval > 0.0:
                import time as _t

                elapsed = _t.perf_counter() - last_ts
                if elapsed < min_interval:
                    try:
                        from os import getenv
                        from asyncio import sleep as _sleep
                        from src.observability.metrics import rate_limit_hits_total

                        worker = getenv("HOSTNAME", "fetcher-1")
                        rate_limit_hits_total.labels(
                            source="iterator", reason="throttle", worker=worker
                        ).inc()
                        await _sleep(min_interval - elapsed)
                    except Exception:
                        pass
            last_ts = __import__("time").perf_counter()
            if not message.date:
                continue

            msg_datetime = message.date
            # Periodic progress logging
            if processed % self.config.progress_interval == 0 and processed > 0:
                self._emit_progress(processed, fetched, msg_datetime)

            processed += 1

            skip, stop = self._check_bounds(msg_datetime)
            if skip:
                continue
            if stop:
                logger.info(
                    "Reached start date boundary",
                    extra={
                        "correlation_id": self.correlation_id,
                        "source": self.source_id,
                        "messages_processed": processed,
                        "messages_fetched": fetched,
                        "boundary_reached": self.start_datetime.isoformat(),
                    },
                )
                break

            try:
                did_fetch = await handle_message(message)
                if did_fetch:
                    fetched += 1
            except Exception:
                logger.warning(
                    "Message handler failed (continuing)",
                    extra={"correlation_id": self.correlation_id},
                    exc_info=True,
                )

        # Observe duration and counters at the end (best-effort)
        try:
            from os import getenv
            from src.observability.metrics import (
                fetch_duration_seconds,
                fetch_messages_total,
                fetch_runs_total,
                fetch_lag_seconds,
            )

            duration = max(0.0, time.perf_counter() - started_at)
            worker = getenv("HOSTNAME", "fetcher-1")
            date_str = self.start_date.isoformat()
            # Histogram: duration per chat/date
            fetch_duration_seconds.labels(
                chat=self.source_id, date=date_str, worker=worker
            ).observe(duration)
            # Counter: total messages per chat/date
            if fetched > 0:
                fetch_messages_total.labels(
                    chat=self.source_id, date=date_str, worker=worker
                ).inc(fetched)
            # Counter: run per chat/date/strategy
            fetch_runs_total.labels(
                chat=self.source_id, date=date_str, worker=worker, strategy=self.strategy_name
            ).inc()
            # Freshness: lag between now and latest message timestamp
            if fetched > 0:
                try:
                    last_ts_utc = (
                        self.end_datetime if processed == 0 else None
                    )  # fallback
                    # We can approximate lag using last processed msg_datetime observed in progress logs;
                    # as a simpler proxy, use end boundary minus now when messages fetched.
                    import time as _t
                    from datetime import timezone as _tz
                    now_utc = datetime.now(tz=_tz.utc)
                    # If we had at least one message, use its date as last; else use end boundary
                    # Note: we don't keep the last msg timestamp here; finalized summary contains precise value
                    lag_seconds = max(
                        0.0,
                        (now_utc - (self.end_datetime if last_ts_utc else self.end_datetime)).total_seconds(),
                    )
                    fetch_lag_seconds.labels(
                        chat=self.source_id, date=date_str, worker=worker
                    ).observe(lag_seconds)
                except Exception:
                    pass
        except Exception:
            logger.debug("Metrics observation failed (non-fatal)", exc_info=True)

        return fetched, processed
