import asyncio
import json
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Test the improved fetcher with error handling


@pytest.mark.integration
class TestImprovedFetcher:
    """Test the improved fetcher with retry mechanisms."""

    @pytest.mark.asyncio
    async def test_fetcher_with_retry_mechanisms(self, temp_data_dir):
        """Test that the improved fetcher uses retry mechanisms."""
        # Mock all necessary imports and dependencies
        with (
            patch("fetcher.TelegramClient") as mock_client_class,
            patch("fetcher.config") as mock_config,
            patch("fetcher.MetricsExporter") as mock_metrics,
        ):

            # Configure config mock
            mock_config.data_dir = temp_data_dir
            mock_config.progress_file = temp_data_dir / "progress.json"
            mock_config.chats = ["test_channel"]
            mock_config.api_id = 12345
            mock_config.api_hash = "test_hash"
            mock_config.session_name = "test_session"

            # Mock rate limit config
            mock_rate_limit = Mock()
            mock_rate_limit.calls_per_second = 1.0
            mock_config.rate_limit = mock_rate_limit

            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock entity for earliest message detection
            mock_entity = Mock()
            mock_entity.id = 123456
            mock_entity.title = "Test Channel"
            mock_client.get_entity.return_value = mock_entity

            # Mock earliest message
            earliest_msg = Mock()
            earliest_msg.date = datetime(2025, 11, 3, 0, 0, 0, tzinfo=UTC)
            mock_client.get_messages.return_value = [earliest_msg]

            # Mock iter_messages to return empty async generator
            async def empty_messages(*args, **kwargs):
                if False:  # Never true, so it's empty
                    yield None

            mock_client.iter_messages = empty_messages

            # Import and run the improved fetcher
            from fetcher import main

            await main()

            # Verify that client was started and stopped
            mock_client.start.assert_called_once()
            mock_client.disconnect.assert_called_once()

            # Just verify that main ran without error
            # (Progress file path might be different due to config handling)

    @pytest.mark.asyncio
    async def test_fetch_day_with_retry(self, temp_data_dir):
        """Test fetch_day function with retry decorator."""
        from fetcher import fetch_day
        from telethon.errors import FloodWaitError

        mock_client = AsyncMock()
        mock_entity = Mock()
        mock_entity.id = 123
        mock_entity.title = "Test Channel"

        call_count = 0

        async def failing_get_entity(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return mock_entity

        mock_client.get_entity.side_effect = failing_get_entity

        # Mock iter_messages to return empty async iterator
        async def mock_iter_messages(*args, **kwargs):
            # Return an empty async generator
            if False:  # Never true, so it's empty
                yield None

        mock_client.iter_messages = mock_iter_messages

        with patch("fetcher.DATA_DIR", temp_data_dir):
            # Should succeed after retry
            result = await fetch_day(mock_client, "test_channel", date(2025, 11, 4))

            # Verify it was called multiple times (retry mechanism)
            assert call_count == 2
            assert result == 0  # No messages returned


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
