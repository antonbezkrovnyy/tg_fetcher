# TZ: Wire CommandSubscriber into DI and config

## Business Goal
Enable distributed triggering of fetch tasks via Redis queue so multiple workers can process commands reliably (BLPOP). Centralize creation and configuration in the DI container, using already externalized settings.

## Functional Requirements
- Provide a DI factory that builds a CommandSubscriber configured from FetcherConfig.
- The subscriber must use:
  - redis_url/redis_password
  - commands_queue
  - commands_blpop_timeout
  - worker_id derived from service_name (e.g., service_name + optional suffix)
- Provide a default async command handler that triggers a single-chat fetch using existing FetchRunner and StrategyFactory.
- Do not change existing run/single CLI flows yet (no new subcommands in this scope).
- Keep events/metrics behavior unchanged.

## Technical Decisions
- Implement provider methods in `src/di/container.py`:
  - `provide_command_handler()` → async Callable[[dict[str, Any]], Awaitable[None]]
  - `provide_command_subscriber()` → `CommandSubscriber`
- The command handler will:
  - Read `chat` (required) and `date` (optional) from the command JSON
  - Build strategy via `provide_strategy(date_str)`; otherwise defaults to configured mode
  - Use `provide_fetch_runner().run_single(...)` to execute work
  - Generate `correlation_id` via `ensure_correlation_id()` for traceability
- No circular imports: use use-cases from container; avoid importing `FetcherService` inside container.

## API Design
- No public REST/gRPC changes. DI-only additions.
- Command JSON (as today):
  ```json
  {"command":"fetch","chat":"ru_python","date":"2025-11-12","requested_by":"scheduler"}
  ```
  - Fields like `days_back`, `limit`, `strategy` may be present but are ignored in this iteration; can be extended later.

## Implementation Plan
1. Add imports in `container.py` for `CommandSubscriber`.
2. Implement `provide_command_handler()` (async closure) and `provide_command_subscriber()` using `FetcherConfig`.
3. Leave lifecycle start/stop to callers (future: CLI `listen` subcommand).
4. Update docs: add this TZ, and later a configuration guide referencing queue fields.
5. Run lint, mypy, and unit tests; update `docs/console.log` with commands.

## Status
- [x] In Progress
- [x] Implemented
- [x] Tested
