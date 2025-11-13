import asyncio
import json
from contextlib import suppress
from typing import Any, List

import pytest
import redis

from src.services.command_subscriber import CommandSubscriber, create_fetch_command


class FakeMetricsAdapter:
    def __init__(self) -> None:
        self.received: int = 0
        self.success: int = 0
        self.timeouts: int = 0
        self.failed: List[str] = []

    # Progress API (unused here)
    def set_progress(
        self, chat: str, date_str: str, value: int
    ) -> None:  # noqa: ARG002
        return

    def reset_progress(self, chat: str, date_str: str) -> None:  # noqa: ARG002
        return

    # Command subscriber counters
    def inc_command_received(self, queue: str, worker: str) -> None:  # noqa: ARG002
        self.received += 1

    def inc_command_success(self, queue: str, worker: str) -> None:  # noqa: ARG002
        self.success += 1

    def inc_command_failed(
        self, queue: str, worker: str, error_type: str
    ) -> None:  # noqa: ARG002
        self.failed.append(error_type)

    def inc_command_timeout(self, queue: str, worker: str) -> None:  # noqa: ARG002
        self.timeouts += 1


@pytest.fixture(scope="module")
def redis_container():
    testcontainers = pytest.importorskip("testcontainers.redis")
    from testcontainers.redis import RedisContainer  # type: ignore

    try:
        with RedisContainer("redis:7.2.4") as container:  # pinned for stability
            host = container.get_container_host_ip()
            port = int(container.get_exposed_port(6379))
            url = f"redis://{host}:{port}"
            yield {"host": host, "port": port, "url": url}
    except Exception as e:  # pragma: no cover - infra-dependent
        pytest.skip(f"Docker is required for RedisContainer: {e}")


@pytest.mark.asyncio
async def test_subscriber_handles_fetch_command_success(redis_container):
    metrics = FakeMetricsAdapter()

    # Arrange subscriber
    sub = CommandSubscriber(
        redis_url=redis_container["url"],
        command_handler=lambda data: asyncio.sleep(0),  # fast no-op handler
        worker_id="worker-1",
        commands_queue="tg_commands_test",
        blpop_timeout=1,
        metrics=metrics,
    )
    sub.connect()

    # Push command
    r = redis.from_url(redis_container["url"], decode_responses=True)
    cmd = create_fetch_command(chat="ru_python", days_back=1, limit=10)
    r.rpush("tg_commands_test", json.dumps(cmd))

    # Act: run listen loop briefly
    task = asyncio.create_task(sub.listen())
    # Wait until command is processed or timeout
    for _ in range(20):
        if metrics.success >= 1:
            break
        await asyncio.sleep(0.1)
    sub.stop()
    with suppress(Exception):
        await asyncio.wait_for(task, timeout=2)

    # Assert
    assert metrics.received >= 1
    assert metrics.success >= 1
    assert "unknown_command" not in metrics.failed


@pytest.mark.asyncio
async def test_subscriber_unknown_command_counts_failed(redis_container):
    metrics = FakeMetricsAdapter()
    sub = CommandSubscriber(
        redis_url=redis_container["url"],
        command_handler=lambda data: asyncio.sleep(0),
        worker_id="worker-2",
        commands_queue="tg_commands_test2",
        blpop_timeout=1,
        metrics=metrics,
    )
    sub.connect()

    r = redis.from_url(redis_container["url"], decode_responses=True)
    r.rpush("tg_commands_test2", json.dumps({"command": "ping"}))

    task = asyncio.create_task(sub.listen())
    for _ in range(20):
        if any(et == "unknown_command" for et in metrics.failed):
            break
        await asyncio.sleep(0.1)
    sub.stop()
    with suppress(Exception):
        await asyncio.wait_for(task, timeout=2)

    assert metrics.received >= 1
    assert any(et == "unknown_command" for et in metrics.failed)


@pytest.mark.asyncio
async def test_subscriber_timeout_increments_without_messages(redis_container):
    metrics = FakeMetricsAdapter()
    sub = CommandSubscriber(
        redis_url=redis_container["url"],
        command_handler=lambda data: asyncio.sleep(0),
        worker_id="worker-3",
        commands_queue="tg_commands_test3",
        blpop_timeout=1,
        metrics=metrics,
    )
    sub.connect()

    task = asyncio.create_task(sub.listen())
    # Wait a bit longer than one BLPOP timeout window to ensure at least one timeout is hit
    await asyncio.sleep(1.5)
    sub.stop()
    with suppress(Exception):
        await asyncio.wait_for(task, timeout=2)

    assert metrics.timeouts >= 1


@pytest.mark.asyncio
async def test_subscriber_handler_error_counts_failed(redis_container):
    metrics = FakeMetricsAdapter()

    async def failing_handler(data: Any) -> None:  # noqa: ARG001
        raise ValueError("boom")

    sub = CommandSubscriber(
        redis_url=redis_container["url"],
        command_handler=failing_handler,
        worker_id="worker-4",
        commands_queue="tg_commands_test4",
        blpop_timeout=1,
        metrics=metrics,
    )
    sub.connect()

    r = redis.from_url(redis_container["url"], decode_responses=True)
    cmd = create_fetch_command(chat="ru_python", days_back=1, limit=1)
    r.rpush("tg_commands_test4", json.dumps(cmd))

    task = asyncio.create_task(sub.listen())
    for _ in range(20):
        if any(et == "command_handler_error" for et in metrics.failed):
            break
        await asyncio.sleep(0.1)
    sub.stop()
    with suppress(Exception):
        await asyncio.wait_for(task, timeout=2)

    assert metrics.received >= 1
    assert any(et == "command_handler_error" for et in metrics.failed)
