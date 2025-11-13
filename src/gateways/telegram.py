"""Telethon-based adapter that implements TelegramGatewayProtocol."""

from __future__ import annotations

from typing import AsyncIterator, cast

from telethon import TelegramClient
from telethon.tl.custom import Message as TelethonMessage

from src.gateways.telegram_protocols import TelegramGatewayProtocol


class TelethonGateway(TelegramGatewayProtocol):
    """Adapter over Telethon client to provide gateway operations."""

    def __init__(self, client: TelegramClient) -> None:
        """Initialize gateway with a Telethon client instance.

        Args:
            client: Pre-configured TelethonClient to use for operations.
        """
        self._client = client

    def iter_channel_comments(
        self, channel_id: int, reply_to_max_id: int, *, limit: int = 50
    ) -> AsyncIterator[TelethonMessage]:  # noqa: E501
        """Iterate discussion comments for a channel post.

        Delegates to Telethon's iter_messages with reply_to filter.

        Args:
            channel_id: Channel identifier containing the post
            reply_to_max_id: Message ID of the channel post
            limit: Max number of comments to iterate
        """
        # Delegate to Telethon's iter_messages with reply_to filter
        return cast(
            AsyncIterator[TelethonMessage],
            self._client.iter_messages(
                channel_id, reply_to=reply_to_max_id, limit=limit
            ),
        )
