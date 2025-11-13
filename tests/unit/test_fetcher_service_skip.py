import datetime as dt
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.models.schemas import SourceInfo
from src.services.fetcher_service import FetcherService


class FakeRepo:
    def __init__(self, base: Path) -> None:
        self.base = base

    def get_output_file_path(self, source_id: str, start_date: dt.date) -> Path:
        p = self.base / source_id.lstrip("@") / f"{start_date.isoformat()}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def get_summary_path(self, source_id: str, start_date: dt.date) -> Path:
        p = self.base / source_id.lstrip("@") / f"{start_date.isoformat()}_summary.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


class FakeMetrics:
    def __init__(self) -> None:
        self.reset_calls: list[tuple[str, str]] = []

    def set_progress(
        self, chat: str, date_str: str, value: int
    ) -> None:  # pragma: no cover
        return

    def reset_progress(self, chat: str, date_str: str) -> None:
        self.reset_calls.append((chat, date_str))


class FakePublisher:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def connect(self) -> None:  # pragma: no cover
        return

    def publish_fetch_skipped(
        self,
        *,
        chat: str,
        date: str,
        reason: str,
        checksum_expected: str | None,
        checksum_actual: str | None,
    ) -> None:
        self.calls.append(
            {
                "chat": chat,
                "date": date,
                "reason": reason,
                "checksum_expected": checksum_expected,
                "checksum_actual": checksum_actual,
            }
        )


@pytest.mark.parametrize("checksums_match", [True, False])
def test_maybe_skip_existing_emits_event_and_resets_gauge(
    tmp_path: Path, checksums_match: bool
) -> None:
    # Arrange service with fakes via attribute injection (private helper under test)
    svc = object.__new__(FetcherService)
    svc.repository = FakeRepo(tmp_path)
    svc.metrics = FakeMetrics()
    svc.event_publisher = FakePublisher()
    svc.config = SimpleNamespace(enable_progress_events=True)

    source = SourceInfo(
        id="@test_chat", title="Test", url="https://t.me/test_chat", type="channel"
    )
    start_date = dt.date(2025, 1, 1)

    # Prepare existing output file and matching/mismatching summary checksum
    out_path = svc.repository.get_output_file_path(source.id, start_date)
    out_path.write_bytes(b"hello world")

    # Compute checksum the same way as service does
    expected_checksum = svc._compute_file_checksum(out_path)
    assert expected_checksum is not None
    if not checksums_match:
        # flip the checksum to force mismatch
        expected_checksum = "0" * 64

    summary_path = svc.repository.get_summary_path(source.id, start_date)
    summary_path.write_text(
        json.dumps({"file_checksum_sha256": expected_checksum}),
        encoding="utf-8",
    )

    # Act
    skipped = svc._maybe_skip_existing(source, start_date, correlation_id="corr-1")

    # Assert
    if checksums_match:
        assert skipped is True
        # Event published once with correct payload
        assert len(svc.event_publisher.calls) == 1
        call = svc.event_publisher.calls[0]
        assert call["chat"] == source.id
        assert call["date"] == start_date.isoformat()
        assert call["reason"] == "already_exists_same_checksum"
        # reset gauge called once for chat/date
        assert svc.metrics.reset_calls == [(source.id, start_date.isoformat())]
    else:
        assert skipped is False
        assert svc.event_publisher.calls == []
        assert svc.metrics.reset_calls == []
