from datetime import date, datetime, timezone

from src.models.schemas import Message, MessageCollection, SourceInfo
from src.services.finalization.finalization_orchestrator import FinalizationOrchestrator


class StubFinalizer:
    def __init__(self):
        self.calls = []

    def save_artifacts(self, *, source_id, target_date, summary, threads, participants):  # noqa: ANN001
        self.calls.append({
            "source_id": source_id,
            "target_date": target_date,
            "summary": summary,
            "threads": threads,
            "participants": participants,
        })
        return {
            "summary_file_path": f"/tmp/{source_id}-{target_date}-summary.json",
            "threads_file_path": f"/tmp/{source_id}-{target_date}-threads.json",
            "participants_file_path": f"/tmp/{source_id}-{target_date}-participants.json",
        }


class StubProgress:
    def __init__(self):
        self.stages = []
        self.completed = []

    def publish_stage(self, *, chat, date, stage):  # noqa: ANN001
        self.stages.append((chat, date, stage))

    def publish_complete(self, *, chat, date, message_count, file_path, duration_seconds):  # noqa: ANN001
        self.completed.append((chat, date, message_count, file_path, duration_seconds))


def _mc(messages):
    return MessageCollection(
        source_info=SourceInfo(id="@c", title="t", url="u", type="channel"),
        senders={"10": "Alice", "20": "Bob"},
        messages=messages,
    )


def test_finalize_builds_threads_saves_and_publishes():
    # Prepare collection with thread structure: 1 root (id=1), child (id=2 -> reply_to=1)
    ts = datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc)
    messages = [
        Message(id=1, date=ts, text="root", sender_id=10, reply_to_msg_id=None, reactions=[], comments=[], token_count=5),
        Message(id=2, date=ts, text="child", sender_id=20, reply_to_msg_id=1, reactions=[], comments=[], token_count=3),
    ]
    collection = _mc(messages)

    finalizer = StubFinalizer()
    progress = StubProgress()

    orchestrator = FinalizationOrchestrator(
        finalizer=finalizer,
        progress_service=progress,
        schema_version="1.0",
        preprocessing_version="2",
    )

    def checksum_fn(path):  # noqa: ANN001
        assert path == "/data/2025-01-02.json"
        return "sha256-abc"

    orchestrator.finalize(
        source_info=SourceInfo(id="@c", title="T", url="u", type="channel"),
        start_date=date(2025, 1, 2),
        collection=collection,
        messages_fetched=len(messages),
        duration=1.25,
        file_path="/data/2025-01-02.json",
        checksum_fn=checksum_fn,
    )

    # Stage published
    assert progress.stages == [("@c", "2025-01-02", "postprocess")]

    # Artifacts saved with expected summary and threads
    assert len(finalizer.calls) == 1
    call = finalizer.calls[0]
    assert call["source_id"] == "@c"
    assert call["target_date"].isoformat() == "2025-01-02"

    summary = call["summary"]
    assert summary["chat"] == "@c"
    assert summary["date"] == "2025-01-02"
    assert summary["schema_version"] == "1.0"
    assert summary["preprocessing_version"] == "2"
    assert summary["first_message_ts"].startswith("2025-01-02T")
    assert summary["last_message_ts"].startswith("2025-01-02T")
    assert summary["message_count"] == 2
    assert summary["estimated_tokens_total"] == 8
    assert summary["file_checksum_sha256"] == "sha256-abc"

    threads = call["threads"]
    assert threads["roots"] == [1]
    assert threads["parent_to_children"] == {"1": [2]}
    assert threads["depth"]["1"] == 0 and threads["depth"]["2"] == 1

    # Completion event
    assert progress.completed == [("@c", "2025-01-02", 2, "/data/2025-01-02.json", 1.25)]
