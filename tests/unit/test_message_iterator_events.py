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


class FakePublisher:
    def __init__(self) -> None:
        self.started = []
        self.stages = []
        self.progress = []

    def publish_fetch_started(
        self, chat: str, date: str, strategy: str
    ) -> None:  # noqa: ARG002
        self.started.append((chat, date))

    def publish_fetch_stage(
        self, chat: str, date: str, stage: str
    ) -> None:  # noqa: ARG002
        self.stages.append((chat, date, stage))

    def publish_fetch_progress(
        self, chat: str, date: str, messages_processed: int, messages_fetched: int
    ) -> None:  # noqa: ARG002,E501
        self.progress.append((chat, date, messages_processed, messages_fetched))


def test_iterator_emits_start_and_progress_events():
    # Arrange: date bounds
    start_date = dt.date(2025, 11, 3)
    start_dt = dt.datetime.combine(start_date, dt.datetime.min.time()).replace(
        tzinfo=dt.timezone.utc
    )
    end_dt = dt.datetime.combine(
        start_date + dt.timedelta(days=1), dt.datetime.min.time()
    ).replace(tzinfo=dt.timezone.utc)

    # Messages: one inside, one at end (skip), one before start (break)
    inside = DummyMessage(10, start_dt + dt.timedelta(hours=1))
    at_end = DummyMessage(11, end_dt)
    before = DummyMessage(12, start_dt - dt.timedelta(seconds=1))
    client = DummyClient([inside, at_end, before])

    # enable progress events, interval=2 -> progress fires once at processed==2
    cfg = SimpleNamespace(enable_progress_events=True, progress_interval=2)
    pub = FakePublisher()

    iterator = MessageIterator(
        client=client,
        entity=object(),
        source_id="@test",
        start_date=start_date,
        start_datetime=start_dt,
        end_datetime=end_dt,
        config=cfg,
        event_publisher=pub,
        metrics=NoopMetricsAdapter(),
        strategy_name="by_date",
        correlation_id="cid",
    )

    async def handler(_):  # noqa: ANN001
        return True

    # Act
    import asyncio

    fetched, processed = asyncio.run(iterator.run(handler))

    # Assert
    assert fetched >= 1
    assert processed == 3
    # Start events once
    assert len(pub.started) == 1
    assert len(pub.stages) >= 1
    # One progress event at processed==2 (interval=2)
    assert len(pub.progress) == 1
    _, _, msgs_processed, _ = pub.progress[0]
    assert msgs_processed == 2
