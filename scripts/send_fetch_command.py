#!/usr/bin/env python3
"""
Utility to send fetch commands to telegram-fetcher via Redis queue.

Usage:
    python scripts/send_fetch_command.py --chat pythonstepikchat --days 1
    python scripts/send_fetch_command.py --chat ru_python --limit 1000 --strategy batch
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import redis.asyncio as redis
except ImportError:
    print("ERROR: redis library not installed. Run: pip install redis")
    sys.exit(1)


async def send_command(
    chat: str,
    days_back: int = 1,
    limit: int | None = None,
    strategy: str = "auto",
    redis_url: str = "redis://localhost:6379",
) -> None:
    """Send fetch command to Redis queue."""

    # Build command structure
    command = {
        "command": "fetch",
        "chat": chat,
        "days_back": days_back,
        "strategy": strategy,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if limit:
        command["limit"] = limit

    # Connect to Redis
    redis_client = redis.from_url(redis_url, decode_responses=True)

    try:
        # Push command to queue (right side, fetcher pops from left)
        await redis_client.rpush("tg_commands", json.dumps(command))

        print(f"✅ Command sent to Redis queue 'tg_commands':")
        print(f"   Chat: {chat}")
        print(f"   Days back: {days_back}")
        print(f"   Limit: {limit or 'No limit'}")
        print(f"   Strategy: {strategy}")
        print(f"\n📋 Full command: {json.dumps(command, indent=2)}")

        # Check queue length
        queue_len = await redis_client.llen("tg_commands")
        print(f"\n📊 Current queue length: {queue_len}")

    finally:
        await redis_client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Send fetch command to telegram-fetcher daemon via Redis"
    )
    parser.add_argument(
        "--chat",
        required=True,
        help="Chat username to fetch (e.g., pythonstepikchat, ru_python)",
    )
    parser.add_argument(
        "--days",
        "--days-back",
        type=int,
        default=1,
        help="Number of days back to fetch (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of messages to fetch (optional)",
    )
    parser.add_argument(
        "--strategy",
        choices=["auto", "batch", "sequential"],
        default="auto",
        help="Fetch strategy (default: auto)",
    )
    parser.add_argument(
        "--redis-url",
        default=os.getenv("REDIS_URL", "redis://localhost:6379"),
        help="Redis URL (default: redis://localhost:6379)",
    )

    args = parser.parse_args()

    # Send command
    asyncio.run(
        send_command(
            chat=args.chat,
            days_back=args.days,
            limit=args.limit,
            strategy=args.strategy,
            redis_url=args.redis_url,
        )
    )


if __name__ == "__main__":
    main()
