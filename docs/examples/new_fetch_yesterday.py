#!/usr/bin/env python3
"""
New unified yesterday fetcher using FetcherService.
Replaces the old fetch_yesterday.py with cleaner, more maintainable code.
"""

import asyncio
import sys
from pathlib import Path

from fetcher_service import FetcherService

from config import FetchMode, load_config


async def main():
    """Main entry point for yesterday-only fetching."""
    try:
        # Load configuration
        config = load_config()

        # Force yesterday-only mode
        config.fetch_mode = FetchMode.YESTERDAY_ONLY.value

        print(f"Starting yesterday fetcher...")
        print(f"Data directory: {config.data_dir}")
        print(f"Channels: {', '.join(config.chats)}")
        print(f"Mode: {config.fetch_mode}")

        # Create and run service
        service = FetcherService(config)
        await service.run()

        print("\n✓ Yesterday fetch completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️  Fetching interrupted by user")
        return 1
    except Exception as e:
        print(f"\n✗ Error during fetching: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
