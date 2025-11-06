"""Main entry point for Telegram Fetcher Service."""
import asyncio
import sys

from src.core.config import FetcherConfig
from src.observability.logging_config import setup_logging, get_logger
from src.services.fetcher_service import FetcherService


async def main() -> int:
    """Main function.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load configuration
        config = FetcherConfig.from_env()
        config.validate()
        
        # Setup logging
        logger = setup_logging(
            level=config.log_level,
            log_format=config.log_format,
        )
        
        logger.info("Configuration loaded successfully")
        
        # Create and run fetcher service
        fetcher = FetcherService(config)
        await fetcher.run()
        
        return 0
        
    except ValueError as e:
        # Configuration or validation error
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    
    except Exception as e:
        # Unexpected error
        logger = get_logger()
        logger.error("Unexpected error", extra={"error": str(e)}, exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
