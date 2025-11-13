# TZ: Observability hardening for telegram-fetcher

## Business Goal
Increase reliability and diagnostic power during data fetch runs by improving structured logging and Prometheus metrics, ensuring clean integration with the existing Redis/Loki/Prometheus stack. Keep overhead low and avoid noisy or PII-leaking logs.

## Functional Requirements
- Logging
  - Structured JSON logs with consistent core fields across the app: service, environment, host, version, git_sha.
  - Correlation ID present in all important stages (start, progress, boundaries, saving, finalization, completion, errors).
  - Mask PII (phone number) in logs.
  - Reduce noisy third‑party logs (Telethon) by default to WARNING.
  - Optional Loki batching via env var (best-effort fallback to non-batch).
- Metrics
  - Export per chat/date duration histogram for fetch (already present) and ensure it’s observed.
  - Counters for fetched messages per chat/date.
  - Counter for fetch runs per chat/date.
  - Counters for Redis events published with status label (success/failure).
  - Keep cardinality bounded (labels: chat, date, worker, strategy for runs; event_type, status, worker for events).
  - Support explicit metrics mode selection: scrape (HTTP endpoint) vs push (Pushgateway) for one‑shot CLI runs.

## Technical Decisions
- Logging
  - Introduce ContextFilter to inject core fields (service, environment, host, version, git_sha) into every record.
  - Extend CustomJsonFormatter to always include correlation_id when present and new core fields if present.
  - Add LokiQueueHandler usage when LOKI_BATCH=true (fallback to LokiHandler).
  - Reduce Telethon log level to WARNING by default inside setup_logging.
  - Mask TELEGRAM_PHONE in session_manager logs.
- Metrics
  - Extend metrics: fetch_runs_total, events_published_total{event_type,status,worker}.
  - Observe fetch_duration_seconds and increment fetch_messages_total/fetch_runs_total in MessageIterator at end of iteration per (chat, date).
  - Add metrics_mode setting (scrape|push, default scrape). If push and pushgateway_url provided, push at end of run for CLI (non-listen) commands.

## API / ENV
- New/updated env variables (documented via .env):
  - LOKI_BATCH=true|false (optional), LOKI_BATCH_SIZE (optional, best-effort)
  - METRICS_MODE=scrape|push (optional, default scrape)
  - SERVICE_NAME, ENVIRONMENT, HOSTNAME, APP_VERSION, GIT_SHA (optional; used in logs)

## Implementation Plan
1. Logging
   - Add ContextFilter in `src/observability/logging_config.py` to inject default fields; reduce Telethon log level; optional Loki batching.
   - Extend CustomJsonFormatter to include service, environment, host, version, git_sha.
   - Mask phone number in `src/services/session_manager.py`.
2. Metrics
   - Add counters in `src/observability/metrics.py`: fetch_runs_total, events_published_total.
   - In `src/services/fetching/message_iterator.py`, record duration and message counts at the end; increment fetch_runs_total.
   - In `src/services/event_publisher.py`, increment events_published_total with status success/failure.
   - Add config `metrics_mode` in `src/core/config.py`; in `src/main.py` push to Pushgateway when mode=push (non-listen commands).

## Status
- [x] In Progress (spec created)
- [ ] Implemented
- [ ] Tested
