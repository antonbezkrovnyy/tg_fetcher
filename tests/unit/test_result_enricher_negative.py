import os
from datetime import date
from pathlib import Path

from src.repositories.message_repository import MessageRepository
from src.services.postprocess.result_enricher import ResultEnricher


def _noop_checksum(_):
    return None


def test_enrich_when_file_missing_sets_paths_only(tmp_path):
    repo = MessageRepository(tmp_path)
    enricher = ResultEnricher(repo)

    source_id = "@testchat"
    d = date(2025, 1, 2)
    # Intentionally reference a non-existent file
    missing_path = repo.get_output_file_path(source_id, d).as_posix()

    result = {
        "message_count": 0,
        "file_path": missing_path,
        "source_id": source_id,
        "dates": [d.isoformat()],
        "checksum_sha256": None,
        "estimated_tokens_total": 0,
        "first_message_ts": None,
        "last_message_ts": None,
        "summary_file_path": None,
        "threads_file_path": None,
        "participants_file_path": None,
    }

    enricher.enrich_single_chat_result(result, source_id, d.isoformat(), _noop_checksum)

    # Check that artifact paths are populated even if file is missing
    assert result["summary_file_path"].endswith("_summary.json")
    assert result["threads_file_path"].endswith("_threads.json")
    assert result["participants_file_path"].endswith("_participants.json")

    # And timestamps/checksum remain None
    assert result["first_message_ts"] is None
    assert result["last_message_ts"] is None
    assert result["checksum_sha256"] is None


def test_enrich_handles_repository_exception(tmp_path):
    class BadRepo:
        # Minimal API matching what's used in ResultEnricher
        def load_collection(self, source_id, dt):  # noqa: D401, ANN001
            return None

        def get_summary_path(self, source_id, dt):  # noqa: D401, ANN001
            raise RuntimeError("broken repo")

        def get_threads_path(self, source_id, dt):  # noqa: D401, ANN001
            return Path(tmp_path / "th.json")

        def get_participants_path(self, source_id, dt):  # noqa: D401, ANN001
            return Path(tmp_path / "p.json")

    enricher = ResultEnricher(BadRepo())

    result = {
        "message_count": 0,
        "file_path": None,
        "source_id": "@id",
        "dates": ["2025-01-02"],
        "checksum_sha256": None,
        "estimated_tokens_total": 0,
        "first_message_ts": None,
        "last_message_ts": None,
        "summary_file_path": None,
        "threads_file_path": None,
        "participants_file_path": None,
    }

    # Should swallow exception and not raise
    enricher.enrich_single_chat_result(result, "@id", "2025-01-02", lambda _: None)

    # Since summary computation exploded, artifact paths may remain None
    # The key assertion is that the call did not raise and result dict is still present
    assert "summary_file_path" in result
