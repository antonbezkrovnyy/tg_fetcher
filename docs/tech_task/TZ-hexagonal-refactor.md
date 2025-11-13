# TZ: Hexagonal Refactor – Repository Port and Service Slimming

## Business Goal
Increase maintainability and testability by aligning the fetcher with hexagonal (ports & adapters), reducing class size, and keeping analyzer untouched.

## Functional Requirements
- No behavior change: event payloads, file formats, and CLI/daemon flows remain compatible.
- Introduce repository port to decouple application from file storage.
- Keep reliability/observability features intact (metrics, events, progress, retries).

## Technical Decisions
- Add `MessageRepositoryProtocol` under `src/repositories/protocols.py`.
- Update ResultEnricher and ResultFinalizer to depend on the repository port.
- Keep `MessageRepository` as concrete adapter wiring in FetcherService.
- Defer Telegram gateway port to a follow-up (requires broader surface change).

## API Design
- Protocol methods cover current usage: save/load collection, path helpers, artifacts IO, file existence, create_collection.
- Structural subtyping – no inheritance; existing adapter conforms by shape.

## Implementation Plan
1. Define `MessageRepositoryProtocol` (port).  [done]
2. Switch `ResultEnricher` and `ResultFinalizer` to the port.  [done]
3. Ensure `FetcherService` wires a concrete adapter (no behavior change).  [done]
4. Introduce `TelegramGatewayProtocol` and `TelethonGateway` and route comment fetching via the gateway in `extract_comments` (opt-in) and `FetcherService`.  [done]
5. Run flake8/mypy/pytest; fix issues.  [pending tests]
6. Prepare follow-up task: UseCase split (`FetchSingleChatUseCase`, `DateRangeProcessor`).  [next]

## Status
- [x] In Progress
- [x] Implemented (phase 1: repository port; phase 2: telegram gateway for comments)
- [ ] Tested (final end-to-end/unit run pending per request)
