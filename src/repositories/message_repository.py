"""Message repository for file-based storage using Pydantic models.

Handles reading/writing MessageCollection objects to JSON files with
atomic operations and versioned schema support.
"""

import json
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from src.models.schemas import Message, MessageCollection, SourceInfo

logger = logging.getLogger(__name__)


class MessageRepository:
    """Repository for storing and retrieving messages from JSON files.

    Uses Pydantic models for automatic validation and serialization.
    File structure: {data_dir}/{source_name}/{YYYY-MM-DD}.json
    """

    def __init__(self, data_dir: Path, *, schema_version: str = "1.0"):
        """Initialize repository with data directory.

        Args:
            data_dir: Root directory for message storage
            schema_version: Version string to record in saved MessageCollection
                artifacts for downstream compatibility checks
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._schema_version = schema_version
        logger.info(f"MessageRepository initialized with data_dir={self.data_dir}")

    def _get_file_path(self, source_name: str, target_date: date) -> Path:
        """Get file path for source and date.

        Args:
            source_name: Source identifier (channel/chat name)
            target_date: Date for messages

        Returns:
            Path to JSON file
        """
        # Remove @ prefix if present for directory name
        clean_source = source_name.lstrip("@")
        source_dir = self.data_dir / clean_source
        source_dir.mkdir(parents=True, exist_ok=True)

        # Format: YYYY-MM-DD.json
        filename = f"{target_date.isoformat()}.json"
        return source_dir / filename

    # Public accessors for artifact paths (used by services for idempotent checks)
    def get_output_file_path(self, source_name: str, target_date: date) -> Path:
        """Return path to the primary JSON file for a chat/date.

        Note: The file may not exist yet; callers should check .exists().
        """
        return self._get_file_path(source_name, target_date)

    def get_summary_path(self, source_name: str, target_date: date) -> Path:
        """Return path for the summary artifact for a chat/date."""
        return self._get_artifact_path(source_name, target_date, "summary")

    def get_threads_path(self, source_name: str, target_date: date) -> Path:
        """Return path for the threads artifact for a chat/date."""
        return self._get_artifact_path(source_name, target_date, "threads")

    def get_participants_path(self, source_name: str, target_date: date) -> Path:
        """Return path for the participants artifact for a chat/date."""
        return self._get_artifact_path(source_name, target_date, "participants")

    def save_collection(
        self, source_name: str, target_date: date, collection: MessageCollection
    ) -> str:
        """Save message collection to JSON file atomically.

        Args:
            source_name: Source identifier
            target_date: Date for messages
            collection: MessageCollection to save
        """
        file_path = self._get_file_path(source_name, target_date)

        # Use Pydantic's model_dump with JSON-compatible types
        data = collection.model_dump(mode="json")

        # Atomic write: write to temp file, then rename
        temp_path = file_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Atomic rename
            temp_path.replace(file_path)

            logger.info(
                f"Saved {len(collection.messages)} messages to {file_path}",
                extra={
                    "source": source_name,
                    "date": target_date.isoformat(),
                    "message_count": len(collection.messages),
                    "file_path": str(file_path),
                },
            )
            return str(file_path)
        except Exception as e:
            logger.error(
                f"Failed to save messages to {file_path}: {e}",
                extra={"source": source_name, "date": target_date.isoformat()},
            )
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise

    def load_collection(
        self, source_name: str, target_date: date
    ) -> Optional[MessageCollection]:
        """Load message collection from JSON file.

        Args:
            source_name: Source identifier
            target_date: Date for messages

        Returns:
            MessageCollection if file exists, None otherwise
        """
        file_path = self._get_file_path(source_name, target_date)

        if not file_path.exists():
            logger.debug(f"File not found: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Use Pydantic validation
            collection = MessageCollection.model_validate(data)

            logger.info(
                f"Loaded {len(collection.messages)} messages from {file_path}",
                extra={
                    "source": source_name,
                    "date": target_date.isoformat(),
                    "message_count": len(collection.messages),
                },
            )
            return collection

        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in {file_path}: {e}",
                extra={"source": source_name, "date": target_date.isoformat()},
            )
            return None
        except Exception as e:
            logger.error(
                f"Failed to load messages from {file_path}: {e}",
                extra={"source": source_name, "date": target_date.isoformat()},
            )
            return None

    def file_exists(self, source_name: str, target_date: date) -> bool:
        """Check if file exists for source and date.

        Args:
            source_name: Source identifier
            target_date: Date to check

        Returns:
            True if file exists, False otherwise
        """
        file_path = self._get_file_path(source_name, target_date)
        return file_path.exists()

    def create_collection(
        self, source_info: SourceInfo, messages: Optional[list[Message]] = None
    ) -> MessageCollection:
        """Create new message collection with schema version.

        Args:
            source_info: Source metadata
            messages: Optional list of messages

        Returns:
            New MessageCollection instance
        """
        return MessageCollection(
            version=self._schema_version,
            source_info=source_info,
            senders={},
            messages=messages or [],
        )

    def append_messages(
        self, source_name: str, target_date: date, new_messages: list[Message]
    ) -> MessageCollection:
        """Append messages to existing collection or create new one.

        Args:
            source_name: Source identifier
            target_date: Date for messages
            new_messages: Messages to append

        Returns:
            Updated MessageCollection

        Raises:
            ValueError: If source_info is needed but not available
        """
        collection = self.load_collection(source_name, target_date)

        if collection is None:
            raise ValueError(
                f"Cannot append to non-existent collection for {source_name} "
                f"on {target_date}. Use save_collection with full data."
            )

        # Append messages (Pydantic validates on assignment)
        collection.messages.extend(new_messages)

        # Save updated collection
        self.save_collection(source_name, target_date, collection)

        return collection

    def get_message_count(self, source_name: str, target_date: date) -> int:
        """Get count of messages for source and date.

        Args:
            source_name: Source identifier
            target_date: Date to check

        Returns:
            Number of messages, 0 if file doesn't exist
        """
        collection = self.load_collection(source_name, target_date)
        return len(collection.messages) if collection else 0

    # New helpers for additional artifacts
    def _get_artifact_path(
        self, source_name: str, target_date: date, suffix: str
    ) -> Path:
        clean_source = source_name.lstrip("@")
        source_dir = self.data_dir / clean_source
        source_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{target_date.isoformat()}_{suffix}.json"
        return source_dir / filename

    def save_summary(self, source_name: str, target_date: date, summary: dict) -> str:
        """Persist a per-day summary artifact.

        Args:
            source_name: Chat/channel identifier
            target_date: Date of messages
            summary: Summary payload (checksum, counts, timestamps)

        Returns:
            Path string to written summary file
        """
        path = self._get_artifact_path(source_name, target_date, "summary")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        logger.info(
            f"Saved summary to {path}",
            extra={
                "source": source_name,
                "date": target_date.isoformat(),
                "file_path": str(path),
            },
        )
        return str(path)

    def save_threads(self, source_name: str, target_date: date, threads: dict) -> str:
        """Persist thread mapping artifact (reply structure) for the day.

        Args:
            source_name: Chat/channel identifier
            target_date: Date of messages
            threads: Mapping data (roots, parent_to_children, depth)

        Returns:
            Path string to written threads file
        """
        path = self._get_artifact_path(source_name, target_date, "threads")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(threads, f, ensure_ascii=False, indent=2)
        logger.info(
            f"Saved threads to {path}",
            extra={
                "source": source_name,
                "date": target_date.isoformat(),
                "file_path": str(path),
            },
        )
        return str(path)

    def save_participants(
        self, source_name: str, target_date: date, participants: dict[str, str]
    ) -> str:
        """Persist participants artifact for the day.

        Args:
            source_name: Chat/channel identifier
            target_date: Date of messages
            participants: Mapping sender_id -> display name

        Returns:
            Path string to written participants file
        """
        path = self._get_artifact_path(source_name, target_date, "participants")
        artifact = {
            "chat": source_name,
            "date": target_date.isoformat(),
            "participants": participants,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2)
        logger.info(
            f"Saved participants to {path}",
            extra={
                "source": source_name,
                "date": target_date.isoformat(),
                "file_path": str(path),
            },
        )
        return str(path)
