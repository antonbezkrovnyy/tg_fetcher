# TZ: Redis CommandSubscriber Integration Tests

## Business Goal
Ensure the Redis-based command subscriber processes commands reliably and exports observability signals, enabling safe daemon operations and horizontal scaling.

## Functional Requirements
- Start/stop a Redis instance ephemeral for tests using Testcontainers.
- Verify that a valid `fetch` command is received and handled exactly once.
- Verify unknown commands are rejected and accounted as failures with error_type `unknown_command`.
- Verify BLPOP timeouts are accounted in metrics when the queue is empty.

## Technical Decisions
- Use `testcontainers` (RedisContainer) to provision a fresh Redis per test module.
- Use a lightweight in-test `FakeMetricsAdapter` to assert counters without requiring Prometheus.
- Use short BLPOP timeouts (≤1s) to keep tests fast and deterministic.
- Run the subscriber in an asyncio `Task`; stop it via `stop()` after assertions.

## Implementation Plan
1. Add `testcontainers` to `requirements-dev.txt`.
2. Create `tests/integration/test_command_subscriber.py` with three tests:
   - success path for `fetch` command
   - unknown command path
   - timeout path (empty queue)
3. Use `pytest.importorskip("testcontainers.redis")` and graceful skip if Docker not available.
4. Run targeted pytest and update `docs/console.log` with executed commands.

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
