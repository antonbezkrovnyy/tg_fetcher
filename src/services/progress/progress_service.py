"""ProgressService facade.

Provides safe wrappers around metrics updates and event publishing to reduce
boilerplate in FetcherService and keep concerns separated (DRY).
"""

from __future__ import annotations

from typing import Optional

from src.observability.metrics_adapter import MetricsAdapter
from src.services.event_publisher import EventPublisherProtocol


class ProgressService:
    """Facade for progress metrics and event publishing (best-effort)."""

    def __init__(
        self,
        *,
        metrics: MetricsAdapter,
        event_publisher: Optional[EventPublisherProtocol],
        enable_events: bool,
    ) -> None:
        self._metrics = metrics
        self._publisher = event_publisher
        self._enable_events = enable_events

    # Metrics
    def reset_gauge(self, chat: str, date: str) -> None:
        try:
            self._metrics.reset_progress(chat, date)
        except Exception:
            # best-effort
            pass

    def set_progress(self, chat: str, date: str, value: int) -> None:
        try:
            self._metrics.set_progress(chat, date, value)
        except Exception:
            # best-effort
            pass

    # Events (best-effort, only if enabled)
    def publish_stage(self, *, chat: str, date: str, stage: str) -> None:
        if not (self._enable_events and self._publisher):
            return
        try:
            self._publisher.publish_fetch_stage(chat=chat, date=date, stage=stage)
        except Exception:
            pass

    def publish_skipped(
        self,
        *,
        chat: str,
        date: str,
        reason: str,
        checksum_expected: Optional[str],
        checksum_actual: Optional[str],
    ) -> None:
        if not (self._enable_events and self._publisher):
            return
        try:
            self._publisher.publish_fetch_skipped(
                chat=chat,
                date=date,
                reason=reason,
                checksum_expected=checksum_expected,
                checksum_actual=checksum_actual,
            )
        except Exception:
            pass

    def publish_complete(
        self,
        *,
        chat: str,
        date: str,
        message_count: int,
        file_path: str,
        duration_seconds: float,
    ) -> None:
        if not (self._enable_events and self._publisher):
            return
        try:
            self._publisher.publish_fetch_complete(
                chat=chat,
                date=date,
                message_count=message_count,
                file_path=file_path,
                duration_seconds=duration_seconds,
            )
        except Exception:
            pass
