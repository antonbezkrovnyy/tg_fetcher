"""Fetch strategy for a specific date from Redis command."""

from collections.abc import AsyncIterator
from datetime import date, datetime

from telethon import TelegramClient

from src.observability.logging_config import get_logger
from src.services.strategy.base import BaseFetchStrategy

logger = get_logger(__name__)


class ByDateStrategy(BaseFetchStrategy):
    """Fetch strategy for a specific date (YYYY-MM-DD)."""

    def __init__(self, date_str: str):
        """Initialize strategy with target date.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Raises:
            ValueError: If date format is invalid
        """
        try:
            self.target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as e:
            logger.error(f"Invalid date format: {date_str}")
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD: {e}")

    def get_strategy_name(self) -> str:
        """Get name of the strategy."""
        return "date"

    async def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Yield single date range for the requested date."""
        if self.target_date:
            logger.info(
                "ByDate strategy: fetching single day",
                extra={"chat": chat_identifier, "date": self.target_date.isoformat()},
            )
            yield (self.target_date, self.target_date)
        else:
            logger.error("No valid date for ByDateStrategy, skipping fetch.")
            return
