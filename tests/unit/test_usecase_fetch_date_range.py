import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest

from src.core.config import FetcherConfig
from src.models.schemas import MessageCollection, SourceInfo
from src.services.usecases.fetch_date_range import (
    FetchDateRangeDeps,
    FetchDateRangeUseCase,
)


class RepoFake:
    def __init__(self):
        self.saved = []

    def create_collection(self, *, source_info, messages):
        return MessageCollection(source_info=source_info, messages=messages)

    def save_collection(self, *, source_name, target_date, collection):
        self.saved.append((source_name, target_date, len(collection.messages)))
        return "/tmp/file.json"

    def get_output_file_path(
        self, source_id, start_date
    ):  # for SkipExistingChecker signature
        return None

    def get_summary_path(self, source_id, start_date):
        return None


class PreprocFake:
    def enrich(self, message):
        return message

    def maybe_merge_short(self, last_message, new_message):
        return False


class SourceMapperFake:
    def get_sender_name(self, sender_obj):
        return "SenderName"


class DateRangeProcessorFake:
    def __init__(self, to_yield=2):
        self.calls = []
        self._to_yield = to_yield

    async def iterate(self, *, handle, **_: object):
        # Simulate two messages handled
        class Msg:
            def __init__(self, i):
                self.sender = object()
                self.id = i

        for i in range(self._to_yield):
            mdata = type("M", (), {"id": i + 1, "sender_id": 123})()
            await handle(Msg(i))
        return self._to_yield, self._to_yield


class ProgressServiceFake:
    def __init__(self):
        self.reset_calls = []
        self.stages = []

    def reset_gauge(self, chat, date):
        self.reset_calls.append((chat, date))

    def publish_stage(self, *, chat, date, stage):
        self.stages.append((chat, date, stage))


class ProgressTrackerFake:
    def __init__(self, completed=False):
        self.completed = completed
        self.in_progress = []
        self.completed_calls = []

    def is_date_completed(self, source_id, date_):
        return self.completed

    def mark_in_progress(self, source_id, date_):
        self.in_progress.append((source_id, date_))

    def mark_completed(self, *, source, target_date, message_count, last_message_id):
        self.completed_calls.append(
            (source, target_date, message_count, last_message_id)
        )


class FinalizeFake:
    def __init__(self):
        self.calls = []

    def finalize(self, **kwargs):
        self.calls.append(kwargs)


@pytest.mark.asyncio
async def test_usecase_already_completed_early_return():
    cfg = FetcherConfig(
        telegram_api_id=1,
        telegram_api_hash="a" * 32,
        telegram_phone="+12345678901",
        telegram_chats=["@c"],
        enable_progress_events=True,
        force_refetch=False,
    )
    deps = FetchDateRangeDeps(
        config=cfg,
        repository=RepoFake(),
        preprocessor=PreprocFake(),
        source_mapper=SourceMapperFake(),
        date_range_processor=DateRangeProcessorFake(),
        progress_service=ProgressServiceFake(),
        progress_tracker=ProgressTrackerFake(completed=True),
        finalization_orchestrator=FinalizeFake(),
        extract_message_data=lambda *a, **k: asyncio.sleep(0),
    )
    uc = FetchDateRangeUseCase(deps)
    src = SourceInfo(id="@c", title="T", url="u")

    fetched = await uc.execute(
        client=object(),
        entity=object(),
        source_info=src,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 1),
        correlation_id="cid",
    )
    assert fetched == 0
    # No gauge reset on this early branch
    assert deps.progress_service.reset_calls == []


@pytest.mark.asyncio
async def test_usecase_checksum_skip(monkeypatch):
    cfg = FetcherConfig(
        telegram_api_id=1,
        telegram_api_hash="a" * 32,
        telegram_phone="+12345678901",
        telegram_chats=["@c"],
        enable_progress_events=True,
        force_refetch=False,
    )

    class FakeChecker:
        def __init__(self, repo):
            pass

        def decide(self, source_id, start_date):
            from src.services.skip.skip_checker import SkipDecision

            return SkipDecision(should_skip=True, reason="already_exists_same_checksum")

    monkeypatch.setattr(
        "src.services.usecases.fetch_date_range.SkipExistingChecker", FakeChecker
    )

    deps = FetchDateRangeDeps(
        config=cfg,
        repository=RepoFake(),
        preprocessor=PreprocFake(),
        source_mapper=SourceMapperFake(),
        date_range_processor=DateRangeProcessorFake(),
        progress_service=ProgressServiceFake(),
        progress_tracker=ProgressTrackerFake(completed=False),
        finalization_orchestrator=FinalizeFake(),
        extract_message_data=lambda *a, **k: asyncio.sleep(0),
    )

    uc = FetchDateRangeUseCase(deps)
    src = SourceInfo(id="@c", title="T", url="u")

    fetched = await uc.execute(
        client=object(),
        entity=object(),
        source_info=src,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 1),
        correlation_id="cid",
    )

    assert fetched == 0
    # Gauge reset should happen on checksum skip
    assert deps.progress_service.reset_calls == [("@c", "2025-01-01")]


@pytest.mark.asyncio
async def test_usecase_happy_path_saves_and_finalizes():
    cfg = FetcherConfig(
        telegram_api_id=1,
        telegram_api_hash="a" * 32,
        telegram_phone="+12345678901",
        telegram_chats=["@c"],
        enable_progress_events=True,
    )

    async def extract_message_data(client, entity, msg, source_info):
        # Provide minimal attributes used later
        return type("D", (), {"id": 42, "sender_id": 777})()

    drp = DateRangeProcessorFake(to_yield=2)
    deps = FetchDateRangeDeps(
        config=cfg,
        repository=RepoFake(),
        preprocessor=PreprocFake(),
        source_mapper=SourceMapperFake(),
        date_range_processor=drp,
        progress_service=ProgressServiceFake(),
        progress_tracker=ProgressTrackerFake(completed=False),
        finalization_orchestrator=FinalizeFake(),
        extract_message_data=extract_message_data,
    )

    uc = FetchDateRangeUseCase(deps)
    src = SourceInfo(id="@c", title="T", url="u")

    fetched = await uc.execute(
        client=object(),
        entity=object(),
        source_info=src,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 1),
        correlation_id="cid",
    )

    # DateRangeProcessorFake yields 2 messages; both appended
    assert fetched == 2
    assert deps.repository.saved[0][2] == 2
    # Stage 'saving' published and gauge reset called at end
    assert ("@c", "2025-01-01", "saving") in deps.progress_service.stages
    assert deps.progress_service.reset_calls[-1] == ("@c", "2025-01-01")
    # mark_completed called with last_message_id from last appended message (id=2 in fake)
    assert deps.progress_tracker.completed_calls
