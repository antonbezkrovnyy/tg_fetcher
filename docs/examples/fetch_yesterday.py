import asyncio
import json
import os
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fetcher_utils import build_output_path, prepare_message, save_json
from retry_utils import RateLimiter, handle_flood_wait, retry_on_error
from shutdown_utils import (
    create_healthcheck_script,
    is_shutdown_requested,
    mark_error,
    mark_healthy,
    set_current_task,
    setup_signal_handlers,
)
from telethon import TelegramClient

from observability.logging import get_logger, setup_logging
from observability.metrics import MetricsExporter

load_dotenv()

# Setup logging (re-enabled Loki after handler fix)
setup_logging()
logger = get_logger(__name__)
logger.debug("init: logging ready")

# Инициализируем метрики (с защитой от ранних ошибок)
try:
    # Используем context manager для батчинга push
    metrics = MetricsExporter()
    messages_fetched_total = metrics.create_counter(
        "telegram_messages_fetched_total",
        "Общее количество загруженных сообщений",
        labelnames=["channel"],
    )
    channels_processed_total = metrics.create_counter(
        "telegram_channels_processed_total", "Общее количество обработанных каналов"
    )
    fetch_errors_total = metrics.create_counter(
        "telegram_fetch_errors_total",
        "Количество ошибок при загрузке",
        labelnames=["channel", "error_type"],
    )
    fetch_duration_seconds = metrics.create_histogram(
        "telegram_fetch_duration_seconds",
        "Время загрузки сообщений (секунды)",
        labelnames=["channel"],
    )
    last_fetch_timestamp = metrics.create_gauge(
        "telegram_last_fetch_timestamp",
        "Timestamp последней успешной загрузки",
        labelnames=["channel"],
    )
    current_progress_date = metrics.create_gauge(
        "telegram_current_progress_date",
        "Текущая дата прогресса (Unix timestamp)",
        labelnames=["channel"],
    )
    # Дополнительные метрики качества данных (по доступным полям)
    reactions_total = metrics.create_counter(
        "telegram_reactions_total",
        "Суммарное количество реакций",
        labelnames=["channel"],
    )
    replies_total = metrics.create_counter(
        "telegram_replies_total",
        "Количество сообщений с reply_to",
        labelnames=["channel"],
    )
    empty_messages = metrics.create_counter(
        "telegram_empty_messages_total",
        "Количество пустых сообщений",
        labelnames=["channel"],
    )
    unique_senders = metrics.create_gauge(
        "telegram_unique_senders_total",
        "Количество уникальных авторов",
        labelnames=["channel"],
    )
    avg_message_length = metrics.create_gauge(
        "telegram_avg_message_length_bytes",
        "Средняя длина текста сообщения",
        labelnames=["channel"],
    )
    logger.debug("init: metrics exporter ready")
except Exception as e:
    logger.error(f"init: metrics exporter failed: {e}")

    class _NoopMetrics:
        def push_metrics(self):
            pass

        def record_messages_fetched(self, *a, **k):
            pass

        def record_channel_processed(self, *a, **k):
            pass

        def record_fetch_error(self, *a, **k):
            pass

        def record_fetch_duration(self, *a, **k):
            pass

        def update_last_fetch_timestamp(self, *a, **k):
            pass

        def update_progress_date(self, *a, **k):
            pass

    metrics = _NoopMetrics()
    # Метрики качества данных не доступны в noop режиме
    reactions_total = None
    replies_total = None
    empty_messages = None
    unique_senders = None
    avg_message_length = None

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
CHATS = [c.strip() for c in os.getenv("CHATS", "").split(",") if c.strip()]
logger.debug(
    "init: env loaded",
    extra={
        "api_id_set": bool(API_ID),
        "api_hash_set": bool(API_HASH),
        "chats_count": len(CHATS),
    },
)
DATA_DIR = Path("/data")  # Изменено для Docker
DATA_DIR.mkdir(parents=True, exist_ok=True)
PROGRESS_FILE = DATA_DIR / "progress.json"

# Rate limiter
rate_limiter = RateLimiter()


