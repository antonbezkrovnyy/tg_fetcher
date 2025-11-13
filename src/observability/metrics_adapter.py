"""Metrics Adapter abstraction to decouple Prometheus from services.

Provides a minimal interface for progress metrics with a Prometheus-backed
implementation and a no-op fallback. This enables Dependency Inversion and
easier testing while keeping FetcherService free of direct Prometheus usage.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

from src.observability.metrics import (
    commands_failed_total,
    commands_received_total,
    commands_success_total,
    commands_timeout_total,
    fetch_progress_messages_current,
)

logger = logging.getLogger(__name__)


class MetricsAdapter(Protocol):
    """Abstract metrics interface used by services.

    Currently limited to progress gauge updates, can be extended later.
    """

    def set_progress(self, chat: str, date_str: str, value: int) -> None:
        """Set current progress value for a chat/date."""

    def reset_progress(self, chat: str, date_str: str) -> None:
        """Reset current progress to 0 for a chat/date."""

    # --- Command subscriber counters ---
    def inc_command_received(self, queue: str, worker: str) -> None:
        """Increment when a command JSON is received from Redis."""

    def inc_command_success(self, queue: str, worker: str) -> None:
        """Increment when a command is handled successfully."""

    def inc_command_failed(self, queue: str, worker: str, error_type: str) -> None:
        """Increment when command handling fails with an error type."""

    def inc_command_timeout(self, queue: str, worker: str) -> None:
        """Increment when BLPOP times out without receiving a command."""


class PrometheusMetricsAdapter:
    """Prometheus-backed metrics adapter.

    Handles exceptions internally to avoid impacting the main workflow.
    """

    def __init__(self) -> None:
        """Initialize adapter and cache worker identifier."""
        self._worker_id = os.getenv("HOSTNAME", "fetcher-1")

    def set_progress(self, chat: str, date_str: str, value: int) -> None:
        """Set gauge to the given value for (chat, date)."""
        try:
            fetch_progress_messages_current.labels(
                chat=chat, date=date_str, worker=self._worker_id
            ).set(value)
        except Exception:
            logger.debug(
                "Prometheus set_progress failed (non-fatal)",
                extra={"chat": chat, "date": date_str, "value": value},
                exc_info=True,
            )

    def reset_progress(self, chat: str, date_str: str) -> None:
        """Reset gauge to zero for (chat, date)."""
        try:
            fetch_progress_messages_current.labels(
                chat=chat, date=date_str, worker=self._worker_id
            ).set(0)
        except Exception:
            logger.debug(
                "Prometheus reset_progress failed (non-fatal)",
                extra={"chat": chat, "date": date_str},
                exc_info=True,
            )

    # --- Command subscriber counters ---
    def inc_command_received(self, queue: str, worker: str) -> None:
        try:
            commands_received_total.labels(queue=queue, worker=worker).inc()
        except Exception:
            logger.debug("Prometheus inc_command_received failed", exc_info=True)

    def inc_command_success(self, queue: str, worker: str) -> None:
        try:
            commands_success_total.labels(queue=queue, worker=worker).inc()
        except Exception:
            logger.debug("Prometheus inc_command_success failed", exc_info=True)

    def inc_command_failed(self, queue: str, worker: str, error_type: str) -> None:
        try:
            commands_failed_total.labels(
                queue=queue, worker=worker, error_type=error_type
            ).inc()
        except Exception:
            logger.debug("Prometheus inc_command_failed failed", exc_info=True)

    def inc_command_timeout(self, queue: str, worker: str) -> None:
        try:
            commands_timeout_total.labels(queue=queue, worker=worker).inc()
        except Exception:
            logger.debug("Prometheus inc_command_timeout failed", exc_info=True)


class NoopMetricsAdapter:
    """No-op adapter used when metrics are disabled."""

    def set_progress(self, chat: str, date_str: str, value: int) -> None:
        """No-op: do nothing."""
        return

    def reset_progress(self, chat: str, date_str: str) -> None:
        """No-op: do nothing."""
        return

    # --- Command subscriber counters ---
    def inc_command_received(self, queue: str, worker: str) -> None:  # noqa: ARG002
        return

    def inc_command_success(self, queue: str, worker: str) -> None:  # noqa: ARG002
        return

    def inc_command_failed(
        self, queue: str, worker: str, error_type: str
    ) -> None:  # noqa: ARG002
        return

    def inc_command_timeout(self, queue: str, worker: str) -> None:  # noqa: ARG002
        return
