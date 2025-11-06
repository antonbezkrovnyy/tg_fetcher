"""Pydantic models for versioned data schemas.

This module defines all data models used for message storage with
strict validation and automatic serialization.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Reaction(BaseModel):
    """Single reaction to a message.

    Attributes:
        emoji: Reaction emoji
        count: Number of users who reacted
        users: Optional list of user IDs who reacted
    """

    model_config = ConfigDict(frozen=True)

    emoji: str = Field(..., min_length=1, description="Reaction emoji")
    count: int = Field(..., ge=1, description="Number of reactions")
    users: Optional[list[int]] = Field(
        default=None, description="User IDs who reacted (if available)"
    )


class ForwardInfo(BaseModel):
    """Information about forwarded message source.

    Attributes:
        from_id: Original sender ID (user or channel)
        from_name: Original sender display name
        date: Original message timestamp
    """

    model_config = ConfigDict(frozen=True)

    from_id: Optional[int] = Field(default=None, description="Original sender ID")
    from_name: Optional[str] = Field(default=None, description="Original sender name")
    date: Optional[datetime] = Field(default=None, description="Original message date")


class Message(BaseModel):
    """Telegram message model with full metadata.

    This model represents a single message with all its properties,
    reactions, and nested comments.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 12345,
                "date": "2025-11-06T10:30:00+00:00",
                "text": "Message text",
                "sender_id": 123456,
                "reply_to_msg_id": None,
                "forward_from": None,
                "reactions": [{"emoji": "👍", "count": 12}],
                "comments": [],
            }
        }
    )

    id: int = Field(..., description="Message ID")
    date: datetime = Field(..., description="Message timestamp")
    text: Optional[str] = Field(default=None, description="Message text content")
    sender_id: Optional[int] = Field(default=None, description="Sender user ID")
    reply_to_msg_id: Optional[int] = Field(
        default=None, description="ID of message this is replying to"
    )
    forward_from: Optional[ForwardInfo] = Field(
        default=None, description="Forward source information"
    )
    reactions: list[Reaction] = Field(
        default_factory=list, description="List of reactions to this message"
    )
    comments: list["Message"] = Field(
        default_factory=list, description="Comments/replies in discussion thread"
    )

    def get_reactions_dict(self) -> dict[str, int]:
        """Get reactions as emoji -> count dictionary.

        Returns:
            Dictionary mapping emoji to reaction count
        """
        return {r.emoji: r.count for r in self.reactions}


class Sender(BaseModel):
    """Sender information model.

    Maps sender ID to display name for efficient lookup.
    """

    model_config = ConfigDict(frozen=True)

    id: int = Field(..., description="Sender user/channel ID")
    display_name: str = Field(..., min_length=1, description="Display name")


class SourceInfo(BaseModel):
    """Information about message source (channel/chat).

    Attributes:
        id: Channel/chat username or ID
        title: Channel/chat title
        url: Direct link to channel/chat
        type: Source type (channel, chat, group)
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., min_length=1, description="Source identifier")
    title: str = Field(..., min_length=1, description="Source title")
    url: str = Field(..., description="Direct URL to source")
    type: str = Field(
        default="unknown",
        pattern=r"^(channel|chat|group|unknown)$",
        description="Source type",
    )


class MessageCollection(BaseModel):
    """Collection of messages from a single source on a specific date.

    This is the root model for JSON file storage with versioning.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "version": "1.0",
                "source_info": {
                    "id": "@channel_username",
                    "title": "Channel Title",
                    "url": "https://t.me/channel_username",
                    "type": "channel",
                },
                "senders": {"123456": "Display Name"},
                "messages": [],
            }
        }
    )

    version: str = Field(
        default="1.0", pattern=r"^\d+\.\d+$", description="Schema version"
    )
    source_info: SourceInfo = Field(..., description="Source metadata")
    senders: dict[str, str] = Field(
        default_factory=dict, description="Mapping of sender_id to display_name"
    )
    messages: list[Message] = Field(
        default_factory=list, description="List of messages"
    )

    def add_sender(self, sender_id: int, display_name: str) -> None:
        """Add or update sender information.

        Args:
            sender_id: Sender user/channel ID
            display_name: Sender display name
        """
        self.senders[str(sender_id)] = display_name

    def get_sender_name(self, sender_id: int) -> Optional[str]:
        """Get sender display name by ID.

        Args:
            sender_id: Sender user/channel ID

        Returns:
            Display name if found, None otherwise
        """
        return self.senders.get(str(sender_id))


class ProgressEntry(BaseModel):
    """Progress tracking for a single source.

    Tracks the last processed message/date for resumability.
    """

    last_message_id: Optional[int] = Field(
        default=None, description="ID of last processed message"
    )
    last_processed_date: Optional[datetime] = Field(
        default=None, description="Timestamp of last processing"
    )
    completed_dates: list[str] = Field(
        default_factory=list, description="List of fully processed dates (YYYY-MM-DD)"
    )

    def mark_date_completed(self, date_str: str) -> None:
        """Mark a date as fully processed.

        Args:
            date_str: Date in YYYY-MM-DD format
        """
        if date_str not in self.completed_dates:
            self.completed_dates.append(date_str)
            self.completed_dates.sort()


class ProgressFile(BaseModel):
    """Root model for progress.json file.

    Stores progress for all sources with versioning.
    """

    version: str = Field(
        default="1.0", pattern=r"^\d+\.\d+$", description="Progress file schema version"
    )
    sources: dict[str, ProgressEntry] = Field(
        default_factory=dict, description="Progress entries keyed by source ID"
    )

    def get_or_create_progress(self, source_id: str) -> ProgressEntry:
        """Get existing progress or create new entry.

        Args:
            source_id: Source identifier

        Returns:
            Progress entry for the source
        """
        if source_id not in self.sources:
            self.sources[source_id] = ProgressEntry()
        return self.sources[source_id]

    def reset_source(self, source_id: str) -> None:
        """Reset progress for a specific source.

        Args:
            source_id: Source identifier to reset
        """
        if source_id in self.sources:
            del self.sources[source_id]

    def reset_all(self) -> None:
        """Reset all progress data."""
        self.sources.clear()
