import asyncio
import datetime as dt
from types import SimpleNamespace

from src.observability.metrics_adapter import NoopMetricsAdapter
from src.services.fetching.message_iterator import MessageIterator


class DummyMessage:
    def __init__(self, mid: int, when: dt.datetime) -> None:
        self.id = mid
        self.date = when
        self.message = "x"


class DummyClient:
    def __init__(self, messages):
        self._messages = messages

    async def iter_messages(
        self, entity, offset_date=None, reverse=False
    ):  # noqa: ARG002
        for m in self._messages:
            yield m


async def _run_iterator(messages, start_date: dt.date):
    start_dt = dt.datetime.combine(start_date, dt.datetime.min.time()).replace(
        tzinfo=dt.timezone.utc
    )
    end_dt = dt.datetime.combine(
        start_date + dt.timedelta(days=1), dt.datetime.min.time()
    ).replace(tzinfo=dt.timezone.utc)

    client = DummyClient(messages)
    cfg = SimpleNamespace(enable_progress_events=False, progress_interval=1000)
    it = MessageIterator(
        client=client,
        entity=object(),
        source_id="@test",
        start_date=start_date,
        start_datetime=start_dt,
        end_datetime=end_dt,
        config=cfg,  # duck-typed config
        event_publisher=None,
        metrics=NoopMetricsAdapter(),
        strategy_name="by_date",
        correlation_id="cid",
    )

    async def handler(_):  # noqa: ANN001
        return True

    return await it.run(handler)


def test_iterator_bounds_and_counts():
    start_date = dt.date(2025, 11, 3)
    start_dt = dt.datetime.combine(start_date, dt.datetime.min.time()).replace(
        tzinfo=dt.timezone.utc
    )
    end_dt = dt.datetime.combine(
        start_date + dt.timedelta(days=1), dt.datetime.min.time()
    ).replace(tzinfo=dt.timezone.utc)

    messages = [
        DummyMessage(1, end_dt),  # >= end -> skip
        DummyMessage(2, start_dt + dt.timedelta(hours=1)),  # inside -> handle
        DummyMessage(3, start_dt - dt.timedelta(seconds=1)),  # < start -> break
    ]

    fetched, processed = asyncio.run(_run_iterator(messages, start_date))

    assert fetched == 1
    assert processed == 3
