"""Main fetcher service orchestrator."""
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from telethon import TelegramClient
from telethon.tl.types import Message, User, Channel, Chat

from src.core.config import FetcherConfig
from src.observability.logging_config import get_logger
from src.repositories.message_repository import MessageRepository
from src.services.session_manager import SessionManager
from src.services.strategy.base import BaseFetchStrategy
from src.services.strategy.yesterday import YesterdayOnlyStrategy


logger = get_logger(__name__)


class FetcherService:
    """Main service for fetching Telegram messages.
    
    Orchestrates session management, strategy execution, and data persistence.
    """
    
    def __init__(self, config: FetcherConfig):
        """Initialize FetcherService.
        
        Args:
            config: Service configuration
        """
        self.config = config
        self.session_manager = SessionManager(
            api_id=config.api_id,
            api_hash=config.api_hash,
            phone=config.phone,
            session_dir=config.session_dir,
        )
        self.repository = MessageRepository(data_dir=config.data_dir)
        self.strategy = self._get_strategy()
    
    def _get_strategy(self) -> BaseFetchStrategy:
        """Get fetch strategy based on configuration.
        
        Returns:
            Strategy instance
        """
        if self.config.fetch_mode == "yesterday":
            return YesterdayOnlyStrategy()
        # Future: add other strategies
        else:
            raise ValueError(f"Unsupported fetch mode: {self.config.fetch_mode}")
    
    async def run(self) -> None:
        """Run the fetcher service."""
        logger.info(
            "Starting Telegram Fetcher Service",
            extra={
                "mode": self.config.fetch_mode,
                "chats": self.config.chats,
                "strategy": self.strategy.get_strategy_name(),
            },
        )
        
        client = await self.session_manager.get_client()
        
        try:
            for chat_identifier in self.config.chats:
                await self._process_chat(client, chat_identifier)
        finally:
            await self.session_manager.close()
        
        logger.info("Fetcher service completed successfully")
    
    async def _process_chat(
        self, client: TelegramClient, chat_identifier: str
    ) -> None:
        """Process a single chat/channel.
        
        Args:
            client: Telegram client
            chat_identifier: Chat username or ID
        """
        logger.info("Processing chat", extra={"chat": chat_identifier})
        
        try:
            # Get chat entity
            entity = await client.get_entity(chat_identifier)
            
            # Get source info
            source_info = self._extract_source_info(entity, chat_identifier)
            
            # Process each date range from strategy
            async for start_date, end_date in self.strategy.get_date_ranges(
                client, chat_identifier
            ):
                await self._process_date_range(
                    client, entity, source_info, start_date, end_date
                )
        
        except Exception as e:
            logger.error(
                "Failed to process chat",
                extra={"chat": chat_identifier, "error": str(e)},
                exc_info=True,
            )
            raise
    
    async def _process_date_range(
        self,
        client: TelegramClient,
        entity: Any,
        source_info: Dict[str, Any],
        start_date,
        end_date,
    ) -> None:
        """Process messages for a date range.
        
        Args:
            client: Telegram client
            entity: Chat/channel entity
            source_info: Source metadata
            start_date: Start date
            end_date: End date
        """
        logger.info(
            "Fetching messages for date range",
            extra={
                "source": source_info["id"],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        
        # For yesterday-only strategy, start_date == end_date
        # We fetch all messages for that single day
        messages = []
        senders = {}
        
        # Calculate datetime boundaries for the date
        offset_start = datetime.combine(
            start_date, datetime.min.time(), tzinfo=timezone.utc
        )
        offset_end = datetime.combine(
            end_date, datetime.max.time(), tzinfo=timezone.utc
        )
        
        # Fetch messages for the date range
        async for message in client.iter_messages(
            entity,
            offset_date=offset_end,
            reverse=False,
        ):
            if message.date.date() < start_date:
                break
            
            if message.date.date() > end_date:
                continue
            
            # Extract message data
            msg_data = self._extract_message_data(message)
            messages.append(msg_data)
            
            # Collect sender info
            if message.sender:
                sender_id = message.sender_id
                sender_name = self._get_sender_name(message.sender)
                senders[str(sender_id)] = sender_name
        
        logger.info(
            "Fetched messages",
            extra={
                "source": source_info["id"],
                "date": start_date.isoformat(),
                "count": len(messages),
            },
        )
        
        # Save to repository
        if messages:
            self.repository.save_messages(
                source_name=source_info["id"],
                target_date=start_date,
                source_info=source_info,
                messages=messages,
                senders=senders,
            )
        else:
            logger.info(
                "No messages found for date",
                extra={"source": source_info["id"], "date": start_date.isoformat()},
            )
    
    def _extract_source_info(self, entity: Any, identifier: str) -> Dict[str, Any]:
        """Extract source information from entity.
        
        Args:
            entity: Telegram entity
            identifier: Original identifier used
            
        Returns:
            Dictionary with id, title, url
        """
        if isinstance(entity, Channel):
            username = entity.username or identifier
            return {
                "id": f"@{username}" if not username.startswith("@") else username,
                "title": entity.title,
                "url": f"https://t.me/{username.lstrip('@')}",
            }
        elif isinstance(entity, Chat):
            return {
                "id": identifier,
                "title": entity.title,
                "url": None,
            }
        else:
            return {
                "id": identifier,
                "title": str(entity),
                "url": None,
            }
    
    def _extract_message_data(self, message: Message) -> Dict[str, Any]:
        """Extract message data into schema format.
        
        Args:
            message: Telegram message object
            
        Returns:
            Message dictionary matching schema
        """
        # Basic message data
        data = {
            "id": message.id,
            "date": message.date.isoformat(),
            "text": message.text or "",
            "sender_id": message.sender_id,
            "reply_to_msg_id": message.reply_to_msg_id,
            "forward_from": None,  # TODO: implement forward info
            "reactions": {},  # TODO: implement reactions
            "comments": [],  # TODO: implement comments
        }
        
        return data
    
    def _get_sender_name(self, sender: Any) -> str:
        """Get display name for sender.
        
        Args:
            sender: Sender object
            
        Returns:
            Display name
        """
        if isinstance(sender, User):
            if sender.first_name and sender.last_name:
                return f"{sender.first_name} {sender.last_name}"
            elif sender.first_name:
                return sender.first_name
            elif sender.username:
                return f"@{sender.username}"
            else:
                return f"User{sender.id}"
        else:
            return str(sender)
