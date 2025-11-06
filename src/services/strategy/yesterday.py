"""Yesterday-only fetch strategy."""

from collections.abc import AsyncIterator
from datetime import date, timedelta

from telethon import TelegramClient

from src.observability.logging_config import get_logger
from src.services.strategy.base import BaseFetchStrategy

logger = get_logger(__name__)


class YesterdayOnlyStrategy(BaseFetchStrategy):
    """Fetch strategy that only collects messages from yesterday.

    This is the default/MVP strategy that fetches messages for a single day
    (yesterday) without maintaining progress state.
    """

    async def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Get yesterday's date range.

        Args:
            client: Telegram client instance
            chat_identifier: Chat username or ID

        Yields:
            Single tuple of (yesterday, yesterday)
        """
        yesterday = date.today() - timedelta(days=1)

        logger.info(
            "Yesterday-only strategy: fetching single day",
            extra={"chat": chat_identifier, "date": yesterday.isoformat()},
        )

        yield (yesterday, yesterday)

    def get_strategy_name(self) -> str:
        """Get strategy name.

        Returns:
            'yesterday'
        """
        return "yesterday"
