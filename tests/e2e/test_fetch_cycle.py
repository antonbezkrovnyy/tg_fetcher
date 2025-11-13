"""End-to-end smoke tests for fetch cycle.

Lightweight tests that verify critical paths without heavy mocking.
For full E2E testing, use Docker integration tests with real Redis.
"""

from datetime import date
from pathlib import Path

import pytest

from src.models.command import FetchCommand, FetchMode, FetchStrategy


class TestFetchCommandE2E:
    """Smoke tests for fetch command end-to-end flow."""

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_command_parse_and_expand_dates(self):
        """Test command parsing and date expansion (critical path)."""
        # This tests the most common production scenario
        cmd = FetchCommand(
            command="fetch",
            chat="@ru_python",
            mode=FetchMode.DAYS,
            days=7,
            strategy=FetchStrategy.BATCH,
        )

        # Verify command is valid
        assert cmd.chat == "@ru_python"
        assert cmd.mode == FetchMode.DAYS
        assert cmd.days == 7

        # Verify date expansion works
        dates = cmd.expand_dates()
        assert len(dates) == 7
        assert all(isinstance(d, date) for d in dates)

        # Verify output path generation
        output_path = cmd.get_output_path("data", dates[0])
        assert "ru_python" in output_path
        assert dates[0].isoformat() in output_path

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_command_range_mode_critical_path(self):
        """Test RANGE mode command (second most common scenario)."""
        cmd = FetchCommand(
            command="fetch",
            chat="@pythonstepikchat",
            mode=FetchMode.RANGE,
            from_date=date(2025, 11, 1),
            to_date=date(2025, 11, 7),
            strategy=FetchStrategy.BATCH,
        )

        dates = cmd.expand_dates()
        assert len(dates) == 7
        assert dates[0] == date(2025, 11, 1)
        assert dates[-1] == date(2025, 11, 7)

    @pytest.mark.e2e
    @pytest.mark.slow
    def test_command_force_mode(self):
        """Test force re-fetch flag (critical for data updates)."""
        cmd = FetchCommand(
            command="fetch",
            chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 11, 7),
            strategy=FetchStrategy.BATCH,
            force=True,
        )

        assert cmd.force is True
        assert cmd.mode == FetchMode.DATE


# NOTE: For full integration testing with real Redis, Telethon, and file I/O,
# use Docker Compose smoke tests:
#
# docker-compose up -d redis telegram-fetcher
# python scripts/send_fetch_command.py --chat @ru_python --days 1
# # Verify: data/ru_python/YYYY/*.json files created
#
# This approach is more reliable than mocking complex async operations.
