# Configuration Guide

This project uses Pydantic BaseSettings to load configuration from environment variables (.env) with validation. Below are key settings, including advanced options introduced during recent refactors.

## Required
- TELEGRAM_API_ID
- TELEGRAM_API_HASH
- TELEGRAM_PHONE
- TELEGRAM_CHATS (space- or comma-separated)

## Fetch Modes
- FETCH_MODE: one of yesterday, full, incremental, continuous, date, range
- FETCH_DATE (for mode=date)
- FETCH_START, FETCH_END (for mode=range)

## Paths
- DATA_DIR (default: ./data)
- SESSION_DIR (default: ./sessions)
- PROGRESS_FILE (default: data/progress.json)

## Observability
- ENABLE_METRICS (default: true)
- METRICS_PORT (default: 9090)
- LOKI_URL (optional)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- LOG_FORMAT (json|text)
- SERVICE_NAME (default: tg_fetcher)

## Events (Redis Pub/Sub)
- ENABLE_EVENTS (default: true)
- ENABLE_PROGRESS_EVENTS (default: true)
- EVENTS_CHANNEL (default: tg_events)
- REDIS_URL (default: redis://localhost:6379)
- REDIS_PASSWORD (optional)

## Commands Queue (Redis List / BLPOP)
These settings enable distributed triggering of fetch tasks via a Redis queue.
- COMMANDS_QUEUE (default: tg_commands)
- COMMANDS_BLPOP_TIMEOUT (default: 5)

How it works:
- The DI container now provides `provide_command_subscriber()` wiring a CommandSubscriber with the queue and BLPOP timeout.
- The subscriber uses Redis `BLPOP` to ensure each command is delivered to exactly one worker (queue pattern).
- A default command handler is provided via `provide_command_handler()`, which executes a single-chat fetch using the configured strategy. Supported keys:
  - `command`: must be `fetch`
  - `chat`: chat identifier (required)
  - `date`: optional YYYY-MM-DD to influence strategy selection

Example command payload:
```json
{"command":"fetch","chat":"ru_python","date":"2025-11-12","requested_by":"scheduler"}
```

Programmatic usage sketch:
```python
from src.core.config import FetcherConfig
from src.di.container import Container

config = FetcherConfig()
container = Container(config=config)
container.initialize_runtime()
subscriber = container.provide_command_subscriber()
subscriber.connect()
# Run inside an event loop
await subscriber.listen()
```

Note: CLI does not yet include a `listen` subcommand; you can integrate the subscriber into your own runner or process manager.

## Schema / Versioning
- DATA_SCHEMA_VERSION (default: 1.0)
- PROGRESS_SCHEMA_VERSION (default: 1.0)
- PREPROCESSING_VERSION (default: 1)

These values are used across the repository, progress tracker, and finalization to annotate produced artifacts and enforce compatibility.

## Preprocessing Flags
- LINK_NORMALIZE_ENABLED (default: true)
- TOKEN_ESTIMATE_ENABLED (default: true)
- MESSAGE_CLASSIFIER_ENABLED (default: true)
- LANGUAGE_DETECT_ENABLED (default: true)
- MERGE_SHORT_MESSAGES_ENABLED (default: true)
- MERGE_SHORT_MESSAGES_MAX_LENGTH (default: 120)
- MERGE_SHORT_MESSAGES_MAX_GAP_SECONDS (default: 90)

Refer to `.env.example` for the complete, up-to-date list of variables and their defaults.
