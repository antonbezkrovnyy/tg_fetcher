"""Tests for fetch strategy implementations."""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from telethon import TelegramClient

from src.services.progress_tracker import Progress, ProgressTracker, SourceProgress
from src.services.strategy.base import BaseFetchStrategy
from src.services.strategy.by_date import ByDateStrategy
from src.services.strategy.full import FullHistoryStrategy
from src.services.strategy.incremental import IncrementalStrategy
from src.services.strategy.range import RangeStrategy
from src.services.strategy.yesterday import YesterdayOnlyStrategy as YesterdayStrategy


class TestYesterdayStrategy:
    """Tests for YesterdayStrategy."""

    @pytest.mark.asyncio
    async def test_get_date_ranges(self):
        """Should yield yesterday's date as both start and end."""
        strategy = YesterdayStrategy()
        client = MagicMock(spec=TelegramClient)
        chat = "@test_chat"

        yesterday = date.today() - timedelta(days=1)

        ranges = [r async for r in strategy.get_date_ranges(client, chat)]

        assert len(ranges) == 1
        assert ranges[0] == (yesterday, yesterday)

    def test_get_strategy_name(self):
        """Should return 'yesterday'."""
        strategy = YesterdayStrategy()
        assert strategy.get_strategy_name() == "yesterday"


class TestByDateStrategy:
    """Tests for ByDateStrategy."""

    @pytest.mark.asyncio
    async def test_get_date_ranges_valid_date(self):
        """Should yield the specified date as both start and end."""
        test_date = "2025-11-07"
        strategy = ByDateStrategy(test_date)
        client = MagicMock(spec=TelegramClient)
        chat = "@test_chat"

        ranges = [r async for r in strategy.get_date_ranges(client, chat)]

        expected_date = datetime.strptime(test_date, "%Y-%m-%d").date()
        assert len(ranges) == 1
        assert ranges[0] == (expected_date, expected_date)

    def test_invalid_date_format(self):
        """Should raise ValueError for invalid date format."""
        with pytest.raises(ValueError):
            ByDateStrategy("invalid-date")

    def test_get_strategy_name(self):
        """Should return 'date'."""
        strategy = ByDateStrategy("2025-11-07")
        assert strategy.get_strategy_name() == "date"


class TestFullHistoryStrategy:
    """Tests for FullHistoryStrategy."""

    @pytest.mark.asyncio
    async def test_get_date_ranges(self):
        """Should yield dates from yesterday back in weekly chunks."""
        strategy = FullHistoryStrategy()
        client = MagicMock(spec=TelegramClient)
        chat = "@test_chat"

        # Create a mock message with a date property
        mock_message = MagicMock()
        first_date = date(2025, 10, 1)  # Example first message date
        mock_message.date.date.return_value = first_date

        # Make client.get_entity return MagicMock
        entity = MagicMock()
        client.get_entity.return_value = entity

        # Make client.get_messages return list with our mock message
        client.get_messages.return_value = [mock_message]

        yesterday = date.today() - timedelta(days=1)

        ranges = [r async for r in strategy.get_date_ranges(client, chat)]

        # Helper for date range validation
        def validate_date_ranges(ranges):
            # Should have at least one range
            assert len(ranges) > 0, "Should have at least one date range"

            # Each range should cover at most 7 days
            for start, end in ranges:
                assert (
                    end - start
                ).days <= 7, f"Range {start} to {end} is more than 7 days"
                assert start <= end, f"Start date {start} after end date {end}"

            # Ranges should be ordered newest to oldest
            for i in range(len(ranges) - 1):
                curr_start, curr_end = ranges[i]
                next_start, next_end = ranges[i + 1]
                assert (
                    next_end < curr_start
                ), "Ranges should be continuous and ordered newest to oldest"

            # Should end at yesterday
            assert (
                ranges[0][1] == yesterday
            ), f"Latest date {ranges[0][1]} should be yesterday {yesterday}"

            # Should start at first_date
            assert (
                ranges[-1][0] == first_date
            ), f"Earliest date {ranges[-1][0]} should match first message {first_date}"

        validate_date_ranges(ranges)

    def test_get_strategy_name(self):
        """Should return 'full'."""
        strategy = FullHistoryStrategy()
        assert strategy.get_strategy_name() == "full"


