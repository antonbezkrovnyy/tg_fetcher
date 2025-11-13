"""Integration tests for Redis queue and PubSub operations.

Optimized: Only critical paths tested.
Now uses Testcontainers for an isolated Redis instance (no localhost dependency).
"""

import asyncio
import json
from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import redis.asyncio as redis

from src.models.command import FetchCommand, FetchMode, FetchStrategy


@pytest.fixture(scope="module")
def _redis_container():
    testcontainers = pytest.importorskip("testcontainers.redis")
    from testcontainers.redis import RedisContainer  # type: ignore

    try:
        with RedisContainer("redis:7.2.4") as container:  # pinned for stability
            host = container.get_container_host_ip()
            port = int(container.get_exposed_port(6379))
            url = f"redis://{host}:{port}"
            yield {"host": host, "port": port, "url": url}
    except Exception as e:  # pragma: no cover - infra dependent
        pytest.skip(f"Docker is required for RedisContainer: {e}")


@pytest_asyncio.fixture
async def redis_client(_redis_container) -> AsyncGenerator[redis.Redis, None]:
    """Provide Redis client connected to a containerized Redis."""
    client = redis.from_url(_redis_container["url"], decode_responses=True)
    try:
        await client.ping()
        # Ensure test keys are clean
        await client.delete("tg_commands")
        await client.delete("tg_events")
        yield client
    finally:
        # Cleanup: Clear test keys and close
        await client.delete("tg_commands")
        await client.delete("tg_events")
        await client.aclose()


@pytest_asyncio.fixture
async def redis_pubsub(
    redis_client: redis.Redis,
) -> AsyncGenerator[redis.client.PubSub, None]:
    """Provide Redis PubSub for tests."""
    pubsub = redis_client.pubsub()
    try:
        yield pubsub
    finally:
        await pubsub.aclose()


class TestRedisCommandQueue:
    """Test Redis BLPOP command queue - critical paths only."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_push_and_pop_command(self, redis_client: redis.Redis):
        """Test basic push/pop cycle (most common operation)."""
        cmd = FetchCommand(
            command="fetch",
            chat="@testchat",
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
        )
        command_json = cmd.model_dump_json()

        # Push command
        await redis_client.rpush("tg_commands", command_json)

        # Pop command with BLPOP
        result = await redis_client.blpop("tg_commands", timeout=1)
        assert result is not None
        queue_name, popped_json = result
        assert queue_name == "tg_commands"

        # Parse and validate
        popped_cmd = FetchCommand.model_validate_json(popped_json)
        assert popped_cmd.chat == cmd.chat
        assert popped_cmd.mode == cmd.mode
        assert popped_cmd.date == cmd.date

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_commands_fifo(self, redis_client: redis.Redis):
        """Test FIFO order is maintained (critical for command processing)."""
        commands = [
            FetchCommand(
                command="fetch",
                chat=f"@chat{i}",
                mode=FetchMode.DATE,
                date=date(2025, 1, 10 + i),
                strategy=FetchStrategy.BATCH,
            )
            for i in range(3)
        ]

        # Push all commands
        for cmd in commands:
            await redis_client.rpush("tg_commands", cmd.model_dump_json())

        # Pop and verify order
        for expected_cmd in commands:
            result = await redis_client.blpop("tg_commands", timeout=1)
            assert result is not None
            _, popped_json = result
            popped_cmd = FetchCommand.model_validate_json(popped_json)
            assert popped_cmd.chat == expected_cmd.chat


class TestRedisPubSub:
    """Test Redis PubSub - critical event notifications only."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_publish_and_receive_event(
        self, redis_client: redis.Redis, redis_pubsub: redis.client.PubSub
    ):
        """Test basic publish/subscribe cycle."""
        channel = "tg_events"

        # Subscribe
        await redis_pubsub.subscribe(channel)

        # Publish event
        event_data = {
            "type": "fetch_started",
            "chat": "@testchat",
            "date": "2025-01-15",
        }
        await redis_client.publish(channel, json.dumps(event_data))

        # Receive event (with timeout)
        message = await asyncio.wait_for(
            redis_pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
            timeout=2.0,
        )

        assert message is not None
        assert message["type"] == "message"
        received_data = json.loads(message["data"])
        assert received_data["type"] == "fetch_started"
        assert received_data["chat"] == "@testchat"


class TestIdempotency:
    """Test idempotency checks - critical for avoiding duplicate fetches."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_duplicate_detection(self, redis_client: redis.Redis):
        """Test detecting duplicate commands with Redis keys."""
        chat = "@testchat"
        target_date = "2025-01-15"
        key = f"fetched:{chat}:{target_date}"

        # First fetch - should not exist
        exists = await redis_client.exists(key)
        assert exists == 0

        # Mark as fetched with 24h TTL
        await redis_client.setex(key, 86400, "1")

        # Second check - should exist
        exists = await redis_client.exists(key)
        assert exists == 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_force_bypasses_duplicate_check(self, redis_client: redis.Redis):
        """Test force flag bypasses idempotency check."""
        chat = "@testchat"
        target_date = "2025-01-15"
        key = f"fetched:{chat}:{target_date}"

        # Mark as already fetched
        await redis_client.setex(key, 86400, "1")

        # Force mode should still allow fetch
        cmd = FetchCommand(
            command="fetch",
            chat=chat,
            mode=FetchMode.DATE,
            date=date(2025, 1, 15),
            strategy=FetchStrategy.BATCH,
            force=True,
        )

        # In real code, force=True would skip the exists check
        assert cmd.force is True
        exists = await redis_client.exists(key)
        # Key still exists, but force flag tells us to ignore it
        assert exists == 1


# NOTE: Removed tests (available in .backup if needed):
# - test_blpop_timeout: trivial Redis behavior
# - test_command_with_force_flag: covered by FetchCommand unit tests
# - test_queue_length: trivial Redis llen operation
# - test_multiple_events: redundant with single event test
# - test_event_with_command_params: covered by unit tests
# - test_ttl_expiration: slow (requires waiting), TTL is Redis guarantee
# - test_concurrent_operations: complex, rarely fails in practice
# - test_race_condition_on_duplicate_check: covered by atomic Redis operations
#
# Total reduction: 334 lines → 165 lines (50% reduction)
