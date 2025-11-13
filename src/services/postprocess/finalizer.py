"""Finalization helpers for persisting per-day artifacts.

Encapsulates saving of summary, threads, and participants to reduce
responsibilities of the main FetcherService.
"""

from __future__ import annotations

from datetime import date

from src.repositories.protocols import MessageRepositoryProtocol


class ResultFinalizer:
    """Finalize a day's results by saving artifacts via repository."""

    def __init__(self, repository: MessageRepositoryProtocol):
        """Create finalizer with a repository dependency."""
        self._repo = repository

    def save_artifacts(
        self,
        source_id: str,
        target_date: date,
        *,
        summary: dict,
        threads: dict,
        participants: dict[str, str],
    ) -> dict[str, str]:
        """Save summary, threads, and participants artifacts.

        Returns a mapping with written file paths.
        """
        paths: dict[str, str] = {}
        paths["summary_file_path"] = self._repo.save_summary(
            source_name=source_id, target_date=target_date, summary=summary
        )
        paths["threads_file_path"] = self._repo.save_threads(
            source_name=source_id, target_date=target_date, threads=threads
        )
        paths["participants_file_path"] = self._repo.save_participants(
            source_name=source_id, target_date=target_date, participants=participants
        )
        return paths
