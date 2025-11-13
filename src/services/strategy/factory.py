"""Factory for creating fetch strategies based on configuration.

This decouples strategy selection from the FetcherService and allows IoC.
"""

from __future__ import annotations

from typing import Optional

from src.core.config import FetcherConfig
from src.services.strategy.base import BaseFetchStrategy
from src.services.strategy.yesterday import YesterdayOnlyStrategy


class StrategyFactory:
    """Create strategies according to config (and optional date).

    Inputs:
      - config: FetcherConfig with fetch_mode and optional fetch_date
      - date_str: Optional ISO date string override

    Output:
      - BaseFetchStrategy implementation
    """

    def __init__(self, config: FetcherConfig) -> None:
        self._config = config

    def create(self, date_str: Optional[str] = None) -> BaseFetchStrategy:
        """Return strategy for current config.

        Raises:
            ValueError: if fetch_mode is unsupported
        """
        mode = self._config.fetch_mode
        if mode == "date":
            if not date_str:
                # fall back to config.fetch_date if available
                if self._config.fetch_date is None:
                    raise ValueError("fetch_date is required for date mode")
                date_str = self._config.fetch_date.isoformat()
            from src.services.strategy.by_date import ByDateStrategy

            return ByDateStrategy(date_str)
        if mode == "yesterday":
            return YesterdayOnlyStrategy()
        raise ValueError(f"Unsupported fetch_mode: {mode}")
