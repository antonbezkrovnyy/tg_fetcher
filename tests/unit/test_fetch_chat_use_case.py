import asyncio
from datetime import date
from typing import Any, AsyncIterator

import pytest

from src.core.config import FetcherConfig
from src.services.usecases.fetch_chat import FetchChatDeps, FetchChatUseCase


class _TG:
    async def get_entity(self, client: Any, chat_identifier: str) -> Any:
        return {"chat": chat_identifier}


class _Mapper:
    def extract_source_info(self, entity: Any, chat_identifier: str):
        from src.models.schemas import SourceInfo

        return SourceInfo(
            id=chat_identifier,
            title=chat_identifier,
            url=f"https://t.me/{chat_identifier.lstrip('@')}",
        )


class _Strategy:
    def __init__(self, ranges: list[tuple[date, date]]):
        self._ranges = ranges

    def get_strategy_name(self) -> str:
        return "test"

    def get_date_ranges(
        self, client: Any, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]:
        async def _gen():
            for r in self._ranges:
                yield r

        return _gen()


class _DateRangeUC:
    def __init__(self, ret: int):
        self._ret = ret

    async def execute(self, **kwargs) -> int:  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)
        return self._ret


@pytest.mark.asyncio
async def test_fetch_chat_use_case_aggregates_results():
    cfg = FetcherConfig()
    deps = FetchChatDeps(
        config=cfg,
        telegram_gateway=_TG(),
        source_mapper=_Mapper(),
        date_range_use_case=_DateRangeUC(5),
    )
    uc = FetchChatUseCase(deps)

    strat = _Strategy(
        [(date(2025, 1, 1), date(2025, 1, 1)), (date(2025, 1, 2), date(2025, 1, 2))]
    )
    total = await uc.execute(
        client=None,
        chat_identifier="@test",
        strategy=strat,
        correlation_id="cid",
        concurrency=2,
    )

    assert total == 10
