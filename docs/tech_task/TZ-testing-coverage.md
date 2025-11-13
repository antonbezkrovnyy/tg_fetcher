# TZ: Testing migration and coverage uplift

## Business Goal
Ensure reliable, environment-independent tests and progressively increase coverage towards 100% to improve confidence and speed of change.

## Functional Requirements
- Use Testcontainers for Redis-based integration tests (no localhost dependency).
- Fix failing strategy tests due to sync/async mismatch.
- Keep tests fast and deterministic; auto-skip gracefully if Docker unavailable.
- Incrementally add unit tests to raise coverage (target staged milestones: 70% → 85% → 95%+).

## Technical Decisions
- Testcontainers: `testcontainers.redis.RedisContainer` pinned to `redis:7.2.4`.
- Async Redis client: `redis.asyncio` against container connection string.
- ProgressTracker is synchronous: tests will mock it with Mock, not AsyncMock.

## Implementation Plan
1. Refactor `tests/integration/test_redis_operations.py` to use RedisContainer fixtures.
2. Update `tests/test_strategies.py` to use `Mock` for `get_progress` and make the name test async to avoid marker warnings.
3. Run tests locally; log commands to `docs/console.log`.
4. Add small unit tests for low-coverage modules (follow-up PRs) to raise coverage stepwise.

## Status
- [x] In Progress
- [ ] Implemented
- [ ] Tested
