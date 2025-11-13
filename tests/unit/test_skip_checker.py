import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from src.services.skip.skip_checker import SkipExistingChecker
from src.utils.checksum import compute_file_checksum


class FakeRepo:
    def __init__(self, output: Path | None, summary: Path | None):
        self._output = output
        self._summary = summary

    def get_output_file_path(self, source_id: str, start_date: date):
        return self._output

    def get_summary_path(self, source_id: str, start_date: date):
        return self._summary


def test_skip_when_output_and_summary_match(tmp_path: Path):
    output = tmp_path / "out.jsonl"
    output.write_text("hello\nworld\n", encoding="utf-8")
    checksum = compute_file_checksum(output)

    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"file_checksum_sha256": checksum}), encoding="utf-8")

    checker = SkipExistingChecker(FakeRepo(output, summary))
    decision = checker.decide("src", date(2025, 11, 1))
    assert decision.should_skip is True
    assert decision.reason == "already_exists_same_checksum"
    assert decision.checksum_expected == checksum
    assert decision.checksum_actual == checksum


def test_do_not_skip_when_summary_missing(tmp_path: Path):
    output = tmp_path / "out.jsonl"
    output.write_text("data", encoding="utf-8")

    checker = SkipExistingChecker(FakeRepo(output, None))
    decision = checker.decide("src", date(2025, 11, 1))
    assert decision.should_skip is False


def test_do_not_skip_when_checksum_mismatch(tmp_path: Path):
    output = tmp_path / "out.jsonl"
    output.write_text("data", encoding="utf-8")
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps({"file_checksum_sha256": "deadbeef"}), encoding="utf-8"
    )

    checker = SkipExistingChecker(FakeRepo(output, summary))
    decision = checker.decide("src", date(2025, 11, 1))
    assert decision.should_skip is False
