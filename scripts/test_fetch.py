"""Test script to check if we can fetch messages from channels at all."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from telethon import TelegramClient

from src.core.config import FetcherConfig
from src.observability.logging_config import get_logger, setup_logging

# Load environment
load_dotenv()

# Setup logging
setup_logging(level="INFO", log_format="text", service_name="test-fetch")
logger = get_logger(__name__)


async def test_fetch():
    """Test fetching last 10 messages from channels."""
    config = FetcherConfig()

    # Create session file path
    safe_phone = config.telegram_phone.replace("+", "")
    session_file = config.session_dir / f"session_{safe_phone}.session"

    logger.info(f"Using session: {session_file}")

    # Create client
    client = TelegramClient(
        str(session_file), config.telegram_api_id, config.telegram_api_hash
    )

    async with client:
        logger.info("Connected to Telegram")

        for chat_id in config.telegram_chats:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing channel: {chat_id}")
            logger.info(f"{'='*60}")

            try:
                entity = await client.get_entity(chat_id)
                logger.info(f"Channel found: {entity.title}")

                # Fetch last 10 messages
                logger.info("Fetching last 10 messages...")
                count = 0
                async for message in client.iter_messages(entity, limit=10):
                    count += 1
                    logger.info(
                        f"  [{count}] ID: {message.id} | "
                        f"Date: {message.date} | "
                        f"Text: {message.text[:50] if message.text else '(no text)'}..."
                    )

                if count == 0:
                    logger.warning(f"  NO MESSAGES FOUND in {chat_id}")
                else:
                    logger.info(f"  Total messages fetched: {count}")

            except Exception as e:
                logger.error(f"Error processing {chat_id}: {e}", exc_info=True)

    logger.info("\nTest completed!")


if __name__ == "__main__":
    asyncio.run(test_fetch())
