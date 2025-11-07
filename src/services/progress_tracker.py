"""Progress tracking for Telegram message fetching.

Manages progress.json file to track completed fetches and avoid re-fetching.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SourceProgress(BaseModel):
    """Progress information for a single source.

    Attributes:
        last_processed_date: Last date successfully processed
        last_message_id: ID of last message fetched
        last_updated: Timestamp of last update
        status: Current status (completed, in_progress, failed)
        message_count: Total messages fetched for this source
    """

    last_processed_date: Optional[str] = None
    last_message_id: Optional[int] = None
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: str = "completed"  # completed, in_progress, failed
    message_count: int = 0


class Progress(BaseModel):
    """Progress tracking for all sources.

    Attributes:
        version: Schema version
        sources: Dictionary mapping source name to progress info
    """

    version: str = "1.0"
    sources: dict[str, SourceProgress] = Field(default_factory=dict)


class ProgressTracker:
    """Tracks fetch progress to avoid re-processing completed dates.

    Uses progress.json file to persist state between runs.
    """

    def __init__(self, progress_file: Path):
        """Initialize progress tracker.

        Args:
            progress_file: Path to progress.json file
        """
        self.progress_file = Path(progress_file)
        self.progress: Progress = self._load()
        logger.info(
            f"ProgressTracker initialized with {len(self.progress.sources)} sources",
            extra={"progress_file": str(self.progress_file)},
        )

    def _load(self) -> Progress:
        """Load progress from file.

        Returns:
            Progress object (empty if file doesn't exist)
        """
        if not self.progress_file.exists():
            logger.info("No existing progress file, starting fresh")
            return Progress()

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            progress = Progress(**data)
            logger.info(
                f"Loaded progress for {len(progress.sources)} sources",
                extra={"sources": list(progress.sources.keys())},
            )
            return progress
        except Exception as e:
            logger.error(f"Failed to load progress file: {e}, starting fresh")
            return Progress()

    def _save(self) -> None:
        """Save progress to file atomically."""
        try:
            # Atomic write: temp file then rename
            temp_path = self.progress_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(
                    self.progress.model_dump(mode="json"),
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            temp_path.replace(self.progress_file)
            logger.debug(f"Progress saved to {self.progress_file}")
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
            raise

    def is_date_completed(self, source: str, target_date: date) -> bool:
        """Check if date was already successfully processed for source.

        Args:
            source: Source identifier (e.g., @ru_python)
            target_date: Date to check

        Returns:
            True if date was already completed
        """
        if source not in self.progress.sources:
            return False

        source_progress = self.progress.sources[source]
        if source_progress.status != "completed":
            return False

        if not source_progress.last_processed_date:
            return False

        try:
            last_date = date.fromisoformat(source_progress.last_processed_date)
            return target_date <= last_date
        except ValueError:
            logger.warning(f"Invalid date format in progress for {source}")
            return False

    def mark_completed(
        self, source: str, target_date: date, message_count: int, last_message_id: Optional[int] = None
    ) -> None:
        """Mark date as completed for source.

        Args:
            source: Source identifier
            target_date: Date that was processed
            message_count: Number of messages fetched
            last_message_id: ID of last message (optional)
        """
        source_progress = SourceProgress(
            last_processed_date=target_date.isoformat(),
            last_message_id=last_message_id,
            last_updated=datetime.utcnow().isoformat(),
            status="completed",
            message_count=message_count,
        )

        self.progress.sources[source] = source_progress
        self._save()

        logger.info(
            f"Marked {source} for {target_date} as completed",
            extra={
                "source": source,
                "date": target_date.isoformat(),
                "message_count": message_count,
            },
        )

    def mark_in_progress(self, source: str, target_date: date) -> None:
        """Mark date as in progress for source.

        Args:
            source: Source identifier
            target_date: Date being processed
        """
        if source in self.progress.sources:
            self.progress.sources[source].status = "in_progress"
        else:
            self.progress.sources[source] = SourceProgress(
                last_processed_date=target_date.isoformat(),
                status="in_progress",
            )
        self._save()

    def mark_failed(self, source: str, target_date: date, error: str) -> None:
        """Mark date as failed for source.

        Args:
            source: Source identifier
            target_date: Date that failed
            error: Error message
        """
        if source in self.progress.sources:
            self.progress.sources[source].status = "failed"
        else:
            self.progress.sources[source] = SourceProgress(
                last_processed_date=target_date.isoformat(), status="failed"
            )
        self._save()

        logger.warning(
            f"Marked {source} for {target_date} as failed",
            extra={"source": source, "date": target_date.isoformat(), "error": error},
        )

    def reset_all(self) -> None:
        """Reset all progress (PROGRESS_RESET=true)."""
        self.progress = Progress()
        self._save()
        logger.warning("All progress has been reset")

    def reset_source(self, source: str) -> None:
        """Reset progress for specific source.

        Args:
            source: Source identifier to reset
        """
        if source in self.progress.sources:
            del self.progress.sources[source]
            self._save()
            logger.warning(f"Progress reset for source: {source}")

    def get_source_progress(self, source: str) -> Optional[SourceProgress]:
        """Get progress for specific source.

        Args:
            source: Source identifier

        Returns:
            SourceProgress or None if not found
        """
        return self.progress.sources.get(source)
