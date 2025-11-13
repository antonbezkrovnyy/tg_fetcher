"""Post-processing utilities to enrich fetch results.

Encapsulates logic for computing checksums, deriving timestamps and token
totals from stored collections, and constructing artifact paths.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from src.repositories.protocols import MessageRepositoryProtocol

logger = logging.getLogger(__name__)


class ResultEnricher:
    """Enrich a single-chat fetch result with metadata and artifact paths."""

    def __init__(self, repository: MessageRepositoryProtocol) -> None:
        """Create a ResultEnricher.

        Args:
            repository: MessageRepository to access stored collections and paths
        """
        self._repo = repository

    def enrich_single_chat_result(
        self,
        result: dict[str, Any],
        source_id: str,
        latest_date: str,
        checksum_fn: Callable[[str | Path | None], Optional[str]],
    ) -> None:
        """Populate checksum, timestamps, token sum, and artifact paths.

        Args:
            result: Mutable result dict to enrich
            source_id: Chat identifier (may start with @)
            latest_date: Date string in ISO format (YYYY-MM-DD)
            checksum_fn: Function that computes sha256 checksum of a file
        """
        try:
            # Derive timestamps and token totals from the stored collection
            if result.get("file_path"):
                p = Path(result["file_path"])
                if p.exists():
                    collection = self._repo.load_collection(
                        source_id, datetime.fromisoformat(latest_date).date()
                    )
                    if collection and collection.messages:
                        result["first_message_ts"] = collection.messages[
                            0
                        ].date.isoformat()
                        result["last_message_ts"] = collection.messages[
                            -1
                        ].date.isoformat()
                        result["estimated_tokens_total"] = sum(
                            (m.token_count or 0) for m in collection.messages
                        )
                    result["checksum_sha256"] = checksum_fn(result.get("file_path"))

            # Artifact paths via repository helpers
            # Convert to str so the result remains JSON-serializable
            dt_obj = datetime.fromisoformat(latest_date).date()
            result["summary_file_path"] = self._repo.get_summary_path(
                source_id, dt_obj
            ).as_posix()
            result["threads_file_path"] = self._repo.get_threads_path(
                source_id, dt_obj
            ).as_posix()
            result["participants_file_path"] = self._repo.get_participants_path(
                source_id, dt_obj
            ).as_posix()
        except Exception:
            logger.warning("Failed to enrich single chat result", exc_info=True)
