import asyncio
from datetime import date as date_cls
from datetime import datetime, timedelta, timezone

import pytest

from src.core.config import FetcherConfig
from src.services.fetching.message_iterator import MessageIterator


class FakeClient:
    def __init__(self, messages):
        self._messages = messages

    async def iter_messages(self, entity, offset_date=None, reverse=False):
        for m in self._messages:
            # Simulate async generator
            await asyncio.sleep(0)
            yield m


class Msg:
    def __init__(self, dt):
        self.date = dt


class RaisingPublisher:
    def publish_fetch_started(self, *a, **kw):
        raise RuntimeError("start")

    def publish_fetch_stage(self, *a, **kw):
        raise RuntimeError("stage")

    def publish_fetch_progress(self, *a, **kw):
        raise RuntimeError("progress")


class MetricsStub:
    def __init__(self):
        self.calls = []

    def set_progress(
        self, chat: str, date: str, value: int
    ):  # noqa: D401 - simple stub
        self.calls.append((chat, date, value))


async def _handler_factory(record, raise_on_second=False):
    async def handle(message):
        # First within-bound message contributes; second raises if requested
        if raise_on_second and len(record) == 1:
            raise RuntimeError("handler boom")
        record.append(message)
        return True

    return handle


@pytest.mark.asyncio
async def test_message_iterator_progress_bounds_and_exceptions(tmp_path):
    start_date = date_cls(2025, 1, 10)
    start_dt = datetime(2025, 1, 10, tzinfo=timezone.utc)
    end_dt = datetime(2025, 1, 11, tzinfo=timezone.utc)

    over_end = Msg(end_dt)  # >= end -> skip
    within1 = Msg(start_dt + timedelta(hours=1))
    within2 = Msg(start_dt + timedelta(hours=2))  # handler raises on this
    none_date = type("N", (), {"date": None})()
    below_start = Msg(start_dt - timedelta(seconds=1))  # < start -> stop

    client = FakeClient([over_end, within1, within2, none_date, below_start])

    # Minimal valid config
    cfg = FetcherConfig(
        telegram_api_id=123456,
        telegram_api_hash="a" * 32,
        telegram_phone="+12345678901",
        telegram_chats=["@c"],
        progress_interval=2,
        enable_progress_events=True,
    )

    metrics = MetricsStub()
    publisher = RaisingPublisher()

    it = MessageIterator(
        client=client,
        entity=object(),
        source_id="@c",
        start_date=start_date,
        start_datetime=start_dt,
        end_datetime=end_dt,
        config=cfg,
        event_publisher=publisher,
        metrics=metrics,  # type: ignore[arg-type]
        strategy_name="by_date",
        correlation_id="cid-1",
    )

    record = []
    handle = await _handler_factory(record, raise_on_second=True)

    fetched, processed = await it.run(handle)

    # fetched only first within-bound message; processed counts msg with date (skip+within+within+below)
    assert fetched == 1
    assert processed == 4
    # metrics gauge set at start and at least once during progress
    assert metrics.calls[0][2] == 0  # initial reset
    assert any(v == 2 for (_, _, v) in metrics.calls)  # progress at processed=2
