#!/usr/bin/env python3
"""
New unified fetcher using FetcherService with continuous mode.
Replaces the old fetcher.py with cleaner, more maintainable code.
"""

import asyncio
import sys
from pathlib import Path

from config import load_config, FetchMode
from fetcher_service import FetcherService

async def main():
    """Main entry point for continuous fetching."""
    try:
        # Load configuration
        config = load_config()
        
        # Force continuous mode
        config.fetch_mode = FetchMode.CONTINUOUS.value
        
        print(f"Starting continuous fetcher...")
        print(f"Data directory: {config.data_dir}")
        print(f"Channels: {', '.join(config.chats)}")
        print(f"Mode: {config.fetch_mode}")
        
        # Create and run service
        service = FetcherService(config)
        await service.run()
        
        print("\n✓ Fetching completed successfully!")
        
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