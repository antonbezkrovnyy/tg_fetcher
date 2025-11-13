from datetime import date, datetime, timezone
from pathlib import Path

from src.models.schemas import Message, MessageCollection, SourceInfo
from src.services.postprocess.result_enricher import ResultEnricher


class RepoPathsStub:
    def __init__(self, collection=None, raise_on_load=False):
        self._collection = collection
        self._raise = raise_on_load

    def load_collection(self, source_id, dt):  # noqa: ANN001
        if self._raise:
            raise RuntimeError("load boom")
        return self._collection

    def get_summary_path(self, source_id, dt):  # noqa: ANN001
        return Path(f"/data/{source_id}/{dt.isoformat()}/summary.json")

    def get_threads_path(self, source_id, dt):  # noqa: ANN001
        return Path(f"/data/{source_id}/{dt.isoformat()}/threads.json")

    def get_participants_path(self, source_id, dt):  # noqa: ANN001
        return Path(f"/data/{source_id}/{dt.isoformat()}/participants.json")


def _collection_with_messages():
    ts = datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc)
    msgs = [
        Message(id=1, date=ts, text="a", sender_id=10, reply_to_msg_id=None, reactions=[], comments=[], token_count=5),
        Message(id=2, date=ts, text="b", sender_id=20, reply_to_msg_id=1, reactions=[], comments=[], token_count=3),
    ]
    return MessageCollection(
        source_info=SourceInfo(id="@c", title="t", url="u", type="channel"),
        senders={"10": "Alice", "20": "Bob"},
        messages=msgs,
    )


def test_enricher_with_existing_file_sets_fields(tmp_path):
    coll = _collection_with_messages()
    repo = RepoPathsStub(collection=coll)
    enricher = ResultEnricher(repository=repo)

    # Create real file so Path.exists() is True
    p = tmp_path / "2025-01-02.json"
    p.write_text("{}", encoding="utf-8")

    result = {"file_path": str(p)}

    def checksum_fn(path):  # noqa: ANN001
        assert Path(path) == p
        return "sha256-abc"

    enricher.enrich_single_chat_result(
        result,
        source_id="@c",
        latest_date="2025-01-02",
        checksum_fn=checksum_fn,
    )

    assert result["first_message_ts"].startswith("2025-01-02T")
    assert result["last_message_ts"].startswith("2025-01-02T")
    assert result["estimated_tokens_total"] == 8
    assert result["checksum_sha256"] == "sha256-abc"

    # Artifact paths always set
    assert result["summary_file_path"].endswith("summary.json")
    assert result["threads_file_path"].endswith("threads.json")
    assert result["participants_file_path"].endswith("participants.json")


def test_enricher_without_file_sets_only_paths(tmp_path):
    repo = RepoPathsStub(collection=None)
    enricher = ResultEnricher(repository=repo)

    result = {"file_path": str(tmp_path / "missing.json")}

    def checksum_fn(path):  # noqa: ANN001
        raise AssertionError("checksum shouldn't be called when file doesn't exist")

    enricher.enrich_single_chat_result(
        result,
        source_id="@c",
        latest_date="2025-01-02",
        checksum_fn=checksum_fn,
    )

    # No timestamps or checksum when file is absent
    for k in ("first_message_ts", "last_message_ts", "estimated_tokens_total", "checksum_sha256"):
        assert k not in result

    # But artifact paths are set
    assert result["summary_file_path"].endswith("summary.json")
    assert result["threads_file_path"].endswith("threads.json")
    assert result["participants_file_path"].endswith("participants.json")


def test_enricher_swallow_exceptions(tmp_path):
    repo = RepoPathsStub(collection=None, raise_on_load=True)
    enricher = ResultEnricher(repository=repo)

    result = {"file_path": str(tmp_path / "missing.json")}

    def checksum_fn(path):  # noqa: ANN001
        return "x"

    # Should not raise despite repo throwing inside
    enricher.enrich_single_chat_result(
        result,
        source_id="@c",
        latest_date="2025-01-02",
        checksum_fn=checksum_fn,
    )

    # Paths still set even if load_collection errored (path creation doesn't use load)
    assert result["summary_file_path"].endswith("summary.json")
    assert result["threads_file_path"].endswith("threads.json")
    assert result["participants_file_path"].endswith("participants.json")


def test_enricher_existing_file_empty_collection(tmp_path):
    # File exists but repo returns empty collection -> checksum set, no timestamps
    repo = RepoPathsStub(collection=None)
    enricher = ResultEnricher(repository=repo)

    p = tmp_path / "2025-01-02.json"
    p.write_text("{}", encoding="utf-8")

    result = {"file_path": str(p)}

    def checksum_fn(path):  # noqa: ANN001
        return "sha256-empty"

    enricher.enrich_single_chat_result(
        result,
        source_id="@c",
        latest_date="2025-01-02",
        checksum_fn=checksum_fn,
    )

    assert result.get("first_message_ts") is None
    assert result.get("last_message_ts") is None
    assert result.get("estimated_tokens_total") is None
    assert result["checksum_sha256"] == "sha256-empty"
