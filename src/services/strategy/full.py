"""Full history fetch strategy.

Implements strategy for fetching all messages from the beginning
of channel/chat history up to yesterday.
"""

from collections.abc import AsyncIterator
from datetime import date, timedelta

from telethon import TelegramClient
from telethon.tl.types import Message

from src.observability.logging_config import get_logger
from src.services.strategy.base import BaseFetchStrategy

logger = get_logger(__name__)


class FullHistoryStrategy(BaseFetchStrategy):
    """Strategy for fetching complete message history.

    Fetches all messages from the first message up to yesterday,
    processing them in date-based chunks to maintain progress
    and allow resumption.
    """

    async def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Get date ranges from first message to yesterday.

        Args:
            client: Connected TelegramClient instance
            chat_identifier: Chat/channel username or ID

        Yields:
            Tuples of (start_date, end_date) for each chunk,
            moving from oldest to newest messages
        """
        # Get entity (channel/chat)
        entity = await client.get_entity(chat_identifier)

        # Get first message to determine start date
        messages = await client.get_messages(
            entity, limit=1, reverse=True  # Get oldest messages first
        )

        if not messages:
            logger.warning("No messages found in chat", extra={"chat": chat_identifier})
            return

        first_message: Message = messages[0]
        start_date = first_message.date.date()
        yesterday = date.today() - timedelta(days=1)

        if start_date >= yesterday:
            logger.info(
                "Chat history starts today/yesterday, nothing to fetch in full mode",
                extra={
                    "chat": chat_identifier,
                    "start_date": start_date.isoformat(),
                    "yesterday": yesterday.isoformat(),
                },
            )
            return

        # Calculate all date ranges first
        date_ranges = []
        current_date = start_date
        chunk_size = timedelta(days=7)  # Process week at a time

        while current_date < yesterday:
            chunk_end = min(current_date + chunk_size, yesterday)

            date_ranges.append((current_date, chunk_end))
            current_date = chunk_end + timedelta(days=1)

        # Yield in reverse order - newest to oldest
        for start_date, end_date in reversed(date_ranges):
            logger.info(
                "Yielding date range for full history fetch",
                extra={
                    "chat": chat_identifier,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )
            yield (start_date, end_date)

    def get_strategy_name(self) -> str:
        """Get the name of this strategy.

        Returns:
            'full' - indicating full history fetch mode
        """
        return "full"
