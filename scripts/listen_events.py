#!/usr/bin/env python3
"""
Utility to listen to events published by telegram-fetcher.

Usage:
    python scripts/listen_events.py
    python scripts/listen_events.py --redis-url redis://tg-redis:6379
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import redis.asyncio as redis
except ImportError:
    print("ERROR: redis library not installed. Run: pip install redis")
    sys.exit(1)


async def listen_events(redis_url: str = "redis://localhost:6379") -> None:
    """Subscribe to tg_events channel and print all events."""

    redis_client = redis.from_url(redis_url, decode_responses=True)

    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("tg_events")

        print("🔊 Listening to Redis channel 'tg_events'...")
        print("   Press Ctrl+C to stop\n")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])

                    # Pretty print event
                    event_type = event_data.get("event", "unknown")

                    if event_type == "fetch_complete":
                        print(f"✅ FETCH COMPLETE:")
                        print(f"   Chat: {event_data.get('chat')}")
                        print(f"   Messages: {event_data.get('message_count')}")
                        print(f"   Date: {event_data.get('date')}")
                        print(f"   Duration: {event_data.get('duration_seconds')}s")
                        print(f"   File: {event_data.get('file_path')}")

                    elif event_type == "fetch_failed":
                        print(f"❌ FETCH FAILED:")
                        print(f"   Chat: {event_data.get('chat')}")
                        print(f"   Date: {event_data.get('date')}")
                        print(f"   Error: {event_data.get('error')}")

                    else:
                        print(f"📨 EVENT: {event_type}")
                        print(f"   {json.dumps(event_data, indent=2)}")

                    print(f"   Timestamp: {event_data.get('timestamp')}")
                    print()

                except json.JSONDecodeError:
                    print(f"⚠️ Invalid JSON: {message['data']}\n")

    except KeyboardInterrupt:
        print("\n🛑 Stopping event listener...")
    finally:
        await pubsub.unsubscribe("tg_events")
        await redis_client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Listen to events from telegram-fetcher daemon"
    )
    parser.add_argument(
        "--redis-url",
        default=os.getenv("REDIS_URL", "redis://localhost:6379"),
        help="Redis URL (default: redis://localhost:6379)",
    )

    args = parser.parse_args()

    # Listen to events
    asyncio.run(listen_events(redis_url=args.redis_url))


if __name__ == "__main__":
    main()
