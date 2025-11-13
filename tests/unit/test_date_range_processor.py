from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from src.core.config import FetcherConfig
from src.services.fetching import date_range_processor as drp_mod


class FakeIterator:
    def __init__(
        self,
        *,
        client,
        entity,
        source_id,
        start_date,
        start_datetime,
        end_datetime,
        config,
        event_publisher,
        metrics,
        strategy_name,
        correlation_id,
    ):
        # capture args for assertions if needed
        self.kw = {
            "client": client,
            "entity": entity,
            "source_id": source_id,
            "start_date": start_date,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "config": config,
            "event_publisher": event_publisher,
            "metrics": metrics,
            "strategy_name": strategy_name,
            "correlation_id": correlation_id,
        }

    async def run(self, handle):
        # pretend we processed 5 messages successfully, 0 failed
        return (5, 0)


def make_config() -> FetcherConfig:
    return FetcherConfig(
        fetch_mode="yesterday",
        api_id=12345,
        api_hash="hash",
        session_name="test",
        redis_url="redis://localhost:6379/0",
    )


@pytest.mark.asyncio
async def test_date_range_processor_iterate_monkeypatched(monkeypatch):
    # Monkeypatch the MessageIterator class used inside module
    monkeypatch.setattr(drp_mod, "MessageIterator", FakeIterator)

    cfg = make_config()
    processor = drp_mod.DateRangeProcessor(
        config=cfg,
        event_publisher=None,
        metrics=SimpleNamespace(),  # dummy metrics adapter
        strategy_name="yesterday",
    )

    async def noop_handle(_msg: Any):
        return True

    # Prepare minimal args
    now = datetime.now(tz=timezone.utc)
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = start_dt.replace(hour=23, minute=59)

    count_ok, count_fail = await processor.iterate(
        client=SimpleNamespace(),
        entity=SimpleNamespace(),
        source_info=SimpleNamespace(id="src1"),
        start_date=date.today(),
        start_datetime=start_dt,
        end_datetime=end_dt,
        correlation_id="cid-123",
        handle=noop_handle,
    )

    assert (count_ok, count_fail) == (5, 0)
