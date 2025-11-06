"""Base strategy interface for fetch modes."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import date

from telethon import TelegramClient


class BaseFetchStrategy(ABC):
    """Base class for fetch strategies.

    Defines interface for different fetch modes (yesterday, full, incremental, etc.).
    """

    @abstractmethod
    def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Get date ranges to fetch for a given chat.

        Args:
            client: Telegram client instance
            chat_identifier: Chat username or ID

        Yields:
            Tuples of (start_date, end_date) to fetch
        """
        ...

    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get the name of the strategy.

        Returns:
            Strategy name
        """
        pass
