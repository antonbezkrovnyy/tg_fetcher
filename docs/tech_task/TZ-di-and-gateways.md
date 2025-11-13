# TZ: DI, TelegramGateway, FinalizationOrchestrator

## Business Goal
Reduce FetcherService responsibilities and improve testability/maintainability by extracting:
- TelegramGateway: all Telethon-facing operations and message-level extractions
- FinalizationOrchestrator: artifact generation + completion publishing
- DI container: simple, explicit wiring for core services

## Functional Requirements
- FetcherService must delegate to TelegramGateway for:
  - get_entity(chat_identifier)
  - extract_reactions(message)
  - extract_comments(client, entity, message, source_info)
  - extract_forward_info(message)
- FetcherService must delegate to FinalizationOrchestrator for:
  - postprocess stage + artifacts (summary, threads, participants)
  - completion event publishing
- No behavior change for outputs/events/metrics
- Respect existing flags in config (enable_events, enable_metrics, comments_limit_per_message)

## Technical Decisions
- Keep MessageIterator as-is; TelegramGateway focuses on extraction and entity resolution used by FetcherService
- FinalizationOrchestrator uses ProgressService for events and ResultFinalizer for artifacts
- DI: minimal Container class providing gateway and orchestrator; FetcherService supports optional injected deps, otherwise resolves defaults via Container

## Contracts
- TelegramGateway
  - get_entity(client, chat_identifier) -> Entity
  - extract_reactions(message) -> list[Reaction]
  - extract_comments(client, entity, message, source_info, limit:int) -> list[Message]
  - extract_forward_info(message) -> Optional[ForwardInfo]
- FinalizationOrchestrator
  - finalize(source_info, start_date, collection, messages_fetched, duration, file_path, checksum_fn) -> None

## Implementation Plan
1. Create TelegramGateway module and move extraction helpers from FetcherService
2. Create FinalizationOrchestrator; move postprocess + publish_complete; replicate _build_threads helper internally
3. Add DI Container with factory methods for gateway and orchestrator
4. Refactor FetcherService: inject or resolve from container; replace calls; remove moved helpers
5. Run flake8/mypy, fix any issues; log commands in docs/console.log

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
