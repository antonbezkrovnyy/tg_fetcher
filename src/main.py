"""Main entry point for Telegram Fetcher Service.

Loads configuration, sets up observability, and runs the fetcher service.
"""

import asyncio
import sys

from pydantic import ValidationError

from src.core.config import FetcherConfig
from src.observability.logging_config import setup_logging, get_logger
from src.services.fetcher_service import FetcherService


async def main() -> int:
    """Main application entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load configuration from environment
        config = FetcherConfig()
        
        # Validate mode-specific requirements
        config.validate_mode_requirements()
        
    except ValidationError as e:
        print(f"Configuration validation error:\n{e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"Failed to load configuration: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Setup logging
    setup_logging(
        level=config.log_level,
        log_format=config.log_format,
        service_name="telegram-fetcher",
        loki_url=config.loki_url
    )
    
    logger = get_logger(__name__)
    
    logger.info(
        "Starting Telegram Fetcher Service",
        extra={
            "fetch_mode": config.fetch_mode,
            "chats_count": len(config.telegram_chats),
            "data_dir": str(config.data_dir)
        }
    )
    
    try:
        # Create and run fetcher service
        service = FetcherService(config)
        await service.run()
        
        logger.info("Fetcher service completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Fatal error in fetcher service: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
