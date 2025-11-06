import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, Mock
from datetime import datetime, date, UTC
from pathlib import Path

# Test the fetcher with configuration


@pytest.mark.integration
class TestFetcherWithConfig:
    """Test fetcher integration with configuration system."""

    def test_config_loading(self):
        """Test that configuration is loaded properly."""
        from config import load_config

        # Mock environment variables for config
        env_vars = {
            'API_ID': '12345',
            'API_HASH': 'test_hash',
            'CHATS': 'channel1,channel2',
            'DATA_DIR': '/test/data',
            'MAX_RETRIES': '5'
        }

        with patch.dict('os.environ', env_vars):
            config = load_config()

            assert config.api_id == 12345
            assert config.api_hash == 'test_hash'
            assert config.chats == ['channel1', 'channel2']
            assert config.data_dir == Path('/test/data')
            assert config.max_retries == 5

    @pytest.mark.asyncio
    async def test_fetcher_uses_config(self, temp_data_dir):
        """Test that fetcher uses configuration values."""
        from config import FetcherConfig

        # Create test config
        test_config = FetcherConfig(
            api_id=99999,
            api_hash="config_test_hash",
            chats=["config_channel"],
            data_dir=temp_data_dir,
            session_dir=temp_data_dir / "sessions",
            max_retries=2,
            concurrent_channels=1
        )

        # Mock the config loading and global config variable
        with patch('fetcher.load_config', return_value=test_config), \
             patch('fetcher.config', test_config), \
             patch('fetcher.TelegramClient') as mock_client_class, \
             patch('fetcher.MetricsExporter'):

            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock entity and messages
            mock_entity = Mock()
            mock_entity.id = 123
            mock_entity.title = "Config Test Channel"
            mock_client.get_entity.return_value = mock_entity

            # Mock earliest message
            earliest_msg = Mock()
            earliest_msg.date = datetime(2025, 11, 1, 0, 0, 0, tzinfo=UTC)
            mock_client.get_messages.return_value = [earliest_msg]

            # Empty async generator for messages
            async def empty_messages(*args, **kwargs):
                if False:
                    yield None
            mock_client.iter_messages = empty_messages

            # Import and run fetcher after mocking
            from fetcher import main

            await main()

            # Verify TelegramClient was called with config values
            mock_client_class.assert_called_once()
            call_args = mock_client_class.call_args

            # Check that credentials are from config
            assert call_args[0][1] == 99999  # api_id
            assert call_args[0][2] == "config_test_hash"  # api_hash
            # Session path check - just verify it contains session_digest
            assert "session_digest" in call_args[0][0]

    def test_config_validation_in_fetcher(self):
        """Test that fetcher fails with invalid configuration."""
        from config import FetcherConfig, ConfigValidationError

        # Test missing required fields
        with pytest.raises(ConfigValidationError, match="api_id is required"):
            FetcherConfig(
                api_id=None,
                api_hash="test",
                chats=["channel1"]
            )

    def test_example_config_creation(self, temp_data_dir):
        """Test creating example configuration file."""
        from config import create_example_config

        config_file = temp_data_dir / "example_config.json"
        create_example_config(config_file)

        assert config_file.exists()

        # Verify example config is valid
        with open(config_file) as f:
            data = json.load(f)

        assert "api_id" in data
        assert "api_hash" in data
        assert "chats" in data
        assert "rate_limit" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])