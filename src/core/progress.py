"""Progress tracking for idempotent fetch operations.

This module provides thread-safe progress tracking to ensure
idempotent fetch operations across restarts and failures.
"""

import json
import threading
from datetime import date as Date
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class CommandProgress(BaseModel):
    """Progress record for a single fetch command."""

    command_id: str = Field(..., description="Unique command identifier")
    chat: str = Field(..., description="Chat identifier")
    mode: str = Field(..., description="Fetch mode (date/days/range)")
    params: dict[str, Any] = Field(
        default_factory=dict, description="Command parameters"
    )
    status: str = Field(
        default="pending",
        description="Status: pending, in_progress, completed, failed",
    )
    processed_dates: list[str] = Field(
        default_factory=list, description="ISO dates successfully processed"
    )
    output_files: list[str] = Field(
        default_factory=list, description="Generated file paths"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: Optional[str] = Field(
        default=None, description="Start timestamp (ISO format)"
    )
    completed_at: Optional[str] = Field(
        default=None, description="Completion timestamp (ISO format)"
    )


class ProgressTracker:
    """Thread-safe progress tracker for fetch operations.

    Maintains persistent state in JSON file to enable idempotent
    operations and safe recovery after restarts.

    Thread-safety is provided via threading.Lock for concurrent access.
    """

    def __init__(self, progress_file: Path | str):
        """Initialize progress tracker.

        Args:
            progress_file: Path to progress JSON file (Path or str)
        """
        self.progress_file = Path(progress_file) if isinstance(progress_file, str) else progress_file
        self._lock = threading.Lock()
        self._data: dict[str, CommandProgress] = {}
        self._load()

    def _load(self) -> None:
        """Load progress from disk."""
        if not self.progress_file.exists():
            return

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._data = {
                    cmd_id: CommandProgress(**progress)
                    for cmd_id, progress in data.items()
                }
        except (json.JSONDecodeError, ValueError) as e:
            # Corrupted file - backup and start fresh
            backup = self.progress_file.with_suffix(".json.backup")
            if self.progress_file.exists():
                self.progress_file.rename(backup)
            self._data = {}

    def _save(self) -> None:
        """Persist progress to disk (caller must hold lock)."""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)

        data = {cmd_id: progress.model_dump() for cmd_id, progress in self._data.items()}

        # Atomic write with temp file
        temp_file = self.progress_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        temp_file.replace(self.progress_file)

    def start_command(
        self, command_id: str, chat: str, mode: str, params: dict[str, Any]
    ) -> None:
        """Mark command as started.

        Args:
            command_id: Unique command ID
            chat: Chat identifier
            mode: Fetch mode
            params: Command parameters
        """
        with self._lock:
            self._data[command_id] = CommandProgress(
                command_id=command_id,
                chat=chat,
                mode=mode,
                params=params,
                status="in_progress",
                started_at=datetime.utcnow().isoformat(),
            )
            self._save()

    def mark_date_processed(
        self, command_id: str, target_date: Date, output_file: str
    ) -> None:
        """Mark specific date as successfully processed.

        Args:
            command_id: Command ID
            target_date: Processed date
            output_file: Generated output file path
        """
        with self._lock:
            if command_id not in self._data:
                return

            progress = self._data[command_id]
            date_str = target_date.isoformat()

            if date_str not in progress.processed_dates:
                progress.processed_dates.append(date_str)

            if output_file not in progress.output_files:
                progress.output_files.append(output_file)

            self._save()

    def complete_command(self, command_id: str) -> None:
        """Mark command as completed.

        Args:
            command_id: Command ID
        """
        with self._lock:
            if command_id not in self._data:
                return

            self._data[command_id].status = "completed"
            self._data[command_id].completed_at = datetime.utcnow().isoformat()
            self._save()

    def fail_command(self, command_id: str, error: str) -> None:
        """Mark command as failed with error message.

        Args:
            command_id: Command ID
            error: Error message
        """
        with self._lock:
            if command_id not in self._data:
                return

            self._data[command_id].status = "failed"
            self._data[command_id].error = error
            self._data[command_id].completed_at = datetime.utcnow().isoformat()
            self._save()

    def is_date_processed(
        self, command_id: str, target_date: Date, force: bool = False
    ) -> bool:
        """Check if date was already processed for this command.

        Args:
            command_id: Command ID
            target_date: Date to check
            force: If True, always return False (force re-fetch)

        Returns:
            True if date was processed and not forcing re-fetch
        """
        if force:
            return False

        with self._lock:
            if command_id not in self._data:
                return False

            date_str = target_date.isoformat()
            return date_str in self._data[command_id].processed_dates

    def get_command_progress(self, command_id: str) -> Optional[CommandProgress]:
        """Get progress for specific command.

        Args:
            command_id: Command ID

        Returns:
            CommandProgress if exists, None otherwise
        """
        with self._lock:
            return self._data.get(command_id)

    def get_all_progress(self) -> dict[str, CommandProgress]:
        """Get all progress records.

        Returns:
            Dictionary mapping command_id to CommandProgress
        """
        with self._lock:
            return dict(self._data)

    def reset_all(self) -> None:
        """Reset all progress (WARNING: deletes all tracking data)."""
        with self._lock:
            self._data.clear()
            self._save()

    def reset_command(self, command_id: str) -> None:
        """Reset specific command progress.

        Args:
            command_id: Command ID to reset
        """
        with self._lock:
            if command_id in self._data:
                del self._data[command_id]
                self._save()
