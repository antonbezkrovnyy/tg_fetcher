"""Skip decision helpers for idempotent fetches.

This module encapsulates logic to skip work when an output file already exists
with a matching checksum recorded in the summary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Protocol

from src.utils.checksum import compute_file_checksum


class _Repository(Protocol):
    """Minimal repository protocol required for skip decision.

    Only the methods used by the checker are defined here to avoid
    tight coupling with the full repository interface.
    """

    def get_output_file_path(
        self, source_id: str, start_date: date
    ) -> Optional[Path]: ...

    def get_summary_path(self, source_id: str, start_date: date) -> Optional[Path]: ...


@dataclass(frozen=True)
class SkipDecision:
    """Result of a skip decision check.

    Attributes:
        should_skip: True if processing should be skipped
        reason: Optional human-readable reason for the decision
        checksum_expected: Expected checksum from summary (if available)
        checksum_actual: Actual checksum from existing file (if available)
    """

    should_skip: bool
    reason: Optional[str] = None
    checksum_expected: Optional[str] = None
    checksum_actual: Optional[str] = None


class SkipExistingChecker:
    """Encapsulates 'skip if already exists with same checksum' logic."""

    def __init__(self, repository: _Repository) -> None:
        """Create checker with a minimal repository dependency."""
        self._repo = repository

    def decide(self, source_id: str, start_date: date) -> SkipDecision:
        """Decide whether to skip processing for the given (source_id, date).

        The decision is based on presence of output and matching checksum
        stored in the corresponding summary file.
        """
        existing = self._repo.get_output_file_path(source_id, start_date)
        if not existing or not existing.exists():
            return SkipDecision(False)

        summary = self._repo.get_summary_path(source_id, start_date)
        if not summary or not summary.exists():
            return SkipDecision(False)

        try:
            with summary.open("r", encoding="utf-8") as f:
                data = json.load(f)
            expected = data.get("file_checksum_sha256")
        except Exception:
            return SkipDecision(False)

        actual = compute_file_checksum(existing)
        if expected and actual and expected == actual:
            return SkipDecision(
                True,
                reason="already_exists_same_checksum",
                checksum_expected=expected,
                checksum_actual=actual,
            )

        return SkipDecision(False)
