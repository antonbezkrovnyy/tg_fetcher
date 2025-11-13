from datetime import datetime, timedelta

import pytest
from freezegun import freeze_time

from src.services.strategy.by_date import ByDateStrategy
from src.services.strategy.full import FullHistoryStrategy


def test_by_date_invalid_format_raises():
    with pytest.raises(ValueError):
        ByDateStrategy("2025/11/01")


@pytest.mark.asyncio
async def test_by_date_get_date_ranges_yields_one():
    s = ByDateStrategy("2025-11-10")
    # Client arg is unused; chat_identifier only for logging
    ranges = []
    async for r in s.get_date_ranges(client=None, chat_identifier="@c"):
        ranges.append(r)
    assert ranges == [(datetime(2025, 11, 10).date(), datetime(2025, 11, 10).date())]


class _FakeClient:
    async def get_entity(self, chat_identifier):  # noqa: ANN001
        return object()

    async def get_messages(self, entity, limit, reverse):  # noqa: ANN001, D401
        # Oldest message has date 3 days before 'today'
        dt = datetime(2025, 11, 10, 12, 0, 0)
        return [type("Msg", (), {"date": dt})()]


@freeze_time("2025-11-13 09:00:00")
@pytest.mark.asyncio
async def test_full_history_single_chunk_to_yesterday():
    s = FullHistoryStrategy()
    client = _FakeClient()
    ranges = []
    async for r in s.get_date_ranges(client=client, chat_identifier="@c"):
        ranges.append(r)
    # yesterday=2025-11-12; start=2025-11-10 → single chunk (10..12)
    assert ranges == [(datetime(2025, 11, 10).date(), datetime(2025, 11, 12).date())]
