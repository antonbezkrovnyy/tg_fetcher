"""Telegram Fetcher Service with Pydantic models and full features.

Main orchestrator for fetching messages from Telegram with reactions,
comments, and progress tracking.
"""

import logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User, MessageReactions

from src.core.config import FetcherConfig
from src.models.schemas import (
    Message,
    MessageCollection,
    Reaction,
    ForwardInfo,
    SourceInfo,
)
from src.repositories.message_repository import MessageRepository
from src.services.session_manager import SessionManager
from src.services.strategy.base import BaseFetchStrategy
from src.services.strategy.yesterday import YesterdayOnlyStrategy

logger = logging.getLogger(__name__)


class FetcherService:
    """Main service for fetching Telegram messages with full metadata.
    
    Coordinates session management, strategy execution, and data persistence.
    """
    
    def __init__(self, config: FetcherConfig):
        """Initialize fetcher service.
        
        Args:
            config: Validated FetcherConfig instance
        """
        self.config = config
        self.session_manager = SessionManager(
            api_id=config.telegram_api_id,
            api_hash=config.telegram_api_hash,
            phone=config.telegram_phone,
            session_dir=config.session_dir
        )
        self.repository = MessageRepository(config.data_dir)
        
        # Select strategy based on fetch mode
        self.strategy = self._create_strategy()
        
        logger.info(
            f"FetcherService initialized",
            extra={
                "strategy": self.strategy.get_strategy_name(),
                "sources": self.config.telegram_chats
            }
        )
    
    def _create_strategy(self) -> BaseFetchStrategy:
        """Create fetch strategy based on config.
        
        Returns:
            Strategy instance
            
        Raises:
            ValueError: If fetch_mode is not supported
        """
        if self.config.fetch_mode == "yesterday":
            return YesterdayOnlyStrategy()
        # TODO: Implement other strategies (full, incremental, continuous, date, range)
        # Note: This is a planned feature. For now, only 'yesterday' mode is supported.
        # Future strategies should implement BaseFetchStrategy interface.
        else:
            raise ValueError(f"Unsupported fetch_mode: {self.config.fetch_mode}")
    
    async def run(self) -> None:
        """Run fetcher service for all configured chats."""
        async with self.session_manager as client:
            for chat_identifier in self.config.telegram_chats:
                try:
                    await self._process_chat(client, chat_identifier)
                except Exception as e:
                    logger.error(
                        f"Failed to process chat {chat_identifier}: {e}",
                        extra={"chat": chat_identifier},
                        exc_info=True
                    )
    
    async def _process_chat(self, client: TelegramClient, chat_identifier: str) -> None:
        """Process single chat/channel.
        
        Args:
            client: Authenticated Telegram client
            chat_identifier: Chat username or ID
        """
        logger.info(f"Processing chat: {chat_identifier}")
        
        # Get entity (channel, chat, or user)
        entity = await client.get_entity(chat_identifier)
        
        # Extract source info
        source_info = self._extract_source_info(entity, chat_identifier)
        
        # Get date ranges from strategy
        async for start_date, end_date in self.strategy.get_date_ranges(client, entity):
            await self._process_date_range(
                client,
                entity,
                source_info,
                start_date,
                end_date
            )
    
    async def _process_date_range(
        self,
        client: TelegramClient,
        entity,
        source_info: SourceInfo,
        start_date: date,
        end_date: date
    ) -> None:
        """Process messages for a date range.
        
        Args:
            client: Telegram client
            entity: Channel/chat entity
            source_info: Source metadata
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        """
        logger.info(
            f"Fetching messages for {source_info.id}",
            extra={
                "source": source_info.id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        
        # Create collection for this date
        collection = self.repository.create_collection(
            source_info=source_info,
            messages=[]
        )
        
        # Fetch messages for date range
        messages_fetched = 0
        
        # Calculate date range boundaries
        # start = beginning of start_date (00:00:00 UTC)
        # end = beginning of day after end_date (00:00:00 UTC next day)
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
        
        logger.info(
            f"Fetching messages for date range",
            extra={
                "source": source_info.id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "start_datetime": start_datetime.isoformat(),
                "end_datetime": end_datetime.isoformat()
            }
        )
        
        # Iterate through messages using offset_date (like in reference implementation)
        # offset_date=end means "start from this date and go backwards"
        # reverse=False is default (newest to oldest)
        
        logger.info(f"Starting message iteration for {source_info.id}")
        messages_processed = 0
        
        async for message in client.iter_messages(entity, offset_date=end_datetime, reverse=False):
            if not message.date:
                continue
                
            msg_datetime = message.date
            
            # Log every 10 messages to track progress
            if messages_processed % 10 == 0 and messages_processed > 0:
                logger.info(
                    f"Processed {messages_processed} messages for {source_info.id}, "
                    f"fetched {messages_fetched}, current msg date: {msg_datetime}"
                )
            
            messages_processed += 1
            
            # Skip messages that are >= end (from next day onwards)
            if msg_datetime >= end_datetime:
                continue
            
            # Stop when we reach messages before our start date
            if msg_datetime < start_datetime:
                logger.info(
                    f"Reached start date boundary, stopping. "
                    f"Processed {messages_processed} messages, fetched {messages_fetched}"
                )
                break
            
            # Extract message data with reactions and comments
            message_data = await self._extract_message_data(client, entity, message)
            collection.messages.append(message_data)
            
            # Add sender to senders map
            if message_data.sender_id:
                sender_name = self._get_sender_name(message.sender)
                collection.add_sender(message_data.sender_id, sender_name)
            
            messages_fetched += 1
        
        # Save collection
        if messages_fetched > 0:
            self.repository.save_collection(
                source_name=source_info.id,
                target_date=start_date,
                collection=collection
            )
            
            logger.info(
                f"Saved {messages_fetched} messages",
                extra={
                    "source": source_info.id,
                    "date": start_date.isoformat(),
                    "count": messages_fetched
                }
            )
        else:
            logger.info(
                f"No messages found for {source_info.id} on {start_date}",
                extra={"source": source_info.id, "date": start_date.isoformat()}
            )
    
    async def _extract_message_data(
        self,
        client: TelegramClient,
        entity,
        message
    ) -> Message:
        """Extract message data into Pydantic model with reactions and comments.
        
        Args:
            client: Telegram client
            entity: Source entity
            message: Telethon message object
            
        Returns:
            Message model instance
        """
        # Extract reactions
        reactions = await self._extract_reactions(message)
        
        # Extract comments (for channels with discussion groups)
        comments = await self._extract_comments(client, entity, message)
        
        # Extract forward info
        forward_info = self._extract_forward_info(message)
        
        return Message(
            id=message.id,
            date=message.date,
            text=message.message or None,
            sender_id=message.sender_id,
            reply_to_msg_id=message.reply_to_msg_id,
            forward_from=forward_info,
            reactions=reactions,
            comments=comments
        )
    
    async def _extract_reactions(self, message) -> list[Reaction]:
        """Extract reactions from message.
        
        Args:
            message: Telethon message object
            
        Returns:
            List of Reaction models
        """
        reactions_list = []
        
        if not hasattr(message, 'reactions') or message.reactions is None:
            return reactions_list
        
        try:
            if isinstance(message.reactions, MessageReactions):
                for reaction in message.reactions.results:
                    # Get emoji from reaction
                    emoji = None
                    if hasattr(reaction, 'reaction'):
                        if hasattr(reaction.reaction, 'emoticon'):
                            emoji = reaction.reaction.emoticon
                        elif isinstance(reaction.reaction, str):
                            emoji = reaction.reaction
                    
                    if emoji and hasattr(reaction, 'count'):
                        reactions_list.append(
                            Reaction(
                                emoji=emoji,
                                count=reaction.count,
                                users=None  # User list not available in basic API
                            )
                        )
        except Exception as e:
            logger.warning(
                f"Failed to extract reactions from message {message.id}: {e}",
                extra={"message_id": message.id}
            )
        
        return reactions_list
    
    async def _extract_comments(
        self,
        client: TelegramClient,
        entity,
        message
    ) -> list[Message]:
        """Extract comments from channel post discussion.
        
        Args:
            client: Telegram client
            entity: Channel entity
            message: Channel message
            
        Returns:
            List of Message models representing comments
        """
        comments_list = []
        
        # Check if message has replies (discussion thread)
        if not hasattr(message, 'replies') or message.replies is None:
            return comments_list
        
        if message.replies.replies == 0:
            return comments_list
        
        try:
            # Get discussion message if this is a channel with linked discussion group
            if isinstance(entity, Channel) and hasattr(message.replies, 'channel_id'):
                # Fetch comments from discussion group (limit to 50 comments per message)
                comment_count = 0
                async for comment in client.iter_messages(
                    message.replies.channel_id,
                    reply_to=message.replies.max_id,
                    limit=50  # Limit comments to prevent hanging
                ):
                    # Recursively extract comment data (without nested comments)
                    comment_data = Message(
                        id=comment.id,
                        date=comment.date,
                        text=comment.message or None,
                        sender_id=comment.sender_id,
                        reply_to_msg_id=comment.reply_to_msg_id,
                        forward_from=self._extract_forward_info(comment),
                        reactions=await self._extract_reactions(comment),
                        comments=[]  # No nested comments
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
                extra={"message_id": message.id}
            )
        
        return comments_list
    
    def _extract_forward_info(self, message) -> Optional[ForwardInfo]:
        """Extract forward information from message.
        
        Args:
            message: Telethon message object
            
        Returns:
            ForwardInfo model if message is forwarded, None otherwise
        """
        if not hasattr(message, 'forward') or message.forward is None:
            return None
        
        try:
            forward = message.forward
            
            from_id = None
            from_name = None
            forward_date = None
            
            if hasattr(forward, 'from_id'):
                from_id = forward.from_id.user_id if hasattr(forward.from_id, 'user_id') else None
            
            if hasattr(forward, 'from_name'):
                from_name = forward.from_name
            
            if hasattr(forward, 'date'):
                forward_date = forward.date
            
            return ForwardInfo(
                from_id=from_id,
                from_name=from_name,
                date=forward_date
            )
        except Exception as e:
            logger.warning(
                f"Failed to extract forward info from message {message.id}: {e}",
                extra={"message_id": message.id}
            )
            return None
    
    def _extract_source_info(self, entity, chat_identifier: str) -> SourceInfo:
        """Extract source information from entity.
        
        Args:
            entity: Telegram entity (Channel, Chat, or User)
            chat_identifier: Original chat identifier string
            
        Returns:
            SourceInfo model
        """
        source_id = chat_identifier
        title = "Unknown"
        source_type = "unknown"
        url = ""
        
        if isinstance(entity, Channel):
            title = entity.title
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
            title = self._get_sender_name(entity)
            source_type = "chat"
            if entity.username:
                source_id = f"@{entity.username}"
                url = f"https://t.me/{entity.username}"
            else:
                source_id = f"user_{entity.id}"
        
        return SourceInfo(
            id=source_id,
            title=title,
            url=url,
            type=source_type
        )
    
    def _get_sender_name(self, sender) -> str:
        """Get display name for sender.
        
        Args:
            sender: Sender entity (User, Channel, etc.)
            
        Returns:
            Display name string
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
