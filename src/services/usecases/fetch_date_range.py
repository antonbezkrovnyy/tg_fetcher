"""Use case to process a single date range end-to-end for a chat."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Protocol, Tuple

from telethon import TelegramClient
from telethon.hints import Entity

from src.core.config import FetcherConfig
from src.models.schemas import SourceInfo
from src.services.skip.skip_checker import SkipExistingChecker
from src.utils.checksum import compute_file_checksum

logger = logging.getLogger(__name__)


class _Repository(Protocol):
    def create_collection(
        self, *, source_info: SourceInfo, messages: list[Any]
    ) -> Any: ...

    def save_collection(
        self, *, source_name: str, target_date: date, collection: Any
    ) -> str | None: ...
    def get_output_file_path(self, source_id: str, start_date: date) -> Any: ...
    def get_summary_path(self, source_id: str, start_date: date) -> Any: ...


class _Preprocessor(Protocol):
    def enrich(self, message: Any) -> Any: ...
    def maybe_merge_short(self, last_message: Any | None, new_message: Any) -> bool: ...


class _SourceMapper(Protocol):
    def get_sender_name(self, sender_obj: Any) -> str: ...


class _DateRangeProcessor(Protocol):
    async def iterate(
        self,
        *,
        client: TelegramClient,
        entity: Entity,
        source_info: SourceInfo,
        start_date: date,
        start_datetime: datetime,
        end_datetime: datetime,
        correlation_id: str,
        handle: Any,
    ) -> Tuple[int, int]: ...


class _ProgressService(Protocol):
    def reset_gauge(self, chat: str, date: str) -> None: ...
    def publish_stage(self, *, chat: str, date: str, stage: str) -> None: ...


class _FinalizationOrchestrator(Protocol):
    def finalize(
        self,
        *,
        source_info: SourceInfo,
        start_date: date,
        collection: Any,
        messages_fetched: int,
        duration: float,
        file_path: str | None,
        checksum_fn: Any,
    ) -> None: ...


class _ProgressTracker(Protocol):
    def is_date_completed(self, source_id: str, date: date) -> bool: ...

    def mark_in_progress(self, source_id: str, date: date) -> None: ...

    def mark_completed(
        self,
        *,
        source: str,
        target_date: date,
        message_count: int,
        last_message_id: int | None,
    ) -> None: ...

    def get_source_progress(self, source: str) -> Any | None: ...


@dataclass
class FetchDateRangeDeps:
    """Dependencies required by FetchDateRangeUseCase."""

    config: FetcherConfig
    repository: _Repository
    preprocessor: _Preprocessor
    source_mapper: _SourceMapper
    date_range_processor: _DateRangeProcessor
    progress_service: _ProgressService
    progress_tracker: _ProgressTracker
    finalization_orchestrator: _FinalizationOrchestrator
    extract_message_data: Callable[
        [TelegramClient, Entity, Any, SourceInfo], Awaitable[Any]
    ]


class FetchDateRangeUseCase:
    """Process a single date range end-to-end."""

    def __init__(self, deps: FetchDateRangeDeps) -> None:
        """Initialize use case with dependencies."""
        self.d = deps

    async def execute(  # noqa: C901 - acceptable complexity for orchestrating steps
        self,
        *,
        client: TelegramClient,
        entity: Entity,
        source_info: SourceInfo,
        start_date: date,
        end_date: date,
        correlation_id: str,
    ) -> int:
        """Execute the date range processing pipeline.

        Args:
            client: Authenticated Telegram client
            entity: Telegram entity for the chat/channel
            source_info: Extracted source info
            start_date: Inclusive start date
            end_date: Inclusive end date
            correlation_id: Correlation id for logging
        """
        cfg = self.d.config

        # Skip if already completed
        if not cfg.force_refetch and self.d.progress_tracker.is_date_completed(
            source_info.id, start_date
        ):
            logger.info(
                "Skipping date range - already completed",
                extra={
                    "correlation_id": correlation_id,
                    "source": source_info.id,
                    "date": start_date.isoformat(),
                    "reason": "already_completed",
                    "force_refetch": False,
                },
            )
            return 0

        self.d.progress_tracker.mark_in_progress(source_info.id, start_date)

        # Create collection
        collection = self.d.repository.create_collection(
            source_info=source_info,
            messages=[],
        )

        # Boundaries
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        end_datetime = datetime.combine(
            end_date + timedelta(days=1), datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        # Idempotent skip by checksum
        if not cfg.force_refetch:
            decision = SkipExistingChecker(self.d.repository).decide(
                source_info.id, start_date
            )
            if decision.should_skip:
                # Reset gauge to clean state
                self.d.progress_service.reset_gauge(
                    source_info.id, start_date.isoformat()
                )
                return 0
        # Idempotency context: use last processed message id for this date if available
        last_processed_id: int | None = None
        # Optional in-run deduplication
        seen_ids: set[int] = set()
        try:
            sp = self.d.progress_tracker.get_source_progress(source_info.id)
            if sp and sp.last_processed_date == start_date.isoformat():
                last_processed_id = sp.last_message_id
        except Exception:
            logger.debug("Progress lookup failed for last_message_id", exc_info=True)

        # Iterate
        async def handle(msg):  # type: ignore[no-untyped-def]
            message_data = await self.d.extract_message_data(
                client, entity, msg, source_info
            )
            message_data = self.d.preprocessor.enrich(message_data)
            # Idempotency by last processed id (chat:date:last_message_id threshold)
            mid = getattr(message_data, "id", None)
            if isinstance(mid, int):
                # Skip if we've already processed up to this id for the same date
                if last_processed_id is not None and mid <= last_processed_id:
                    try:
                        from os import getenv

                        from src.observability.metrics import dedup_skipped_total

                        worker = getenv("HOSTNAME", "fetcher-1")
                        dedup_skipped_total.labels(
                            chat=source_info.id,
                            date=start_date.isoformat(),
                            reason="leq_last",
                            worker=worker,
                        ).inc()
                    except Exception:
                        pass
                    return False
                # Optional: skip duplicates encountered within the same run
                if self.d.config.dedup_in_run_enabled and mid in seen_ids:
                    try:
                        from os import getenv

                        from src.observability.metrics import dedup_skipped_total

                        worker = getenv("HOSTNAME", "fetcher-1")
                        dedup_skipped_total.labels(
                            chat=source_info.id,
                            date=start_date.isoformat(),
                            reason="seen_in_run",
                            worker=worker,
                        ).inc()
                    except Exception:
                        pass
                    return False
            if self.d.preprocessor.maybe_merge_short(
                collection.messages[-1] if collection.messages else None,
                message_data,
            ):
                return False
            collection.messages.append(message_data)
            # Track seen ids only if in-run dedup is enabled
            if (
                isinstance(getattr(message_data, "id", None), int)
                and self.d.config.dedup_in_run_enabled
            ):
                seen_ids.add(message_data.id)
            if getattr(message_data, "sender_id", None):
                sender_name = self.d.source_mapper.get_sender_name(
                    getattr(msg, "sender", None)
                )
                collection.add_sender(message_data.sender_id, sender_name)
            return True

        fetched, processed = await self.d.date_range_processor.iterate(
            client=client,
            entity=entity,
            source_info=source_info,
            start_date=start_date,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            correlation_id=correlation_id,
            handle=handle,
        )

        # Save
        file_path = None
        last_message_id = None
        if fetched > 0:
            file_path = self.d.repository.save_collection(
                source_name=source_info.id,
                target_date=start_date,
                collection=collection,
            )
            if getattr(collection, "messages", None):
                last_message = collection.messages[-1]
                last_message_id = last_message.id

        # Mark complete
        self.d.progress_tracker.mark_completed(
            source=source_info.id,
            target_date=start_date,
            message_count=fetched,
            last_message_id=last_message_id,
        )

        # Orchestrate finalize
        try:
            self.d.progress_service.publish_stage(
                chat=source_info.id,
                date=start_date.isoformat(),
                stage="saving",
            )
            self.d.finalization_orchestrator.finalize(
                source_info=source_info,
                start_date=start_date,
                collection=collection,
                messages_fetched=fetched,
                duration=0.0,  # duration can be provided by caller if needed
                file_path=file_path,
                checksum_fn=compute_file_checksum,
            )
        except Exception:
            logger.warning("Finalization failed (non-fatal)", exc_info=True)

        # Reset progress gauge
        self.d.progress_service.reset_gauge(source_info.id, start_date.isoformat())

        return fetched
