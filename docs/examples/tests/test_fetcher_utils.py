import asyncio
import json
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add parent directory to path for importing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetcher_utils import build_output_path, count_reactions, prepare_message


@pytest.mark.unit
class TestFetcherUtils:
    """Test cases for fetcher utility functions."""

    def test_count_reactions_with_none(self):
        """Test count_reactions with None input."""
        assert count_reactions(None) == 0

    def test_count_reactions_with_no_results(self):
        """Test count_reactions with no results attribute."""
        reactions = Mock()
        del reactions.results  # Remove results attribute
        assert count_reactions(reactions) == 0

    def test_count_reactions_with_results(self):
        """Test count_reactions with valid results."""
        reaction1 = Mock()
        reaction1.count = 5
        reaction2 = Mock()
        reaction2.count = 3

        reactions = Mock()
        reactions.results = [reaction1, reaction2]

        assert count_reactions(reactions) == 8

    def test_build_output_path_channel(self):
        """Test build_output_path for channel."""
        base_dir = "/test/data"
        channel_username = "@testchannel"

        output_dir, safe_name, filepath = build_output_path(base_dir, channel_username)

        assert safe_name == "testchannel"
        assert "channels" in output_dir
        assert base_dir in output_dir
        assert filepath.endswith(".json")

    def test_build_output_path_chat(self):
        """Test build_output_path for chat."""
        base_dir = "/test/data"
        chat_username = "testchat"

        output_dir, safe_name, filepath = build_output_path(base_dir, chat_username)

        assert safe_name == "testchat"
        assert "chats" in output_dir
        assert base_dir in output_dir

    def test_build_output_path_beginners_chat(self):
        """Test build_output_path for beginners chat."""
        base_dir = "/test/data"
        chat_username = "beginners_group"

        output_dir, safe_name, filepath = build_output_path(base_dir, chat_username)

        assert safe_name == "beginners_group"
        assert "chats" in output_dir
        assert base_dir in output_dir

    def test_prepare_message_basic(self):
        """Test prepare_message with basic message."""
        mock_msg = Mock()
        mock_msg.id = 12345
        mock_msg.date = datetime(2025, 11, 4, 12, 0, 0, tzinfo=UTC)
        mock_msg.text = "Test message"
        mock_msg.reply_to_msg_id = None
        mock_msg.reactions = None
        mock_msg.sender = None

        result = prepare_message(mock_msg, "testchannel")

        expected = {
            "id": 12345,
            "ts": int(datetime(2025, 11, 4, 12, 0, 0, tzinfo=UTC).timestamp()),
            "text": "Test message",
            "reply_to": None,
            "reactions": 0,
            "sender_id": None,
        }

        assert result == expected

    def test_prepare_message_with_sender(self):
        """Test prepare_message with sender information."""
        mock_sender = Mock()
        mock_sender.id = 67890

        mock_msg = Mock()
        mock_msg.id = 12345
        mock_msg.date = datetime(2025, 11, 4, 12, 0, 0, tzinfo=UTC)
        mock_msg.text = "Test message"
        mock_msg.reply_to_msg_id = 111
        mock_msg.reactions = None
        mock_msg.sender = mock_sender

        result = prepare_message(mock_msg, "testchannel")

        assert result["sender_id"] == 67890
        assert result["reply_to"] == 111

    def test_prepare_message_with_reactions(self):
        """Test prepare_message with reactions."""
        reaction = Mock()
        reaction.count = 5

        reactions = Mock()
        reactions.results = [reaction]

        mock_msg = Mock()
        mock_msg.id = 12345
        mock_msg.date = datetime(2025, 11, 4, 12, 0, 0, tzinfo=UTC)
        mock_msg.text = "Test message"
        mock_msg.reply_to_msg_id = None
        mock_msg.reactions = reactions
        mock_msg.sender = None

        result = prepare_message(mock_msg, "testchannel")

        assert result["reactions"] == 5

    def test_prepare_message_empty_text(self):
        """Test prepare_message with empty text."""
        mock_msg = Mock()
        mock_msg.id = 12345
        mock_msg.date = datetime(2025, 11, 4, 12, 0, 0, tzinfo=UTC)
        mock_msg.text = "   "  # Whitespace only
        mock_msg.reply_to_msg_id = None
        mock_msg.reactions = None
        mock_msg.sender = None

        result = prepare_message(mock_msg, "testchannel")

        assert result["text"] == ""  # Should be stripped to empty string

    def test_prepare_message_no_text_attribute(self):
        """Test prepare_message when text attribute is missing."""
        mock_msg = Mock()
        mock_msg.id = 12345
        mock_msg.date = datetime(2025, 11, 4, 12, 0, 0, tzinfo=UTC)
        del mock_msg.text  # Remove text attribute
        mock_msg.reply_to_msg_id = None
        mock_msg.reactions = None
        mock_msg.sender = None

        result = prepare_message(mock_msg, "testchannel")

        assert result["text"] == ""

    def test_prepare_message_no_date(self):
        """Test prepare_message when date attribute is missing."""
        mock_msg = Mock()
        mock_msg.id = 12345
        del mock_msg.date  # Remove date attribute
        mock_msg.text = "Test message"
        mock_msg.reply_to_msg_id = None
        mock_msg.reactions = None
        mock_msg.sender = None

        result = prepare_message(mock_msg, "testchannel")

        assert result["ts"] is None
