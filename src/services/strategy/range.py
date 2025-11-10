"""Range fetch strategy.

Implementation of strategy for fetching messages between two specified dates.
"""

from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta

from telethon import TelegramClient

from src.observability.logging_config import get_logger
from src.services.strategy.base import BaseFetchStrategy

logger = get_logger(__name__)


class RangeStrategy(BaseFetchStrategy):
    """Strategy for fetching messages in a specific date range.

    Fetches messages between specified start and end dates. Processes in chunks
    to avoid memory issues with large date ranges.
    """

    def __init__(self, start_date: str, end_date: str):
        """Initialize range strategy.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format (inclusive)

        Raises:
            ValueError: If dates are invalid or end_date is before start_date
        """
        try:
            self.start = datetime.strptime(start_date, "%Y-%m-%d").date()
            self.end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError as e:
            raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}")

        if self.end < self.start:
            raise ValueError(
                f"End date {end_date} cannot be before start date {start_date}"
            )

        logger.info(
            "Initialized range strategy",
            extra={"start_date": start_date, "end_date": end_date},
        )

    async def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Get date ranges between specified start and end dates.

        Args:
            client: Connected TelegramClient instance
            chat_identifier: Chat/channel username or ID

        Yields:
            Tuples of (start_date, end_date) for each chunk to process
        """
        # Process in reasonable chunks
        current_date = self.start
        chunk_size = timedelta(days=7)  # Week at a time

        while current_date <= self.end:
            chunk_end = min(current_date + chunk_size, self.end)

            logger.info(
                "Yielding date range chunk",
                extra={
                    "chat": chat_identifier,
                    "start_date": current_date.isoformat(),
                    "end_date": chunk_end.isoformat(),
                },
            )

            yield (current_date, chunk_end)
            current_date = chunk_end + timedelta(days=1)

    def get_strategy_name(self) -> str:
        """Get the name of this strategy.

        Returns:
            'range' - indicating date range fetch mode
        """
        return "range"
