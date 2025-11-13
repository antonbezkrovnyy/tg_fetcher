# TZ: Fetcher Resilience, Idempotency, and Parallelism

## Business Goal
Increase reliability and throughput of Telegram fetching while respecting limits and avoiding data duplication. Provide clear observability and controls for production.

## Confirmed Scope (from user)
- Storage backend: FS (file system) for this sprint.
- Parallelism per chats: enabled, safe starting with 2–3.
- Rate limits: No explicit RPS/windows, no proxy, no reserve accounts. Must be conservative and adaptive.
- Production metrics default: both (scrape + push).

## Functional Requirements
1. Resilience
   - Retries with exponential backoff + jitter for Telethon calls and Redis publish.
   - Circuit breaker around Telethon client to avoid hammering during prolonged failures.
2. Idempotency & Deduplication
   - Idempotency key: `${chat}:${date}:${message_id}`; drop duplicates before write.
   - Track `last_processed_msg_id` per (chat, date) to support restart without reprocessing.
3. Parallelism & Rate Limiting
   - Bounded concurrency by chat (2–3). Adaptive sleep/backoff on FloodWait/limit signals.
4. Schema Version Tagging
   - Every artifact must include `schema_version` and `timezone`.
5. Observability
   - Extend metrics: `retries_total`, `rate_limit_hits_total`, `fetch_lag_seconds`, `fetch_duration_seconds` histogram, `breaker_state`.
   - Keep METRICS_MODE supporting `scrape|push|both` with prod default `both`.

## Technical Decisions
- Use `tenacity` for retry/backoff with full jitter (Decorrelated Jitter or Exponential + random) and max elapsed time.
- Simple circuit breaker (closed → open → half-open) with failure threshold and open timeout; half-open tries limited probes.
- Parallelism via a small thread/async pool (match current code style) with guard against memory growth (bounded queues/batch sizes).
- Repository remains FS; dedup performed in-memory per day slice before write and by persisting last processed pointer.
- Timezone normalization remains UTC throughout; lag computed vs. current time.

## Config Keys (new)
- RETRY_MAX_ATTEMPTS (int, default 5)
- RETRY_MAX_ELAPSED_SECONDS (int, default 120)
- BACKOFF_BASE_SECONDS (float, default 0.5)
- BACKOFF_MAX_SECONDS (float, default 10)
- CIRCUIT_BREAKER_WINDOW_SECONDS (int, default 30)
- CIRCUIT_BREAKER_FAILURE_THRESHOLD (int, default 5)
- CIRCUIT_BREAKER_OPEN_TIMEOUT_SECONDS (int, default 60)
- PARALLELISM_MAX (int, default 2)
- RATE_LIMIT_STRATEGY (str: "adaptive", default adaptive)
- SCHEMA_VERSION (str, default "1.0.0")
- METRICS_MODE (existing, ensure default prod = both)

## Metrics (Prometheus)
- Counter: `retries_total{target, reason}`
- Counter: `rate_limit_hits_total{source, reason}`
- Gauge: `last_retry_delay_seconds{target}`
- Gauge: `breaker_state{component}` (0=closed,1=open,2=half_open)
- Counter: `breaker_open_total{component}`
- Histogram: `fetch_duration_seconds{chat}` (define sensible buckets)
- Gauge: `fetch_lag_seconds{chat}`
- Counter: `deduplicated_messages_total{source}`

## Implementation Plan
1) Retries & Backoff (tenacity)
- Wrap Telethon network calls and Redis publish with retry decorator.
- Log attempts (attempt number, delay, reason); emit retries_total and last_retry_delay_seconds.

2) Circuit Breaker
- Implement simple breaker utility (module `src/services/resilience/circuit_breaker.py`).
- Integrate in session manager so that calls short-circuit when open; after open_timeout, allow limited probes.
- Emit breaker metrics and logs on state transitions.

3) Idempotency & Dedup
- Compute idempotency key; maintain set per run/day; filter duplicates before write.
- Persist `last_processed_msg_id` per (chat, date) in progress storage (JSON) to resume safely.
- Increment deduplicated_messages_total.

4) Parallelism & Rate Limit
- Add PARALLELISM_MAX; run chats concurrently with bounded pool.
- Adaptive sleep on FloodWait/limit signals (increase backoff windows) and track rate_limit_hits_total.

5) Schema Tagging & Writers
- Introduce SCHEMA_VERSION constant; include `schema_version` and `timezone` into all saved artifacts.

6) Metrics Expansion & Defaults
- Add and wire new metrics; ensure METRICS_MODE default for prod is both (config-driven).

7) Tests
- Unit: retry policy (simulate failures), breaker transitions, dedup logic.
- Integration: Redis publish with retry; end-to-end day fetch with dedup and progress.
- Contract: artifact contains schema_version/timezone; matches analyzer expectations.

## Acceptance Criteria
- Intermittent network errors recover with retry and are visible in metrics.
- Persistent failures open breaker; transitions logged; half-open recovers when healthy.
- Re-runs do not create duplicate messages for the same (chat, date).
- With PARALLELISM_MAX=2, total runtime decreases on multiple chats; no rate-limit explosions; rate_limit_hits_total tracked.
- All artifacts include `schema_version` and `timezone`.
- Metrics available in both scrape and push modes; prod config set to both.

## Rollout
- Phase 1: Enable retries + metrics (low risk).
- Phase 2: Circuit breaker + idempotency.
- Phase 3: Parallelism + rate limiting.
- Phase 4: Schema tagging & tests consolidation.

## Status
- [ ] In Progress
- [ ] Implemented
- [ ] Tested
