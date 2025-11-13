"""Telegram message extractors (reactions, comments, forward info).

Separated from FetcherService to reduce responsibilities and improve testability.
Includes both functional helpers and a DI-friendly MessageExtractor class.
"""

from __future__ import annotations

import logging
from typing import Optional

from telethon import TelegramClient
from telethon.hints import Entity
from telethon.tl.custom import Message as TelethonMessage
from telethon.tl.types import Channel

from src.gateways.telegram_protocols import TelegramGatewayProtocol
from src.models.schemas import ForwardInfo, Message, Reaction, SourceInfo

logger = logging.getLogger(__name__)


async def extract_reactions(message: TelethonMessage) -> list[Reaction]:
    """Extract reactions from a Telethon message.

    Returns a list of Reaction models. Handles missing fields gracefully.
    """
    reactions_list: list[Reaction] = []

    if not hasattr(message, "reactions") or message.reactions is None:
        return reactions_list

    try:
        from telethon.tl.types import MessageReactions

        if isinstance(message.reactions, MessageReactions):
            for reaction in message.reactions.results:
                emoji = None
                if hasattr(reaction, "reaction"):
                    if hasattr(reaction.reaction, "emoticon"):
                        emoji = reaction.reaction.emoticon
                    elif isinstance(reaction.reaction, str):
                        emoji = reaction.reaction

                if emoji and hasattr(reaction, "count"):
                    reactions_list.append(
                        Reaction(
                            emoji=emoji,
                            count=reaction.count,
                            users=None,  # User list not available in basic API
                        )
                    )
    except Exception as e:
        logger.warning(
            f"Failed to extract reactions from message {message.id}: {e}",
            extra={"message_id": message.id},
        )

    return reactions_list


async def extract_comments(
    client: TelegramClient,
    entity: Entity,
    message: TelethonMessage,
    source_info: SourceInfo,
    gateway: Optional[TelegramGatewayProtocol] = None,
) -> list[Message]:
    """Extract comments (discussion replies) for a channel message.

    Only applicable for channels; chats/supergroups return an empty list.
    Limits to 50 comments to avoid long-running iterations.
    """
    comments_list: list[Message] = []

    if source_info.type != "channel":
        return comments_list

    if not hasattr(message, "replies") or message.replies is None:
        return comments_list

    if message.replies.replies == 0:
        return comments_list

    try:
        if isinstance(entity, Channel) and hasattr(message.replies, "channel_id"):
            comment_count = 0
            # Use Telethon client to iterate comments.
            # Gateway-based iteration is handled by MessageExtractor.extract()
            # via gateway.extract_comments().
            iterator = client.iter_messages(
                message.replies.channel_id,
                reply_to=message.replies.max_id,
                limit=50,
            )

            async for comment in iterator:
                comment_data = Message(
                    id=comment.id,
                    date=comment.date,
                    text=comment.message or None,
                    sender_id=comment.sender_id,
                    reply_to_msg_id=comment.reply_to_msg_id,
                    forward_from=extract_forward_info(comment),
                    reactions=await extract_reactions(comment),
                    comments=[],
                )
                comments_list.append(comment_data)
                comment_count += 1

            if comment_count > 0:
                logger.debug(
                    f"Fetched {comment_count} comments for message {message.id}"
                )
    except Exception as e:
        logger.warning(
            f"Failed to extract comments from message {message.id}: {e}",
            extra={"message_id": message.id},
        )

    return comments_list


def extract_forward_info(message: TelethonMessage) -> Optional[ForwardInfo]:
    """Extract forward info from a Telethon message (if present)."""
    if not hasattr(message, "forward") or message.forward is None:
        return None

    try:
        forward = message.forward
        from_id = None
        from_name = None
        forward_date = None

        if hasattr(forward, "from_id"):
            from_id = (
                forward.from_id.user_id if hasattr(forward.from_id, "user_id") else None
            )

        if hasattr(forward, "from_name"):
            from_name = forward.from_name

        if hasattr(forward, "date"):
            forward_date = forward.date

        return ForwardInfo(from_id=from_id, from_name=from_name, date=forward_date)
    except Exception as e:
        logger.warning(
            f"Failed to extract forward info from message {message.id}: {e}",
            extra={"message_id": message.id},
        )
        return None


class MessageExtractor:
    """Small service that uses a TelegramGateway-like object to build Message.

    This provides a stable `extract()` callable for DI into use-cases.
    """

    def __init__(
        self, gateway: TelegramGatewayProtocol, comments_limit: int = 50
    ) -> None:
        """Initialize extractor with a gateway and comments limit."""
        self._gateway = gateway
        self._limit = comments_limit

    async def extract(
        self,
        client: TelegramClient,
        entity: Entity,
        message: TelethonMessage,
        source_info: SourceInfo,
    ) -> Message:
        """Extract a normalized Message including reactions and comments."""
        reactions = await self._gateway.extract_reactions(message)
        comments = await self._gateway.extract_comments(
            client, entity, message, source_info, limit=self._limit
        )
        forward_info = self._gateway.extract_forward_info(message)
        text = message.message or None
        return Message(
            id=message.id,
            date=message.date,
            text=text,
            sender_id=message.sender_id,
            reply_to_msg_id=message.reply_to_msg_id,
            forward_from=forward_info,
            reactions=reactions,
            comments=comments,
            token_count=None,
            normalized_links=[],
            message_type=None,
            lang=None,
        )
