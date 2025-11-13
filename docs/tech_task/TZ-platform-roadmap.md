# TZ: Platform-wide Roadmap (Fetcher → Analyzer → Web → Infra)

## Business Goal
Deliver a reliable, observable, and scalable Telegram data platform with clear data contracts, quality guarantees, and actionable insights for downstream web and analytics.

## Current State (Summary)
- Services: python-tg (fetcher), tg_analyzer (analytics), tg_web (web), infrastructure (Redis, Loki, Prometheus, Pushgateway, Grafana, MongoDB).
- Observability: Structured logs (JSON) with context; Loki enabled; Prometheus metrics + Pushgateway push for CLI runs.
- Data flow: Fetcher writes JSON artifacts to data/; Analyzer reads from files; Web presents results.

## Key Gaps and Risks
1. Data contract
   - Implicit JSON schema; no schema_version; analyzer not validating structure strictly.
2. Reliability
   - No explicit retry/backoff/circuit-breaker policies for network interactions (Telethon/Redis). Idempotency/dedup not enforced.
3. Scalability & Performance
   - Sequential iteration; file-only storage; large JSONs; limited parallelism and no rate control metrics.
4. Data Quality
   - No automated checks for duplicates, referential integrity between threads/messages, timezone consistency, deleted/edited flags.
5. Observability (next level)
   - No SLIs/SLOs or alerting; no tracing (OTel). Dashboards to be added.
6. Security & Privacy
   - Strengthen tg_web auth; retention and masking policies; secrets rotation.
7. Testing & CI
   - Lack of contract tests between fetcher/analyzer; few integration tests; no unified pre-commit/CI pipeline across repos.

## Functional Requirements
- Enforce versioned data schemas with strict validation.
- Ensure resilient fetch with retries (exponential + jitter), circuit breaker, and clear backoff logs.
- Provide data-quality guarantees (duplicate detection, referential integrity, timezone normalization, flags for edits/deletes).
- Expose platform SLIs and dashboards; support push and scrape metrics.
- Support scalable storage (FS or Mongo backend) with indexes.

## Technical Decisions
- Schemas: Pydantic v2 models with schema_version in every artifact; shared models package for cross-repo reuse (optional phase).
- Resilience: Retry w/ exponential backoff + jitter; circuit breaker around Telethon and Redis publish; idempotency keys per (chat, msg_id, date).
- Storage: Repository abstraction with FS and Mongo backends; Mongo indexes (chat, date, msg_id).
- Observability: Extend metrics (lag, retries_total, rate_limit_hits_total); define SLIs/SLOs; later add OTel tracing.
- Data Quality: Analyzer validators + metrics (duplicates_total, validation_failures_total, share_of_missing_fields), with a daily report.

## API/Data Design
- Artifacts include fields: schema_version, source, date, timezone, messages (each with id, timestamp UTC, edited/deleted flags), threads, participants.
- Idempotency key: f"{chat}:{date}:{message_id}".

## Implementation Plan
1) Quick Wins (1–3 days)
- Add schema_version to all fetcher outputs; publish Pydantic models in tg_analyzer and validate on read.
- Introduce retry/backoff w/ jitter for Telethon + Redis publish; add retries_total metrics.
- Pre-commit and CI pipelines (black/isort/flake8/mypy/pytest/pip-audit) in all repos.
- Basic Grafana dashboards for fetch RED and Pushgateway.

2) Sprint (1–2 weeks)
- Repository abstraction and Mongo backend; indexes on (chat, date, msg_id).
- Parallelize per-chat fetching with rate limiting; add idempotent write path + deduplicator.
- Contract tests fetcher↔analyzer + integration tests (Redis, Mongo, Pushgateway) via Testcontainers.
- tg_web: strengthen auth (JWT + refresh), rate limiting, CORS.

3) Strategic (1–2 months)
- OTel tracing end-to-end; SLOs + alerting on SLIs.
- Parquet/ZSTD or JSONL for large analytics artifacts; aggregated data marts for web.
- Scheduler (cron/Airflow) with backfill and monitoring; data retention & backup policies.

## SLIs/SLOs (Examples)
- Success rate: successful_fetch_runs / total_runs  SLO  99% (5m window).
- Latency: p95 fetch duration per chat   120s.
- Freshness: data_lag_seconds   600s in 95% cases.

## Testing Strategy
- Contract tests for schema compatibility.
- Integration tests with Redis, Mongo, Pushgateway.
- Property-based tests for validators.

## Status
- [x] Initial assessment captured
- [ ] Quick wins implemented
- [ ] Sprint tasks implemented
- [ ] Strategic tasks implemented
