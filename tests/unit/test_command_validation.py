"""Unit tests for FetchCommand model validation and normalization."""

import pytest
from datetime import date, timedelta
from pydantic import ValidationError

from src.models.command import FetchCommand, FetchMode, FetchStrategy


class TestFetchCommandValidation:
    """Test command validation for all fetch modes."""

    def test_date_mode_valid(self):
        """Test valid DATE mode command."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.mode == FetchMode.DATE
        assert cmd.date == date(2025, 1, 15)
        assert cmd.days is None
        assert cmd.from_date is None
        assert cmd.to_date is None

    def test_days_mode_valid(self):
        """Test valid DAYS mode command."""
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=7, strategy=FetchStrategy.BATCH
        )
        assert cmd.mode == FetchMode.DAYS
        assert cmd.days == 7
        assert cmd.date is None
        assert cmd.from_date is None
        assert cmd.to_date is None

    def test_range_mode_valid(self):
        """Test valid RANGE mode command."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 1, 1),
            to_date=date(2025, 1, 10),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.mode == FetchMode.RANGE
        assert cmd.from_date == date(2025, 1, 1)
        assert cmd.to_date == date(2025, 1, 10)
        assert cmd.date is None
        assert cmd.days is None

    def test_date_mode_missing_date(self):
        """Test DATE mode fails without date field."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DATE, strategy=FetchStrategy.BATCH
            )
        errors = exc_info.value.errors()
        assert any("date" in str(e) for e in errors)

    def test_days_mode_missing_days(self):
        """Test DAYS mode fails without days field."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, strategy=FetchStrategy.BATCH
            )
        errors = exc_info.value.errors()
        assert any("days" in str(e) for e in errors)

    def test_range_mode_missing_dates(self):
        """Test RANGE mode fails without from_date/to_date."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.RANGE, strategy=FetchStrategy.BATCH
            )
        errors = exc_info.value.errors()
        assert any("from" in str(e) or "to" in str(e) for e in errors)

    def test_range_mode_backwards_dates(self):
        """Test RANGE mode fails with backwards date range."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(command="fetch", chat="@testchat",
                mode=FetchMode.RANGE,
                from_date=date(2025, 1, 10),
                to_date=date(2025, 1, 1),
                strategy=FetchStrategy.BATCH,
            )
        errors = exc_info.value.errors()
        assert any("from" in str(e) or "to" in str(e) or "Value error" in str(e) for e in errors)

    def test_days_zero(self):
        """Test DAYS mode fails with zero days."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=0, strategy=FetchStrategy.BATCH
            )
        errors = exc_info.value.errors()
        assert any("days" in str(e) and "greater than" in str(e) for e in errors)

    def test_days_negative(self):
        """Test DAYS mode fails with negative days."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(command="fetch", chat="@testchat",
                mode=FetchMode.DAYS,
                days=-5,
                strategy=FetchStrategy.BATCH,
            )
        errors = exc_info.value.errors()
        assert any("days" in str(e) and "greater than" in str(e) for e in errors)

    def test_missing_chat(self):
        """Test command fails without chat."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(
                mode=FetchMode.DATE, date=date(2025, 1, 15), strategy=FetchStrategy.BATCH
            )
        errors = exc_info.value.errors()
        assert any("chat" in str(e) for e in errors)

    def test_empty_chat(self):
        """Test command fails with empty chat."""
        with pytest.raises(ValidationError) as exc_info:
            FetchCommand(command="fetch", chat="", mode=FetchMode.DATE, date=date(2025, 1, 15), strategy=FetchStrategy.BATCH
            )
        errors = exc_info.value.errors()
        assert any("chat" in str(e) for e in errors)


class TestChatNormalization:
    """Test chat identifier normalization."""

    def test_normalize_username_with_at(self):
        """Test username starting with @ is preserved."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.chat == "@testchat"

    def test_normalize_username_without_at(self):
        """Test username without @ gets @ prepended."""
        cmd = FetchCommand(command="fetch", chat="testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.chat == "@testchat"

    def test_normalize_numeric_id(self):
        """Test numeric chat ID is preserved."""
        cmd = FetchCommand(command="fetch", chat="123456789",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.chat == "123456789"

    def test_normalize_negative_id(self):
        """Test negative chat ID is preserved."""
        cmd = FetchCommand(command="fetch", chat="-123456789",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.chat == "-123456789"

    def test_normalize_whitespace_trimmed(self):
        """Test leading/trailing whitespace is trimmed."""
        cmd = FetchCommand(command="fetch", chat="  @testchat  ",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.chat == "@testchat"

    def test_normalize_mixed_case_username(self):
        """Test username case is preserved."""
        cmd = FetchCommand(command="fetch", chat="@TestChat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.chat == "@TestChat"


class TestForceFlag:
    """Test force re-fetch flag behavior."""

    def test_force_default_false(self):
        """Test force flag defaults to False."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.force is False

    def test_force_explicit_true(self):
        """Test force flag can be set to True."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
            force=True,
        )
        assert cmd.force is True

    def test_force_explicit_false(self):
        """Test force flag can be explicitly False."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
            force=False,
        )
        assert cmd.force is False


class TestDefaultValues:
    """Test default values for optional fields."""

    def test_strategy_default_batch(self):
        """Test strategy defaults to BATCH."""
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DATE, date=date(2025, 1, 15)
        )
        assert cmd.strategy == FetchStrategy.BATCH

    def test_explicit_per_day_strategy(self):
        """Test PER_DAY strategy can be set explicitly."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.PER_DAY,
        )
        assert cmd.strategy == FetchStrategy.PER_DAY


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_date_today(self):
        """Test command with today's date."""
        today = date.today()
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DATE, date=today, strategy=FetchStrategy.BATCH
        )
        assert cmd.date == today

    def test_date_far_past(self):
        """Test command with date far in the past."""
        old_date = date(2010, 1, 1)
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.DATE,
            date=old_date,
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.date == old_date

    def test_days_single_day(self):
        """Test DAYS mode with single day."""
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=1, strategy=FetchStrategy.BATCH
        )
        assert cmd.days == 1

    def test_days_large_number(self):
        """Test DAYS mode with large number of days."""
        cmd = FetchCommand(command="fetch", chat="@testchat", mode=FetchMode.DAYS, days=365, strategy=FetchStrategy.BATCH
        )
        assert cmd.days == 365

    def test_range_single_day(self):
        """Test RANGE mode with same start and end date."""
        target_date = date(2025, 1, 15)
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=target_date,
            to_date=target_date,
            strategy=FetchStrategy.BATCH,
        )
        assert cmd.from_date == target_date
        assert cmd.to_date == target_date

    def test_range_large_span(self):
        """Test RANGE mode with large date span."""
        cmd = FetchCommand(command="fetch", chat="@testchat",
            mode=FetchMode.RANGE,
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31),
            strategy=FetchStrategy.BATCH,
        )
        assert (cmd.to_date - cmd.from_date).days == 365
