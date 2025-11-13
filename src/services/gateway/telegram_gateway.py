"""Telegram gateway.

Encapsulates Telethon-facing operations and message-level extractions
to keep orchestration logic slim and testable.
"""

from __future__ import annotations

import contextlib
from typing import Optional

from telethon import TelegramClient
from telethon.hints import Entity
from telethon.tl.custom import Message as TelethonMessage
from telethon.tl.types import Channel, MessageReactions

from src.models.schemas import ForwardInfo, Message, Reaction, SourceInfo


class TelegramGateway:
    """Facade for Telethon interactions and message extraction helpers."""

    async def get_entity(self, client: TelegramClient, chat_identifier: str) -> Entity:
        """Resolve chat/channel/user entity by identifier."""
        return await client.get_entity(chat_identifier)

    async def extract_reactions(self, message: TelethonMessage) -> list[Reaction]:
        """Extract reactions from a Telethon message (best-effort)."""
        reactions_list: list[Reaction] = []
        if not hasattr(message, "reactions") or message.reactions is None:
            return reactions_list
        with contextlib.suppress(Exception):
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
                            Reaction(emoji=emoji, count=reaction.count, users=None)
                        )
        return reactions_list

    async def extract_comments(
        self,
        client: TelegramClient,
        entity: Entity,
        message: TelethonMessage,
        source_info: SourceInfo,
        *,
        limit: int,
    ) -> list[Message]:
        """Extract flat comments for channel posts only.

        For chats/supergroups returns an empty list. No nested comments.
        """
        comments_list: list[Message] = []
        if source_info.type != "channel":
            return comments_list
        if not hasattr(message, "replies") or message.replies is None:
            return comments_list
        if message.replies.replies == 0:
            return comments_list

        with contextlib.suppress(Exception):
            if isinstance(entity, Channel) and hasattr(message.replies, "channel_id"):
                if limit <= 0:
                    return comments_list
                async for comment in client.iter_messages(
                    message.replies.channel_id,
                    reply_to=message.replies.max_id,
                    limit=limit,
                ):
                    comments_list.append(
                        Message(
                            id=comment.id,
                            date=comment.date,
                            text=comment.message or None,
                            sender_id=comment.sender_id,
                            reply_to_msg_id=comment.reply_to_msg_id,
                            forward_from=self.extract_forward_info(comment),
                            reactions=await self.extract_reactions(comment),
                            comments=[],
                        )
                    )
        return comments_list

    def extract_forward_info(self, message: TelethonMessage) -> Optional[ForwardInfo]:
        """Extract forward info from message (best-effort)."""
        if not hasattr(message, "forward") or message.forward is None:
            return None
        with contextlib.suppress(Exception):
            forward = message.forward
            from_id = None
            if hasattr(forward, "from_id") and hasattr(forward.from_id, "user_id"):
                from_id = forward.from_id.user_id
            from_name = getattr(forward, "from_name", None)
            forward_date = getattr(forward, "date", None)
            return ForwardInfo(
                from_id=from_id,
                from_name=from_name,
                date=forward_date,
            )
        return None
