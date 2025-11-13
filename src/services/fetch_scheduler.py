"""Simple daily scheduler that pushes fetch commands to Redis.

Purpose: ensure the fetcher receives a job every day to fetch yesterday's
messages for configured chats (e.g., ru_python).

Environment variables:
- REDIS_URL: redis://host:port
- REDIS_PASSWORD: optional password
- FETCH_SCHEDULE_CHATS: comma-separated list of chats (e.g., "ru_python")
- SCHEDULE_TIME: daily time in HH:MM (24h) when to enqueue (default: 02:00)
- TIMEZONE: use "UTC" or leave empty to use container local time (default: UTC)
- RUN_ON_START: if "true", send job immediately at start (default: false)

The command format matches CommandSubscriber expectations and includes `date`
explicitly set to yesterday in YYYY-MM-DD.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import List

import redis

COMMANDS_QUEUE = "tg_commands"


def _parse_time(hhmm: str) -> tuple[int, int]:
    try:
        hh, mm = hhmm.split(":")
        return int(hh), int(mm)
    except Exception:
        raise ValueError(f"Invalid SCHEDULE_TIME format: {hhmm}, expected HH:MM")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _seconds_until_next_run(hh: int, mm: int, use_utc: bool = True) -> float:
    now = _now_utc() if use_utc else datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return (target - now).total_seconds()


def _yesterday_yyyy_mm_dd(use_utc: bool = True) -> str:
    base = _now_utc().date() if use_utc else datetime.now().date()
    y = base - timedelta(days=1)
    return y.strftime("%Y-%m-%d")


def _create_fetch_command(chat: str, date_str: str) -> dict:
    return {
        "command": "fetch",
        "chat": chat,
        "date": date_str,
        "requested_by": "scheduler",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def main() -> int:
    """Run daily scheduler loop.

    Connects to Redis and enqueues a daily fetch command for configured chats
    at the specified time. Optionally enqueues once on startup.

    Returns:
        Process exit code (0 on normal termination, 1 on connection error)
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_password = os.getenv("REDIS_PASSWORD") or None
    chats_env = os.getenv("FETCH_SCHEDULE_CHATS", "ru_python")
    schedule_time = os.getenv("SCHEDULE_TIME", "02:00")
    timezone_name = (os.getenv("TIMEZONE") or "UTC").upper()
    run_on_start = os.getenv("RUN_ON_START", "false").lower() == "true"

    chats: List[str] = [c.strip() for c in chats_env.split(",") if c.strip()]
    use_utc = timezone_name == "UTC"
    hh, mm = _parse_time(schedule_time)

    # Connect Redis
    r = redis.from_url(redis_url, password=redis_password, decode_responses=True)
    # quick ping
    try:
        r.ping()
        print(f"✓ Scheduler connected to Redis at {redis_url}")
    except Exception as e:
        print(f"✗ Failed to connect to Redis: {e}", file=sys.stderr)
        return 1

    # Optionally fire immediately on startup
    if run_on_start:
        date_str = _yesterday_yyyy_mm_dd(use_utc=use_utc)
        for chat in chats:
            cmd = _create_fetch_command(chat, date_str)
            r.rpush(COMMANDS_QUEUE, json.dumps(cmd))
            print(f"→ Enqueued on start: {chat} {date_str}")

    # Main loop
    while True:
        try:
            sleep_s = _seconds_until_next_run(hh, mm, use_utc=use_utc)
            # Avoid busy loop
            time.sleep(max(1.0, sleep_s))

            date_str = _yesterday_yyyy_mm_dd(use_utc=use_utc)
            for chat in chats:
                cmd = _create_fetch_command(chat, date_str)
                r.rpush(COMMANDS_QUEUE, json.dumps(cmd))
                print(f"→ Enqueued daily: {chat} {date_str}")

        except KeyboardInterrupt:
            print("Scheduler stopped by user")
            return 0
        except Exception as e:
            print(f"⚠ Scheduler error: {e}", file=sys.stderr)
            # brief backoff
            time.sleep(10)


if __name__ == "__main__":
    sys.exit(main())
