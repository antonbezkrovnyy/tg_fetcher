from __future__ import annotations

from typing import Any, Optional


class SkipReporter:
    """Reports skip events via ProgressService with legacy fallbacks.

    This consolidates the side effects of reporting a skipped fetch and
    resetting progress, while keeping backward compatibility with existing
    tests that rely on legacy event publisher and metrics.
    """

    def __init__(
        self,
        *,
        progress_service: Optional[Any] = None,
        event_publisher: Optional[Any] = None,
        metrics: Optional[Any] = None,
        config: Optional[Any] = None,
    ) -> None:
        self._ps = progress_service
        self._publisher = event_publisher
        self._metrics = metrics
        self._config = config

    def report_skipped(
        self,
        *,
        chat: str,
        date: str,
        reason: str,
        checksum_expected: Optional[str],
        checksum_actual: Optional[str],
    ) -> None:
        """Publish 'skipped' via preferred ProgressService or legacy fallback."""
        if self._ps is not None:
            self._ps.publish_skipped(
                chat=chat,
                date=date,
                reason=reason,
                checksum_expected=checksum_expected,
                checksum_actual=checksum_actual,
            )
            return

        enable_events = False
        if self._config is not None:
            enable_events = getattr(self._config, "enable_progress_events", False)

        if self._publisher is not None and enable_events:
            self._publisher.publish_fetch_skipped(
                chat=chat,
                date=date,
                reason=reason,
                checksum_expected=checksum_expected,
                checksum_actual=checksum_actual,
            )

    def reset_progress(self, *, chat: str, date: str) -> None:
        """Reset progress via ProgressService or legacy metrics fallback."""
        if self._ps is not None:
            self._ps.reset_gauge(chat=chat, date=date)
            return
        if self._metrics is not None:
            self._metrics.reset_progress(chat, date)
