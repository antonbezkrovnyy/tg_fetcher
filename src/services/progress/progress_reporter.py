"""ProgressReporter: unified wrapper over ProgressService.

This optional layer keeps call sites clean and centralizes potential schema
adjustments for progress events and gauges.
"""

from __future__ import annotations

from typing import Optional

from src.services.progress.progress_service import ProgressService


class ProgressReporter:
    """Simple pass-through wrapper with a stable API surface."""

    def __init__(self, progress_service: ProgressService) -> None:
        """Initialize reporter.

        Args:
            progress_service: Underlying ProgressService facade
        """
        self._ps = progress_service

    # Metrics
    def reset(self, chat: str, date: str) -> None:
        """Reset per-date progress gauge to 0."""
        self._ps.reset_gauge(chat, date)

    def set(self, chat: str, date: str, value: int) -> None:
        """Set per-date progress gauge to a specific value."""
        self._ps.set_progress(chat, date, value)

    # Events
    def stage(self, *, chat: str, date: str, stage: str) -> None:
        """Publish stage event for a chat/date."""
        self._ps.publish_stage(chat=chat, date=date, stage=stage)

    def skipped(
        self,
        *,
        chat: str,
        date: str,
        reason: str,
        checksum_expected: Optional[str],
        checksum_actual: Optional[str],
    ) -> None:
        """Publish skipped event with optional checksum context."""
        self._ps.publish_skipped(
            chat=chat,
            date=date,
            reason=reason,
            checksum_expected=checksum_expected,
            checksum_actual=checksum_actual,
        )

    def complete(
        self,
        *,
        chat: str,
        date: str,
        message_count: int,
        file_path: str,
        duration_seconds: float,
    ) -> None:
        """Publish completion event for a chat/date."""
        self._ps.publish_complete(
            chat=chat,
            date=date,
            message_count=message_count,
            file_path=file_path,
            duration_seconds=duration_seconds,
        )
