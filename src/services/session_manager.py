"""Telegram session management."""
from pathlib import Path
from typing import Any, Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

from src.observability.logging_config import get_logger


logger = get_logger(__name__)


class SessionManager:
    """Manages Telegram client sessions.
    
    Handles session creation, persistence, and client lifecycle.
    """
    
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        phone: str,
        session_dir: Path,
    ):
        """Initialize SessionManager.
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: Phone number for authentication
            session_dir: Directory to store session files
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        self._client: Optional[TelegramClient] = None
        # Remove + from phone for safe filename
        safe_phone = phone.replace('+', '')
        self._session_file = self.session_dir / f"session_{safe_phone}.session"
    
    async def get_client(self) -> TelegramClient:
        """Get or create Telegram client.
        
        Returns:
            Connected TelegramClient instance
        """
        if self._client is None:
            logger.info(
                "Creating Telegram client",
                extra={"phone": self.phone, "session_file": str(self._session_file)},
            )
            
            # Create client with session file
            self._client = TelegramClient(
                str(self._session_file),
                self.api_id,
                self.api_hash,
            )
            
            # Connect and authenticate
            await self._client.connect()
            
            if not await self._client.is_user_authorized():
                logger.info("User not authorized, starting auth process")
                await self._client.send_code_request(self.phone)
                
                # In production, this would need to handle code input
                # For MVP, assuming session already exists or manual intervention
                logger.warning(
                    "Session not authorized. Please run auth setup first.",
                    extra={"phone": self.phone},
                )
                raise RuntimeError(
                    f"Session for {self.phone} is not authorized. "
                    "Please authorize the session first."
                )
            
            logger.info("Telegram client connected and authorized")
        
        return self._client
    
    async def close(self) -> None:
        """Close the Telegram client connection."""
        if self._client is not None:
            logger.info("Closing Telegram client")
            await self._client.disconnect()
            self._client = None
    
    async def __aenter__(self) -> TelegramClient:
        """Async context manager entry.
        
        Returns:
            Connected and authorized TelegramClient instance
        """
        return await self.get_client()
    
    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any]
    ) -> None:
        """Async context manager exit.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        await self.close()
