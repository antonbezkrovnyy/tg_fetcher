# Lightweight orchestrator: fetch messages and save per-channel files.
import os
import json
import asyncio
import time
from datetime import datetime, timedelta, UTC, date
from pathlib import Path
from telethon import TelegramClient

from fetcher_utils import prepare_message, build_output_path, save_json
from retry_utils import retry_on_error_enhanced, handle_flood_wait_direct, RateLimiter
from config import load_config, FetcherConfig

try:
    from observability.metrics import MetricsExporter
except ImportError:
    # Fallback for when observability module is not available
    class MetricsExporter:
        def record_messages_fetched(self, *args, **kwargs): pass
        def record_fetch_duration(self, *args, **kwargs): pass  
        def update_last_fetch_timestamp(self, *args, **kwargs): pass
        def update_progress_date(self, *args, **kwargs): pass
        def record_fetch_error(self, *args, **kwargs): pass
        def record_channel_processed(self, *args, **kwargs): pass

# Load configuration
config = load_config()

# Configuration-based initialization  
DATA_DIR = config.data_dir
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = DATA_DIR / "progress.json"

metrics = MetricsExporter()


@retry_on_error_enhanced(max_attempts=3, backoff_factor=2.0)
async def fetch_day(client: TelegramClient, channel_username: str, day_date: date) -> int:
    """Fetch messages from a single day for a channel/chat and save them into a JSON file.

    - day_date: a date object (UTC day) for which messages should be collected.
    Returns number of messages saved.
    """
    start_time = time.time()
    print(f"Fetching {channel_username} for {day_date.isoformat()}...")
    
    try:
        entity = await client.get_entity(channel_username)

        start = datetime(day_date.year, day_date.month, day_date.day, tzinfo=UTC)
        end = start + timedelta(days=1)

        messages = []
        senders = {}

        # iterate forward from start-of-day to end-of-day: use offset_date=end and stop when msg.date < start
        async for msg in client.iter_messages(entity, offset_date=end, reverse=False):
            if not getattr(msg, 'date', None):
                continue
            msg_date = msg.date
            if msg_date >= end:
                # skip messages beyond end (shouldn't usually happen with offset_date=end)
                continue
            if msg_date < start:
                break

            # collect sender display name (if available)
            if getattr(msg, 'sender', None) and getattr(msg.sender, 'id', None):
                sender_id = msg.sender.id
                sender_name = getattr(msg.sender, 'first_name', '') or getattr(msg.sender, 'title', '') or 'Unknown User'
                # Skip empty/invisible names
                if sender_name.strip() and not all(ord(c) in [0x2800, 0x3164, 0x2000, 0x200B, 0x200C, 0x200D, 0xFEFF] for c in sender_name):
                    senders[sender_id] = sender_name
                else:
                    senders[sender_id] = 'Unknown User'

            messages.append(prepare_message(msg, channel_username))

        output_dir, safe_name, _ = build_output_path(str(DATA_DIR), channel_username)
        dir_for_channel = os.path.join(output_dir, safe_name)
        os.makedirs(dir_for_channel, exist_ok=True)
        filepath = os.path.join(dir_for_channel, f"{day_date.isoformat()}.json")

        result = {
            "channel_info": {
                "id": channel_username,
                "title": getattr(entity, 'title', channel_username),
                "url": f"https://t.me/{safe_name}"
            },
            "senders": senders,
            "messages": messages,
        }

        save_json(filepath, result, ensure_ascii=False, indent=2)
        print(f"  → Saved {len(messages)} messages to {filepath}")
        
        # Записываем метрики
        duration = time.time() - start_time
        metrics.record_messages_fetched(channel_username, len(messages))
        metrics.record_fetch_duration(channel_username, duration)
        metrics.update_last_fetch_timestamp(channel_username, time.time())
        metrics.update_progress_date(channel_username, start.timestamp())
        
        return len(messages)
    
    except Exception as e:
        # Записываем ошибку в метрики
        error_type = type(e).__name__
        metrics.record_fetch_error(channel_username, error_type)
        raise


async def main():
    # Initialize rate limiter from config
    rate_limiter = RateLimiter(calls_per_second=config.rate_limit.calls_per_second)
    
    # Use session directory from config
    session_file = config.session_dir / "session_digest"
    client = TelegramClient(str(session_file), config.api_id, config.api_hash)
    await client.start()

    # load progress
    if PROGRESS_FILE.exists():
        try:
            with PROGRESS_FILE.open('r', encoding='utf-8') as pf:
                progress = json.load(pf)
        except Exception:
            progress = {}
    else:
        progress = {}

    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    for ch in config.chats:
        if not ch:
            continue
        ch = ch.strip()
        print(f"\n=== Processing {ch} ===")

        # determine starting date
        last_parsed_str = progress.get(ch)
        if last_parsed_str:
            try:
                last_parsed = datetime.fromisoformat(last_parsed_str).date()
                start_date = last_parsed + timedelta(days=1)
            except Exception:
                start_date = None
        else:
            start_date = None

        if start_date is None:
            # try to detect earliest message date
            try:
                entity = await client.get_entity(ch)
                msgs = await client.get_messages(entity, limit=1, reverse=True)
                if msgs and getattr(msgs[0], 'date', None):
                    start_date = msgs[0].date.date()
                else:
                    # fallback start date (configurable if needed)
                    start_date = date(2015, 1, 1)
            except Exception as e:
                print(f"Warning: could not detect earliest date for {ch}: {e}")
                start_date = date(2015, 1, 1)

        if start_date > yesterday:
            print(f"{ch}: already up to date (nothing to parse).")
            continue

        cursor = start_date
        consecutive_failures = 0
        max_consecutive_failures = 3
        
        while cursor <= yesterday:
            try:
                # Apply rate limiting before each API call
                await rate_limiter.acquire()
                
                result = await handle_flood_wait_direct(fetch_day, client, ch, cursor)
                
                # persist progress (mark this date as last parsed)
                progress[ch] = cursor.isoformat()
                with PROGRESS_FILE.open('w', encoding='utf-8') as pf:
                    json.dump(progress, pf, ensure_ascii=False, indent=2)
                
                # Записываем успешную обработку канала
                metrics.record_channel_processed()
                
                # Reset failure counter on success
                consecutive_failures = 0
                
            except Exception as e:
                consecutive_failures += 1
                print(f"Error fetching {ch} for {cursor.isoformat()} (attempt {consecutive_failures}): {e}")
                
                # If too many consecutive failures, skip this channel
                if consecutive_failures >= max_consecutive_failures:
                    print(f"Too many consecutive failures for {ch}, skipping remaining dates")
                    break
                
                # For non-consecutive failures, just skip this date and continue
                if consecutive_failures == 1:
                    print(f"Skipping date {cursor.isoformat()} for {ch}, continuing with next date")
            
            cursor = cursor + timedelta(days=1)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
