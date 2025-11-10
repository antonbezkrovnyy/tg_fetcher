"""
Queue fetch tasks for all days in November 2025 for ru_python chat.

Usage:
    python queue_fetch_tasks_november.py

This script will:
1. Find all days in November 2025 (1-30)
2. Check which days are missing in data/ru_python
3. Queue fetch tasks to Redis for missing days
"""

from datetime import date, timedelta
from pathlib import Path

import redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
QUEUE_NAME = "tg_fetcher:fetch_queue"
CHAT_NAME = "ru_python"
DATA_PATH = Path(r"C:\Users\Мой компьютер\Desktop\python-tg\data\ru_python")


def get_november_dates(year=2025):
    """Return list of all dates in November as strings YYYY-MM-DD."""
    start = date(year, 11, 1)
    dates = []
    for i in range(30):
        d = start + timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


def main():
    print("=" * 60)
    print("  📋 Queue Fetch Tasks for November 2025")
    print("=" * 60)
    print()

    # Connect to Redis
    print(f"🔌 Connecting to Redis at {REDIS_HOST}:{REDIS_PORT} ...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    print("✅ Connected to Redis")
    print()

    # Get all November dates
    all_dates = get_november_dates()
    print(f"📅 November dates: {len(all_dates)} days")

    # Find existing files
    existing = set(f.stem for f in DATA_PATH.glob("2025-11-*.json"))
    print(f"📂 Existing files: {len(existing)}")

    # Find missing dates
    missing = [d for d in all_dates if d not in existing]
    print(f"❗ Missing days: {len(missing)}")
    print()

    if not missing:
        print("✅ Все дни уже скачаны!")
        return

    # Queue fetch tasks
    import json
    from datetime import datetime

    for d in missing:
        task = {
            "command": "fetch",
            "chat": CHAT_NAME,
            "date": d,
            "requested_by": "batch_script",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        r.rpush("tg_commands", json.dumps(task))
        print(f"  ✓ Queued fetch: {CHAT_NAME} @ {d}")

    print()
    print(f"✅ Всего поставлено задач: {len(missing)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
