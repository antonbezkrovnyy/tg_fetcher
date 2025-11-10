"""Unit tests for FetchCommand.expand_dates() method."""

import pytest
from datetime import date, timedelta

from src.models.command import FetchCommand, FetchMode, FetchStrategy


class TestDateModeExpansion:
    """Test date expansion for DATE mode."""

    def test_date_mode_single_date(self):
        """Test DATE mode expands to single date."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert dates == [date(2025, 1, 15)]

    def test_date_mode_today(self):
        """Test DATE mode with today's date."""
        today = date.today()
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DATE, date=today, strategy=FetchStrategy.BATCH
        )
        dates = cmd.expand_dates()
        assert dates == [today]

    def test_date_mode_past(self):
        """Test DATE mode with date in the past."""
        past_date = date(2020, 6, 15)
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=past_date,
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert dates == [past_date]


class TestDaysModeExpansion:
    """Test date expansion for DAYS mode."""

    def test_days_mode_single_day(self):
        """Test DAYS mode with 1 day."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=1, strategy=FetchStrategy.BATCH
        )
        dates = cmd.expand_dates()
        assert len(dates) == 1
        assert dates[0] == yesterday

    def test_days_mode_multiple_days(self):
        """Test DAYS mode with multiple days."""
        today = date.today()
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=7, strategy=FetchStrategy.BATCH
        )
        dates = cmd.expand_dates()
        assert len(dates) == 7
        expected = [today - timedelta(days=i) for i in range(1, 8)]
        assert dates == expected

    def test_days_mode_large_range(self):
        """Test DAYS mode with large number of days."""
        today = date.today()
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=30, strategy=FetchStrategy.BATCH
        )
        dates = cmd.expand_dates()
        assert len(dates) == 30
        assert dates[0] == today - timedelta(days=1)
        assert dates[-1] == today - timedelta(days=30)

    def test_days_mode_order(self):
        """Test DAYS mode returns dates in descending order (newest first)."""
        today = date.today()
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=5, strategy=FetchStrategy.BATCH
        )
        dates = cmd.expand_dates()
        for i in range(len(dates) - 1):
            assert dates[i] > dates[i + 1], "Dates should be in descending order"

    def test_days_mode_no_duplicates(self):
        """Test DAYS mode produces unique dates."""
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=10, strategy=FetchStrategy.BATCH
        )
        dates = cmd.expand_dates()
        assert len(dates) == len(set(dates)), "Dates should be unique"


class TestRangeModeExpansion:
    """Test date expansion for RANGE mode."""

    def test_range_mode_single_day(self):
        """Test RANGE mode with same start and end date."""
        target_date = date(2025, 1, 15)
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=target_date,
            to_date=target_date,
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert dates == [target_date]

    def test_range_mode_multiple_days(self):
        """Test RANGE mode with date range."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 10),
            to_date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert len(dates) == 6
        expected = [date(2025, 1, 10 + i) for i in range(6)]
        assert dates == expected

    def test_range_mode_month_span(self):
        """Test RANGE mode spanning entire month."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert len(dates) == 31
        assert dates[0] == date(2025, 1, 1)
        assert dates[-1] == date(2025, 1, 31)

    def test_range_mode_leap_year(self):
        """Test RANGE mode with leap year February."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2024, 2, 1),
            to_date=date(2024, 2, 29),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert len(dates) == 29
        assert date(2024, 2, 29) in dates

    def test_range_mode_year_boundary(self):
        """Test RANGE mode crossing year boundary."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2024, 12, 30),
            to_date=date(2025, 1, 2),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert len(dates) == 4
        assert dates == [
            date(2024, 12, 30),
            date(2024, 12, 31),
            date(2025, 1, 1),
            date(2025, 1, 2),
        ]

    def test_range_mode_order(self):
        """Test RANGE mode returns dates in ascending order."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 10),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        for i in range(len(dates) - 1):
            assert dates[i] < dates[i + 1], "Dates should be in ascending order"

    def test_range_mode_no_duplicates(self):
        """Test RANGE mode produces unique dates."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 31),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert len(dates) == len(set(dates)), "Dates should be unique"

    def test_range_mode_large_span(self):
        """Test RANGE mode with large date span."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert len(dates) == 366  # 2024 is leap year
        assert dates[0] == date(2024, 1, 1)
        assert dates[-1] == date(2024, 12, 31)


class TestExpansionConsistency:
    """Test consistency across different expansion methods."""

    def test_days_equals_range(self):
        """Test DAYS mode produces same dates as equivalent RANGE."""
        today = date.today()
        days_cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=7, strategy=FetchStrategy.BATCH
        )
        range_cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=today - timedelta(days=7),
            to_date=today - timedelta(days=1),
            strategy=FetchStrategy.BATCH,
        )

        days_dates = sorted(days_cmd.expand_dates())
        range_dates = sorted(range_cmd.expand_dates())

        assert days_dates == range_dates

    def test_date_equals_single_day_range(self):
        """Test DATE mode produces same result as single-day RANGE."""
        target_date = date(2025, 1, 15)
        date_cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=target_date,
            strategy=FetchStrategy.BATCH,
        )
        range_cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=target_date,
            to_date=target_date,
            strategy=FetchStrategy.BATCH,
        )

        assert date_cmd.expand_dates() == range_cmd.expand_dates()

    def test_date_equals_single_day_days(self):
        """Test DATE mode with yesterday equals DAYS mode with 1 day."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        date_cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DATE, date=yesterday, strategy=FetchStrategy.BATCH
        )
        days_cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=1, strategy=FetchStrategy.BATCH
        )

        assert date_cmd.expand_dates() == days_cmd.expand_dates()


class TestExpansionBoundaries:
    """Test boundary conditions in date expansion."""

    def test_days_boundary_midnight(self):
        """Test DAYS mode at day boundary (conceptual test)."""
        # This test documents that DAYS mode starts from yesterday (today-1)
        # which is timezone-dependent
        today = date.today()
        yesterday = today - timedelta(days=1)
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=1, strategy=FetchStrategy.BATCH
        )
        dates = cmd.expand_dates()
        assert dates[0] == yesterday

    def test_range_includes_both_endpoints(self):
        """Test RANGE mode includes both start and end dates."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 3),
            strategy=FetchStrategy.BATCH,
        )
        dates = cmd.expand_dates()
        assert date(2025, 1, 1) in dates
        assert date(2025, 1, 3) in dates

    def test_expansion_deterministic(self):
        """Test date expansion is deterministic (same input = same output)."""
        cmd1 = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 10),
            strategy=FetchStrategy.BATCH,
        )
        cmd2 = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 10),
            strategy=FetchStrategy.BATCH,
        )

        assert cmd1.expand_dates() == cmd2.expand_dates()
