"""Telegram gateway protocol (port) for hexagonal architecture.

Defines the minimal operations the application needs from the Telegram layer.
Concrete adapters (e.g., Telethon) should satisfy this protocol.
"""

from __future__ import annotations

from typing import Optional, Protocol

from telethon import TelegramClient
from telethon.hints import Entity
from telethon.tl.custom import Message as TelethonMessage

from src.models.schemas import ForwardInfo, Message, Reaction, SourceInfo


class TelegramGatewayProtocol(Protocol):
    """Port for Telegram operations required by comments extraction.

    The full gateway surface can be expanded iteratively.
    """

    async def extract_reactions(self, message: TelethonMessage) -> list[Reaction]:
        """Extract reactions from a message.

        Returns a list of Reaction models; must handle missing data gracefully.
        """
        ...

    async def extract_comments(
        self,
        client: TelegramClient,
        entity: Entity,
        message: TelethonMessage,
        source_info: SourceInfo,
        *,
        limit: int,
    ) -> list[Message]:
        """Extract flat comments for a channel message up to the given limit."""
        ...

    def extract_forward_info(self, message: TelethonMessage) -> Optional[ForwardInfo]:
        """Extract forward info from a message if present, else None."""
        ...
