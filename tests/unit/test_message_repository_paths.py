from datetime import date
from pathlib import Path

from src.repositories.message_repository import MessageRepository


def test_artifact_paths_shape(tmp_path):
    repo = MessageRepository(tmp_path)
    source = "@demo"
    d = date(2025, 2, 3)

    out_path = repo.get_output_file_path(source, d)
    assert out_path.name == f"{d.isoformat()}.json"
    # Subdir is source without leading @
    assert out_path.parent.name == source.lstrip("@")

    summary = repo.get_summary_path(source, d).as_posix()
    threads = repo.get_threads_path(source, d).as_posix()
    participants = repo.get_participants_path(source, d).as_posix()

    assert summary.endswith("_summary.json")
    assert threads.endswith("_threads.json")
    assert participants.endswith("_participants.json")