@pytest.mark.asyncio
class TestIncrementalStrategy:
    """Tests for IncrementalStrategy."""

    @pytest.fixture
    def mock_progress_tracker(self):
        """Create mock ProgressTracker with configurable response (sync)."""
        tracker = Mock(spec=ProgressTracker)
        tracker.get_progress = Mock()
        return tracker

    async def test_get_date_ranges_with_progress(self, mock_progress_tracker):
        """Should yield ranges from last processed date to yesterday."""
        last_date = "2025-11-01"
        chat = "@test_chat"

        mock_progress_tracker.get_progress.return_value = Progress(
            sources={chat: SourceProgress(last_processed_date=last_date)}
        )

        strategy = IncrementalStrategy(mock_progress_tracker)
        client = MagicMock(spec=TelegramClient)

        ranges = [r async for r in strategy.get_date_ranges(client, chat)]

        start_date = datetime.strptime(last_date, "%Y-%m-%d").date() + timedelta(days=1)
        yesterday = date.today() - timedelta(days=1)

        # Verify ranges cover from start_date to yesterday in weekly chunks
        assert ranges[0][0] == start_date
        assert ranges[-1][1] == yesterday

        for start, end in ranges:
            assert (end - start).days <= 7  # Max 7 days per chunk
            assert start <= end  # Valid range

    async def test_get_date_ranges_no_progress(self, mock_progress_tracker):
        """Should yield only yesterday's date when no progress exists."""
        chat = "@test_chat"
        mock_progress_tracker.get_progress.return_value = Progress(sources={})

        strategy = IncrementalStrategy(mock_progress_tracker)
        client = MagicMock(spec=TelegramClient)

        ranges = [r async for r in strategy.get_date_ranges(client, chat)]

        yesterday = date.today() - timedelta(days=1)
        assert len(ranges) == 1
        assert ranges[0][0] == yesterday
        assert ranges[0][1] == yesterday

    async def test_get_date_ranges_invalid_progress_date(self, mock_progress_tracker):
        """Should handle invalid date in progress gracefully."""
        chat = "@test_chat"
        mock_progress_tracker.get_progress.return_value = Progress(
            sources={chat: SourceProgress(last_processed_date="invalid-date")}
        )

        strategy = IncrementalStrategy(mock_progress_tracker)
        client = MagicMock(spec=TelegramClient)

        ranges = [r async for r in strategy.get_date_ranges(client, chat)]
        assert len(ranges) == 0  # Should yield nothing for invalid date

    async def test_get_strategy_name(self):
        """Should return 'incremental'."""
        strategy = IncrementalStrategy(MagicMock(spec=ProgressTracker))
        assert strategy.get_strategy_name() == "incremental"


class TestRangeStrategy:
    """Tests for RangeStrategy."""

    @pytest.mark.asyncio
    async def test_get_date_ranges_valid_dates(self):
        """Should yield weekly chunks between start and end dates."""
        strategy = RangeStrategy("2025-11-01", "2025-11-15")
        client = MagicMock(spec=TelegramClient)
        chat = "@test_chat"

        ranges = [r async for r in strategy.get_date_ranges(client, chat)]

        start_date = datetime.strptime("2025-11-01", "%Y-%m-%d").date()
        end_date = datetime.strptime("2025-11-15", "%Y-%m-%d").date()

        # Verify ranges cover full date range in weekly chunks
        assert ranges[0][0] == start_date
        assert ranges[-1][1] == end_date

        for start, end in ranges:
            assert (end - start).days <= 7  # Max 7 days per chunk
            assert start <= end  # Valid range

    def test_invalid_date_format(self):
        """Should raise ValueError for invalid date formats."""
        with pytest.raises(ValueError):
            RangeStrategy("invalid", "2025-11-15")

        with pytest.raises(ValueError):
            RangeStrategy("2025-11-01", "invalid")

    def test_end_before_start(self):
        """Should raise ValueError if end date is before start date."""
        with pytest.raises(ValueError):
            RangeStrategy("2025-11-15", "2025-11-01")

    def test_get_strategy_name(self):
        """Should return 'range'."""
        strategy = RangeStrategy("2025-11-01", "2025-11-15")
        assert strategy.get_strategy_name() == "range"
