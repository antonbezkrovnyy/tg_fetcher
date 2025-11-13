"""Repository protocols (ports) for hexagonal architecture.

These Protocols define the minimal contracts the application layer depends on.
Concrete adapters (e.g., file-based MessageRepository) should satisfy them via
structural subtyping (no inheritance required).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional, Protocol

from src.models.schemas import Message, MessageCollection, SourceInfo


class MessageRepositoryProtocol(Protocol):
    """Port for message persistence and artifact management.

    Implemented by file-based repository adapters or alternative storages.
    """

    # Core collection IO
    def save_collection(
        self, source_name: str, target_date: date, collection: MessageCollection
    ) -> str:  # noqa: D401
        """Save message collection to persistent storage and return path string."""

    def load_collection(
        self, source_name: str, target_date: date
    ) -> Optional[MessageCollection]:  # noqa: D401
        """Load a message collection if present; return None otherwise."""

    def file_exists(self, source_name: str, target_date: date) -> bool:  # noqa: D401
        """Return True if a collection file exists for the given day."""

    def create_collection(
        self, source_info: SourceInfo, messages: Optional[list[Message]] = None
    ) -> MessageCollection:  # noqa: E501
        """Create an empty collection with schema/version metadata."""

    # Primary output file path
    def get_output_file_path(
        self, source_name: str, target_date: date
    ) -> Path:  # noqa: D401
        """Return the canonical path for the day's primary JSON file."""

    # Artifact paths
    def get_summary_path(
        self, source_name: str, target_date: date
    ) -> Path:  # noqa: D401
        """Return path for the summary artifact for the day."""

    def get_threads_path(
        self, source_name: str, target_date: date
    ) -> Path:  # noqa: D401
        """Return path for the threads artifact for the day."""

    def get_participants_path(
        self, source_name: str, target_date: date
    ) -> Path:  # noqa: D401
        """Return path for the participants artifact for the day."""

    # Artifact persistence
    def save_summary(
        self, source_name: str, target_date: date, summary: dict
    ) -> str:  # noqa: D401
        """Persist summary artifact and return written path string."""

    def save_threads(
        self, source_name: str, target_date: date, threads: dict
    ) -> str:  # noqa: D401
        """Persist threads artifact and return written path string."""

    def save_participants(
        self, source_name: str, target_date: date, participants: dict[str, str]
    ) -> str:  # noqa: E501
        """Persist participants artifact and return written path string."""
