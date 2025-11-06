"""Test script to debug message fetching locally (without Docker)."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.core.config import FetcherConfig
from src.observability.logging_config import get_logger, setup_logging
from src.services.fetcher_service import FetcherService

# Load environment
load_dotenv()

# Setup logging (text format for console readability)
setup_logging(level="INFO", log_format="text", service_name="test-fetch")
logger = get_logger(__name__)


async def test_fetch_service():
    """Test the fetcher service with detailed logging."""
    logger.info("="*60)
    logger.info("Starting Fetcher Service Test (Today's messages)")
    logger.info("="*60)
    
    config = FetcherConfig()
    
    logger.info(f"Config loaded:")
    logger.info(f"  - Chats: {config.telegram_chats}")
    logger.info(f"  - Session dir: {config.session_dir}")
    logger.info(f"  - Data dir: {config.data_dir}")
    
    # Create service - it creates strategy and repository internally
    service = FetcherService(config=config)
    
    logger.info("\nStarting fetch operation...")
    
    try:
        await service.run()
        logger.info("\n" + "="*60)
        logger.info("✅ Fetch completed successfully!")
        logger.info("="*60)
    except Exception as e:
        logger.error(f"\n❌ Fetch failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(test_fetch_service())
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n💥 Fatal error: {e}")
        sys.exit(1)
