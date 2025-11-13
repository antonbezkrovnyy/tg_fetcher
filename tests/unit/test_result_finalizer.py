from datetime import date

from src.services.postprocess.finalizer import ResultFinalizer


class RepoStub:
    def __init__(self):
        self.calls = []

    def save_summary(self, *, source_name, target_date, summary):  # noqa: ANN001
        self.calls.append(("summary", source_name, target_date, summary))
        return f"/tmp/{source_name}-{target_date}-summary.json"

    def save_threads(self, *, source_name, target_date, threads):  # noqa: ANN001
        self.calls.append(("threads", source_name, target_date, threads))
        return f"/tmp/{source_name}-{target_date}-threads.json"

    def save_participants(self, *, source_name, target_date, participants):  # noqa: ANN001
        self.calls.append(("participants", source_name, target_date, participants))
        return f"/tmp/{source_name}-{target_date}-participants.json"


def test_result_finalizer_delegates_and_returns_paths():
    repo = RepoStub()
    fin = ResultFinalizer(repository=repo)

    out = fin.save_artifacts(
        source_id="@c",
        target_date=date(2025, 1, 2),
        summary={"a": 1},
        threads={"b": 2},
        participants={"10": "A"},
    )

    assert set(out.keys()) == {
        "summary_file_path",
        "threads_file_path",
        "participants_file_path",
    }
    assert out["summary_file_path"].endswith("summary.json")
    assert out["threads_file_path"].endswith("threads.json")
    assert out["participants_file_path"].endswith("participants.json")

    kinds = [k for k, *_ in repo.calls]
    assert kinds == ["summary", "threads", "participants"]
