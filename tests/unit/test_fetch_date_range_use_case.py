import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from telethon import TelegramClient
from telethon.hints import Entity

from src.core.config import FetcherConfig
from src.models.schemas import SourceInfo
from src.services.usecases.fetch_date_range import (
    FetchDateRangeDeps,
    FetchDateRangeUseCase,
)


class _Repo:
    def __init__(self) -> None:
        self.saved = False

    def create_collection(self, *, source_info: SourceInfo, messages: list[Any]) -> Any:
        class Col:
            def __init__(self) -> None:
                self.messages: list[Any] = []

            def add_sender(self, *_args: Any, **_kwargs: Any) -> None:
                pass

        return Col()

    def save_collection(
        self, *, source_name: str, target_date: date, collection: Any
    ) -> str | None:
        self.saved = True
        return "path.json"

    def get_output_file_path(self, source_id: str, start_date: date) -> Any:
        return "data.json"

    def get_summary_path(self, source_id: str, start_date: date) -> Any:
        return "summary.json"


class _Pre:
    def enrich(self, message: Any) -> Any:
        return message

    def maybe_merge_short(self, last_message: Any | None, new_message: Any) -> bool:
        return False


class _Map:
    def get_sender_name(self, sender_obj: Any) -> str:
        return "sender"


class _Iter:
    async def iterate(self, **kwargs):  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)
        return (0, 0)


class _ProgSvc:
    def reset_gauge(self, chat: str, date: str) -> None:
        pass

    def publish_stage(self, *, chat: str, date: str, stage: str) -> None:
        pass


class _ProgTr:
    def __init__(self, completed: bool) -> None:
        self.completed = completed

    def is_date_completed(self, source_id: str, d: date) -> bool:
        return self.completed

    def mark_in_progress(self, source_id: str, d: date) -> None:
        pass

    def mark_completed(
        self,
        *,
        source: str,
        target_date: date,
        message_count: int,
        last_message_id: int | None,
    ) -> None:
        pass


class _Final:
    def finalize(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        pass


async def _extract(_: TelegramClient, __: Entity, ___: Any, ____: SourceInfo) -> Any:
    return object()


@pytest.mark.asyncio
async def test_fetch_date_range_use_case_skip_when_completed():
    cfg = FetcherConfig()
    deps = FetchDateRangeDeps(
        config=cfg,
        repository=_Repo(),
        preprocessor=_Pre(),
        source_mapper=_Map(),
        date_range_processor=_Iter(),
        progress_service=_ProgSvc(),
        progress_tracker=_ProgTr(completed=True),
        finalization_orchestrator=_Final(),
        extract_message_data=_extract,
    )
    uc = FetchDateRangeUseCase(deps)

    src = SourceInfo(id="@test", title="test", url="https://t.me/test")
    fetched = await uc.execute(
        client=None,  # type: ignore[arg-type]
        entity=None,  # type: ignore[arg-type]
        source_info=src,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 1),
        correlation_id="cid",
    )

    assert fetched == 0
