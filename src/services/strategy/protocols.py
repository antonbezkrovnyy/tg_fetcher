"""Strategy protocol for fetch strategies.

Defines the minimal surface used by orchestration and use-cases.
"""

from __future__ import annotations

from datetime import date
from typing import AsyncIterator, Protocol


class StrategyProtocol(Protocol):
    """Minimal contract required from a strategy implementation."""

    def get_strategy_name(self) -> str:
        """Return human-readable strategy name for logging/metrics."""

    def get_date_ranges(
        self, client: object, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Yield inclusive date ranges to process for the given chat."""
