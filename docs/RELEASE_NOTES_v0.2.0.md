# Release v0.2.0 — Fetcher resilience, metrics, and configurability

Date: 2025-11-13

Highlights

- Resilience:
  - Unified retry/backoff helpers used across Telethon auth/connect and Redis publish
  - Circuit breaker with CLOSED/OPEN/HALF_OPEN states and metrics, guarding Telegram session flows
  - Safer iterator throttling with configurable calls-per-second and graceful disable
- Idempotency & deduplication:
  - Cross-run idempotency via last_processed_id per chat/date
  - Optional in-run dedup behind config flag (DEDUP_IN_RUN_ENABLED=false by default)
- Parallelism & rate limiting:
  - Bounded cross-chat concurrency in runner
  - Throttle emits rate_limit_hits_total and observes fetch_lag_seconds
- Repository abstraction:
  - File-system backend remains default
  - Experimental Mongo repository scaffold behind STORAGE_BACKEND=mongo (not default)
- Schema and observability:
  - MessageCollection includes timezone; summary artifacts include timezone
  - Metrics expanded (fetch_duration_seconds, fetch_messages_total, fetch_runs_total, fetch_errors_total, fetch_retries_total, floodwait_wait_seconds, rate_limit_hits_total, dedup_skipped_total, fetch_lag_seconds, breaker metrics)
- Configuration:
  - New keys: STORAGE_BACKEND, MONGO_URL, MONGO_DB, MONGO_COLLECTION, DEDUP_IN_RUN_ENABLED, METRICS_MODE (scrape|push|both)

Breaking changes

- None. Defaults preserve previous behavior (FS backend, in-run dedup disabled).

Upgrade notes

1) Update .env (or environment) with new optional keys if you plan to use Mongo or Pushgateway:
   - STORAGE_BACKEND=fs (default) | mongo
   - MONGO_URL, MONGO_DB, MONGO_COLLECTION (when using mongo)
   - METRICS_MODE=scrape|push|both
   - DEDUP_IN_RUN_ENABLED=false|true
2) Rebuild containers if running in Docker to pick up new env and metrics wiring.

Quality gates

- Unit tests: PASS (full suite green on local Windows PowerShell)
- Type check and lint: previously green; no new violations introduced by this release scope

Notes

- Mongo repository is experimental and not enabled by default; production hardening and integration tests are planned next.
