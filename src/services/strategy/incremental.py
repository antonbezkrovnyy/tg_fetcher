"""Incremental fetch strategy.

Implementation of strategy for fetching messages from last processed
date up to yesterday, maintaining progress state.
"""

from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta

from telethon import TelegramClient

from src.observability.logging_config import get_logger
from src.services.progress_tracker import ProgressTracker
from src.services.strategy.base import BaseFetchStrategy

logger = get_logger(__name__)


class IncrementalStrategy(BaseFetchStrategy):
    """Strategy for incremental message fetching.

    Fetches messages from the last processed date (from progress tracker)
    up to yesterday. If no progress data exists, behaves like full history
    fetch.
    """

    def __init__(self, progress_tracker: ProgressTracker):
        """Initialize incremental strategy.

        Args:
            progress_tracker: Instance to check last processed dates
        """
        self.progress_tracker = progress_tracker

    async def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        """Get date ranges from last processed to yesterday.

        Args:
            client: Connected TelegramClient instance
            chat_identifier: Chat/channel username or ID

        Yields:
            Tuples of (start_date, end_date) for each chunk to process
        """
        # Get last processed date for this chat
        progress = await self.progress_tracker.get_progress()
        source_progress = progress.sources.get(chat_identifier)

        if source_progress and source_progress.last_processed_date:
            try:
                last_date = datetime.strptime(
                    source_progress.last_processed_date, "%Y-%m-%d"
                ).date()

                # Add one day to avoid re-processing last date
                start_date = last_date + timedelta(days=1)
            except ValueError:
                logger.error(
                    "Invalid date format in progress",
                    extra={
                        "chat": chat_identifier,
                        "last_processed_date": source_progress.last_processed_date,
                    },
                )
                return
        else:
            # No progress data - start from yesterday
            start_date = date.today() - timedelta(days=1)
            logger.info(
                "No progress data, starting from yesterday",
                extra={"chat": chat_identifier, "start_date": start_date.isoformat()},
            )

        yesterday = date.today() - timedelta(days=1)

        if start_date > yesterday:
            logger.info(
                "Already up to date, nothing to fetch",
                extra={
                    "chat": chat_identifier,
                    "last_date": start_date.isoformat(),
                    "yesterday": yesterday.isoformat(),
                },
            )
            return

        # Process in reasonable chunks
        current_date = start_date
        chunk_size = timedelta(days=7)  # Week at a time

        while current_date <= yesterday:
            chunk_end = min(current_date + chunk_size, yesterday)

            logger.info(
                "Yielding date range for incremental fetch",
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
            'incremental' - indicating incremental fetch mode
        """
        return "incremental"
