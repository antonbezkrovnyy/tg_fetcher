"""Source and sender mapping utilities.

Keeps Telethon-specific entity mapping away from orchestration logic.
"""

from __future__ import annotations

from typing import Any

from telethon.hints import Entity
from telethon.tl.types import Channel, Chat, User

from src.models.schemas import SourceInfo


class SourceInfoMapper:
    """Map Telethon entities to SourceInfo and resolve sender display names."""

    def extract_source_info(self, entity: Entity, chat_identifier: str) -> SourceInfo:
        """Build SourceInfo from a Telethon entity and fallback identifier.

        Args:
            entity: Telethon entity (Channel, Chat, or User)
            chat_identifier: Fallback chat identifier if username is missing

        Returns:
            SourceInfo describing the source id, title, url, and type
        """
        source_id = chat_identifier
        title = "Unknown"
        source_type = "unknown"
        url = ""

        if isinstance(entity, Channel):
            title = entity.title
            if entity.megagroup:
                source_type = "supergroup"
            else:
                source_type = "channel"
            if entity.username:
                source_id = f"@{entity.username}"
                url = f"https://t.me/{entity.username}"
            else:
                source_id = f"channel_{entity.id}"
                url = f"https://t.me/c/{entity.id}"

        elif isinstance(entity, Chat):
            title = entity.title
            source_type = "chat" if not entity.megagroup else "group"
            source_id = f"chat_{entity.id}"
            url = f"https://t.me/c/{entity.id}"

        elif isinstance(entity, User):
            title = self.get_sender_name(entity)
            source_type = "chat"
            if entity.username:
                source_id = f"@{entity.username}"
                url = f"https://t.me/{entity.username}"
            else:
                source_id = f"user_{entity.id}"

        return SourceInfo(id=source_id, title=title, url=url, type=source_type)

    def get_sender_name(self, sender: Any) -> str:
        """Resolve a human-friendly sender display name.

        Args:
            sender: Telethon User/Channel/Chat object or any

        Returns:
            Display name or a generic fallback
        """
        if sender is None:
            return "Unknown"
        if isinstance(sender, User):
            parts = []
            if sender.first_name:
                parts.append(sender.first_name)
            if sender.last_name:
                parts.append(sender.last_name)
            if parts:
                return " ".join(parts)
            if sender.username:
                return f"@{sender.username}"
            return f"User_{sender.id}"
        elif isinstance(sender, (Channel, Chat)):
            return sender.title or f"Channel_{sender.id}"
        return "Unknown"
