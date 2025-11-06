import pytest
import asyncio
import json
from datetime import datetime, date, UTC, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from telethon import TelegramClient
from telethon.tl.types import Message, User, Channel, Chat


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary directory for test data."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def mock_telegram_client():
    """Mock Telegram client for testing."""
    client = AsyncMock(spec=TelegramClient)
    client.start = AsyncMock()
    client.disconnect = AsyncMock()
    client.get_entity = AsyncMock()
    client.iter_messages = AsyncMock()
    client.get_messages = AsyncMock()
    return client


@pytest.fixture
def mock_telegram_message():
    """Create mock Telegram message."""
    message = Mock(spec=Message)
    message.id = 12345
    message.date = datetime(2025, 11, 4, 12, 0, 0, tzinfo=UTC)
    message.text = "Test message content"
    message.reply_to_msg_id = None
    message.reactions = None
    
    # Mock sender
    sender = Mock(spec=User)
    sender.id = 67890
    sender.first_name = "Test User"
    message.sender = sender
    
    return message


@pytest.fixture
def mock_telegram_entity():
    """Create mock Telegram entity (channel/chat)."""
    entity = Mock(spec=Channel)
    entity.id = 123456789
    entity.title = "Test Channel"
    entity.username = "testchannel"
    return entity


@pytest.fixture
def sample_progress_data():
    """Sample progress data for testing."""
    return {
        "testchannel": "2025-11-03",
        "anotherchannel": "2025-11-02"
    }


@pytest.fixture
def sample_messages_data():
    """Sample messages data for testing."""
    return [
        {
            "id": 1,
            "ts": int(datetime(2025, 11, 4, 10, 0, 0, tzinfo=UTC).timestamp()),
            "text": "First test message",
            "reply_to": None,
            "reactions": 5,
            "sender_id": 1001
        },
        {
            "id": 2,
            "ts": int(datetime(2025, 11, 4, 11, 0, 0, tzinfo=UTC).timestamp()),
            "text": "Second test message",
            "reply_to": 1,
            "reactions": 0,
            "sender_id": 1002
        }
    ]


@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    return {
        "API_ID": "12345",
        "API_HASH": "test_hash",
        "CHATS": "testchannel,anotherchannel"
    }


@pytest.fixture(autouse=True)
def setup_test_env(mock_env_vars):
    """Setup test environment variables."""
    with patch.dict('os.environ', mock_env_vars):
        yield


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class MockAsyncIterator:
    """Mock async iterator for Telegram messages."""
    
    def __init__(self, items):
        self.items = iter(items)
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        try:
            return next(self.items)
        except StopIteration:
            raise StopAsyncIteration


@pytest.fixture
def mock_metrics():
    """Mock metrics exporter."""
    with patch('fetcher.MetricsExporter') as mock_exporter:
        mock_instance = Mock()
        mock_instance.record_messages_fetched = Mock()
        mock_instance.record_fetch_duration = Mock()
        mock_instance.update_last_fetch_timestamp = Mock()
        mock_instance.update_progress_date = Mock()
        mock_instance.record_fetch_error = Mock()
        mock_instance.record_channel_processed = Mock()
        mock_exporter.return_value = mock_instance
        yield mock_instance