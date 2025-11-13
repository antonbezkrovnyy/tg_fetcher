# TZ: Tests for ProgressService and EventPublisher payloads

## Business Goal
Raise coverage by testing ProgressService (best-effort wrappers) and verifying that EventPublisher composes and publishes correctly structured payloads when enabled and connected.

## Functional Requirements
- ProgressService:
  - Metrics paths: `reset_gauge` and `set_progress` must swallow exceptions from metrics adapter and not raise.
  - Event paths:
    - If `enable_events` is False or `event_publisher` is None, publish methods must be no-ops.
    - If enabled, publish_* must call respective methods on the publisher; exceptions must be swallowed.
- EventPublisher:
  - When enabled and with a stubbed Redis client (publish returns a value), `_build_and_publish` should send a JSON containing base fields and specific payload keys.
  - Base fields: `event`, `timestamp` (ISO), `service`, `correlation_id` (non-empty).
  - Payload-specific keys for at least one method (e.g., `publish_fetch_complete`).

## Technical Decisions
- Use stub MetricsAdapter that raises or records inputs.
- Use stub EventPublisherProtocol for ProgressService tests; for EventPublisher payload test set `pub._redis_client` to a stub with `publish` capturing inputs.
- Avoid network calls; do not create real Redis connections.

## Test Cases
1. ProgressService.metrics: adapter raises → no exception from service methods.
2. ProgressService.events: disabled or None publisher → no calls done; enabled publisher called; if publisher raises, service still does not raise.
3. EventPublisher payload: capture published JSON and assert required structure and key values.

## Implementation Plan
1. Create tests/unit/test_progress_service.py with stubs and assertions.
2. Create tests/unit/test_event_publisher_payload.py to validate payload and base fields.
3. Run full test suite and review coverage delta.

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
