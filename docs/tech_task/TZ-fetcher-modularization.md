# TZ: Fetcher Modularization

## Business Goal
Reduce complexity in `FetcherService` to ease future feature development, improve testability, and follow SOLID/GRASP by splitting responsibilities into cohesive modules.

## Functional Requirements
- Preserve current behavior and public API of fetch operations (no functional regressions).
- Keep idempotent skip, progress events, metrics, preprocessing features, and file artifacts intact.
- Maintain Prometheus metrics and Redis events integration.

## Technical Decisions
- Introduce dedicated modules:
  - MessageIterator: Telethon iteration with date boundaries and progress hooks
  - MessagePreprocessor: links normalization, token estimate, classification, language detection, short-merge
  - Finalizer: saving collection, summary/threads/participants, publish completion
  - MetricsAdapter: thin wrapper over Prometheus gauge (DIP)
- Keep Repository and Strategy patterns as-is; inject new components into FetcherService (controller role).

## Decisions Update (2025-11-12)
- Added global events gating via `FetcherConfig.enable_events` with no-op `EventPublisher` when disabled.
  - Rationale: enable clean local runs without Redis errors while preserving progress events through the existing `enable_progress_events` flag.
  - Effect: Daemon/FetcherService wire `EventPublisher(enabled=config.enable_events)`; all publish calls are guarded and failures are non-fatal.
- Prometheus metrics server is started early (best-effort) when `enable_metrics=true`.

## Next Refactor Targets
- Reduce `FetcherService.fetch_single_chat` complexity by extracting helpers (skip check, result enrichment).
- Extract progress/boundary logic in `MessageIterator.run` into small methods to drop C901.
- Simplify `MessagePreprocessor.maybe_merge_short` by separating predicate checks from merge action.

## Architecture Sketch
- FetcherService (Controller): orchestrates Iterator → Preprocessor → Finalizer; owns idempotency checks and strategy date ranges.
- MessageIterator: async generator yielding messages; exposes callbacks for progress.
- MessagePreprocessor: pure logic; supports feature flags from config.
- Finalizer: persistence + events; no iteration/telethon details.
- MetricsAdapter: interface used by controller/iterator for gauge updates; Prometheus-backed implementation provided.

## API Design (internal)
- class MessageIterator:
  - async def run(client, entity, start_dt, end_dt, on_progress) -> AsyncIterator[TelethonMessage | MessageData]
- class MessagePreprocessor:
  - def preprocess_and_maybe_merge(prev: Message | None, current: Message) -> tuple[Message | None, bool]
- class Finalizer:
  - def finalize(source_info, date, collection, messages_fetched, duration) -> Optional[str]
- class MetricsAdapter:
  - def set_progress(chat: str, date: str, value: int) -> None

## Implementation Plan
1. Extract `_finalize_date_range` helper (DONE) to reduce complexity in `_process_date_range`.
2. Create MessagePreprocessor and move link/lang/cls/token/merge logic into it.
3. Add MetricsAdapter; replace direct Prometheus usage.
4. Extract MessageIterator for Telethon iteration and progress updates.
5. Thin FetcherService to orchestration only; ensure mypy/flake8 clean; address C901.
6. Add unit tests for Preprocessor and Iterator (happy path + edge cases).

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
