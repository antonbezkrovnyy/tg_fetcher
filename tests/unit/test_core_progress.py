from datetime import date
from pathlib import Path

from src.core.progress import ProgressTracker


def test_progress_tracker_lifecycle(tmp_path: Path):
    p = tmp_path / "progress.json"
    tracker = ProgressTracker(p)

    cmd = "cmd-1"
    tracker.start_command(cmd, chat="@chat", mode="date", params={"date": "2025-11-01"})

    # mark processed for two dates
    d1 = date(2025, 11, 1)
    d2 = date(2025, 11, 2)
    tracker.mark_date_processed(cmd, d1, output_file="out1.json")
    tracker.mark_date_processed(cmd, d2, output_file="out2.json")

    assert tracker.is_date_processed(cmd, d1) is True
    assert tracker.is_date_processed(cmd, d2) is True
    # force=true bypasses idempotency
    assert tracker.is_date_processed(cmd, d1, force=True) is False

    tracker.complete_command(cmd)
    prog = tracker.get_command_progress(cmd)
    assert prog is not None and prog.status == "completed"
    assert prog.completed_at is not None

    # fail flow updates error and status
    tracker.fail_command(cmd, error="boom")
    prog = tracker.get_command_progress(cmd)
    assert prog is not None and prog.status == "failed" and prog.error == "boom"

    # reset specific and all
    tracker.reset_command(cmd)
    assert tracker.get_command_progress(cmd) is None

    tracker.start_command(cmd, chat="@chat", mode="date", params={})
    tracker.reset_all()
    assert tracker.get_all_progress() == {}
