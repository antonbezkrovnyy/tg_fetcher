import asyncio
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.core import retry as retry_mod


@pytest.mark.asyncio
async def test_retry_with_backoff_eventual_success():
    attempts = {"n": 0}

    async def op():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    async def fast_sleep(_s, *_args, **_kwargs):
        return None

    with patch.object(asyncio, "sleep", new=fast_sleep):
        result = await retry_mod.retry_with_backoff(
            op, max_attempts=3, jitter=False, base_delay=0.01
        )
    assert result == "ok"
    assert attempts["n"] == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_exhausted():
    async def op():
        raise ValueError("boom")

    async def fast_sleep(_s, *_args, **_kwargs):
        return None

    with patch.object(asyncio, "sleep", new=fast_sleep):
        with pytest.raises(ValueError):
            await retry_mod.retry_with_backoff(
                op, max_attempts=2, jitter=False, base_delay=0.0, retry_on=(ValueError,)
            )


@pytest.mark.asyncio
async def test_handle_flood_wait_respects_limit():
    # Monkeypatch FloodWaitError in module to a simple Exception with seconds attr
    class FakeFloodWait(Exception):
        def __init__(self, seconds: int):
            super().__init__(f"FloodWait {seconds}")
            self.seconds = seconds

    with patch.object(retry_mod, "FloodWaitError", FakeFloodWait):
        calls = {"n": 0}

        async def op():
            calls["n"] += 1
            raise FakeFloodWait(2)

        # To avoid real sleep, patch asyncio.sleep to a no-op coroutine
        async def fast_sleep(_s):
            return None

        with patch.object(asyncio, "sleep", new=fast_sleep):
            # Limit is 1 second; error should raise immediately
            with pytest.raises(FakeFloodWait):
                await retry_mod.handle_flood_wait(op, max_wait_seconds=1)


@pytest.mark.asyncio
async def test_safe_operation_combines_retry_and_floodwait():
    # Simulate first FloodWait (allowed), then success
    class FakeFloodWait(Exception):
        def __init__(self, seconds: int):
            super().__init__(f"FloodWait {seconds}")
            self.seconds = seconds

    with patch.object(retry_mod, "FloodWaitError", FakeFloodWait):
        calls = {"n": 0}

        async def op():
            calls["n"] += 1
            if calls["n"] == 1:
                raise FakeFloodWait(0)
            return "ok"

        async def fast_sleep(_s):
            return None

        with patch.object(asyncio, "sleep", new=fast_sleep):
            result = await retry_mod.safe_operation(
                op, max_attempts=2, base_delay=0.0, max_delay=0.0
            )
    assert result == "ok"
    assert calls["n"] == 2
