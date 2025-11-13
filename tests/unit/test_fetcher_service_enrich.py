import datetime as dt
import tempfile
from pathlib import Path

from src.models.schemas import Message, MessageCollection, SourceInfo
from src.services.fetcher_service import FetcherService


class FakeRepo:
    def __init__(self, collection):
        self._collection = collection

    def load_collection(self, source_id: str, d: dt.date):  # noqa: ARG002
        return self._collection

    # Provide artifact path helpers to match production repository API
    def get_summary_path(self, source_id: str, d: dt.date):
        return Path(f"data/{source_id.lstrip('@')}/{d.isoformat()}_summary.json")

    def get_threads_path(self, source_id: str, d: dt.date):
        return Path(f"data/{source_id.lstrip('@')}/{d.isoformat()}_threads.json")

    def get_participants_path(self, source_id: str, d: dt.date):
        return Path(f"data/{source_id.lstrip('@')}/{d.isoformat()}_participants.json")


def test_enrich_single_chat_result_sets_checksum_and_artifact_paths(monkeypatch):
    # Prepare fake collection with two messages
    now = dt.datetime.now(dt.timezone.utc)
    src = SourceInfo(id="@testsrc", title="T", url="u", type="channel")
    m1 = Message(
        id=1, date=now, text="a", sender_id=1, reactions=[], comments=[], token_count=2
    )
    m2 = Message(
        id=2,
        date=now.replace(minute=(now.minute + 1) % 60),
        text="b",
        sender_id=2,
        reactions=[],
        comments=[],
        token_count=3,
    )
    coll = MessageCollection(source_info=src, messages=[m1, m2])

    # Create instance without running __init__ to avoid side effects
    svc: FetcherService = object.__new__(FetcherService)
    svc.repository = FakeRepo(coll)
    svc._compute_file_checksum = lambda _: "abc"  # type: ignore[attr-defined]

    result = {"file_path": "", "summary_file_path": None}
    latest_date = "2025-11-03"

    # Create a temp file to satisfy existence check
    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "data.json"
        fp.write_text("{}", encoding="utf-8")
        result["file_path"] = str(fp)

        # Act
        svc._enrich_single_chat_result(result, src.id, latest_date)

        # Assert
        assert result["checksum_sha256"] == "abc"
        assert result["first_message_ts"] == m1.date.isoformat()
        assert result["last_message_ts"] == m2.date.isoformat()
        assert result["estimated_tokens_total"] == 5
    assert result["summary_file_path"].endswith("testsrc/2025-11-03_summary.json")
    assert result["threads_file_path"].endswith("testsrc/2025-11-03_threads.json")
    assert result["participants_file_path"].endswith(
        "testsrc/2025-11-03_participants.json"
    )