@retry_on_error
async def fetch_day(
    client: TelegramClient, channel_username: str, day_date: date
) -> int:
    """Fetch messages with retry logic and rate limiting"""
    start_time = time.time()

    logger.info(
        f"Fetching {channel_username} for {day_date.isoformat()}",
        extra={"channel": channel_username, "date": day_date.isoformat()},
    )

    try:
        # Check for shutdown request
        if is_shutdown_requested():
            logger.warning("Shutdown requested, skipping fetch")
            return 0

        set_current_task(f"Fetching {channel_username} for {day_date.isoformat()}")

        # Apply rate limiting
        await rate_limiter.acquire()

        # Use flood wait handler
        entity = await handle_flood_wait(client.get_entity, channel_username)

        start = datetime(day_date.year, day_date.month, day_date.day, tzinfo=UTC)
        end = start + timedelta(days=1)

        messages = []
        senders = {}

        async for msg in client.iter_messages(entity, offset_date=end, reverse=False):
            if not getattr(msg, "date", None):
                continue
            msg_date = msg.date
            if msg_date >= end:
                continue
            if msg_date < start:
                break

            if getattr(msg, "sender", None) and getattr(msg.sender, "id", None):
                sender_id = msg.sender.id
                sender_name = (
                    getattr(msg.sender, "first_name", "")
                    or getattr(msg.sender, "title", "")
                    or "Unknown User"
                )
                if sender_name.strip() and not all(
                    ord(c) in [0x2800, 0x3164, 0x2000, 0x200B, 0x200C, 0x200D, 0xFEFF]
                    for c in sender_name
                ):
                    senders[sender_id] = sender_name
                else:
                    senders[sender_id] = "Unknown User"

            messages.append(prepare_message(msg, channel_username))

        output_dir, safe_name, _ = build_output_path(str(DATA_DIR), channel_username)
        dir_for_channel = Path(output_dir) / safe_name
        dir_for_channel.mkdir(parents=True, exist_ok=True)
        filepath = dir_for_channel / f"{day_date.isoformat()}.json"

        result = {
            "channel_info": {
                "id": channel_username,
                "title": getattr(entity, "title", channel_username),
                "url": f"https://t.me/{safe_name}",
            },
            "senders": senders,
            "messages": messages,
        }

        save_json(str(filepath), result, ensure_ascii=False, indent=2)

        logger.info(
            f"Saved {len(messages)} messages to {filepath}",
            extra={
                "channel": channel_username,
                "date": day_date.isoformat(),
                "message_count": len(messages),
                "file_path": str(filepath),
            },
        )

        # Дополнительные метрики качества данных (по доступным полям)
        if unique_senders is not None:
            total_length = 0
            replies_count = 0
            empty_count = 0
            reactions_sum = 0
            for m in messages:
                txt = m.get("text") or ""
                total_length += len(txt)
                if m.get("reply_to"):
                    replies_count += 1
                if not txt:
                    empty_count += 1
                reactions_sum += int(m.get("reactions", 0) or 0)

            unique_senders.labels(channel=channel_username).set(len(senders))
            avg_len = (total_length / len(messages)) if messages else 0
            avg_message_length.labels(channel=channel_username).set(avg_len)
            replies_total.labels(channel=channel_username).inc(replies_count)
            empty_messages.labels(channel=channel_username).inc(empty_count)
            if reactions_sum:
                reactions_total.labels(channel=channel_username).inc(reactions_sum)

        # Основные метрики
        duration = time.time() - start_time
        messages_fetched_total.labels(channel=channel_username).inc(len(messages))
        fetch_duration_seconds.labels(channel=channel_username).observe(duration)
        last_fetch_timestamp.labels(channel=channel_username).set(time.time())
        current_progress_date.labels(channel=channel_username).set(start.timestamp())

        return len(messages)

    except Exception as e:
        # Записываем ошибку в метрики
        error_type = type(e).__name__
        fetch_errors_total.labels(channel=channel_username, error_type=error_type).inc()
        raise


async def main():
    """Main execution with graceful shutdown support"""
    # Setup signal handlers
    setup_signal_handlers()

    # Create healthcheck script
    try:
        create_healthcheck_script()
    except Exception as e:
        logger.warning(f"Could not create healthcheck script: {e}")

    logger.info("Starting fetcher service (yesterday mode)")

    try:
        client = TelegramClient("/sessions/session_digest", API_ID, API_HASH)
        await client.start()

        logger.info("Connected to Telegram")

        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)

        total_messages = 0
        total_channels = len([c for c in CHATS if c])
        processed_channels = 0

        for ch in CHATS:
            if not ch:
                continue

            # Check for shutdown request between channels
            if is_shutdown_requested():
                logger.warning("Shutdown requested, stopping processing")
                break

            ch = ch.strip()

            try:
                message_count = await fetch_day(client, ch, yesterday)
                total_messages += message_count
                processed_channels += 1

                # Записываем успешную обработку канала
                channels_processed_total.inc()

                logger.info(
                    f"Channel progress: {processed_channels}/{total_channels}",
                    extra={
                        "processed": processed_channels,
                        "total": total_channels,
                        "channel": ch,
                    },
                )

            except Exception as e:
                logger.error(
                    f"Error fetching {ch} for {yesterday.isoformat()}: {e}",
                    extra={
                        "channel": ch,
                        "date": yesterday.isoformat(),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                mark_error(f"Failed to fetch {ch}: {str(e)}")

        await client.disconnect()

        logger.info(
            "Fetcher completed successfully",
            extra={
                "total_messages": total_messages,
                "total_channels": processed_channels,
                "date": yesterday.isoformat(),
            },
        )

        # Финальная отправка метрик (batched)
        metrics.push()

        mark_healthy()

    except Exception as e:
        logger.critical(
            f"Fatal error in fetcher: {e}",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )
        mark_error(f"Fatal error: {str(e)}")
        raise


if __name__ == "__main__":
    import atexit
    import signal
    import sys

    def force_exit():
        """Force exit after cleanup."""
        import os
        import time

        time.sleep(0.1)
        os._exit(0)

    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        print(f"Received signal {signum}, shutting down...", flush=True)
        sys.exit(0)

    # Регистрируем обработчики
    atexit.register(force_exit)
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        asyncio.run(main())
        exit_code = 0
    except KeyboardInterrupt:
        print("\nInterrupted by user", flush=True)
        exit_code = 0
    except Exception as e:
        print(f"Fatal error: {e}", flush=True)
        exit_code = 1
    finally:
        # Cleanup with timeout
        import logging
        import threading

        def shutdown_logging():
            try:
                logging.shutdown()
            except Exception:
                pass

        shutdown_thread = threading.Thread(target=shutdown_logging)
        shutdown_thread.daemon = True
        shutdown_thread.start()
        shutdown_thread.join(timeout=2.0)

        time.sleep(0.5)

    if exit_code != 0:
        os._exit(exit_code)

    sys.exit(exit_code)
