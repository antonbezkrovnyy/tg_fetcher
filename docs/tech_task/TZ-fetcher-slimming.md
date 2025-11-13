# TZ: Slimming FetcherService into Use Cases

## Business Goal
Reduce complexity of `FetcherService` by extracting cohesive use cases and helpers, improving testability and adherence to SOLID/hexagonal architecture.

## Functional Requirements
- Preserve current observable behavior (events, artifacts), cosmetic payload changes are acceptable.
- Add bounded parallel processing of date ranges per chat.
- Keep idempotency logic (checksum-based skip) but encapsulate it; do not rely on Redis keys.
- Favor unit tests with mocks for new components.
- Backward compatibility is not required as long as external behavior remains equivalent.

## Technical Decisions
- Introduce application use cases:
  - FetchChatUseCase: orchestrates strategy ranges (parallel) for a chat.
  - FetchDateRangeUseCase: processes a single date range end-to-end.
- Extract supporting services:
  - SkipExistingChecker + SkipReporter
  - ProgressReporter facade (wraps ProgressService)
- Use existing ports/adapters (Gateway, Repository, Finalizer, ProgressService) via DI Container.
- Default bounded parallelism per chat: concurrency=3 (configurable later).

## API Design
- SkipExistingChecker
  - decide(source_id: str, date: date) -> tuple[bool, str|None]
- SkipReporter
  - report_skipped(source_id: str, date: date, reason: str, expected: str|None, actual: str|None) -> None
- ProgressReporter
  - publish_stage(chat, date, stage); publish_skipped(...); publish_complete(...)
  - set_gauge(chat, date, value); reset_gauge(chat, date)
- FetchDateRangeUseCase
  - execute(client, entity, source_info, start_date, end_date) -> DateRangeResult
- FetchChatUseCase
  - execute(client, chat_identifier, strategy) -> ChatResult

## Implementation Plan
1. Quick wins: add TZ (this file), plan, and use existing checksum util.
2. Implement SkipExistingChecker + SkipReporter.
3. Implement ProgressReporter.
4. Implement FetchDateRangeUseCase (reusing DateRangeProcessor and Preprocessor/Gateway).
5. Implement FetchChatUseCase with bounded concurrency (Semaphore=3).
6. Wire in DI and update FetcherService.run to delegate to FetchChatUseCase.
7. Lint, type-check, and add unit tests for checker and date-range use case (mock ports).

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
