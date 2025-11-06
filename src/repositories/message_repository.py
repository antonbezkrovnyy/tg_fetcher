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

    SCHEMA_VERSION = "1.0"

    def __init__(self, data_dir: Path):
        """Initialize repository with data directory.

        Args:
            data_dir: Root directory for message storage
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
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

    def save_collection(
        self, source_name: str, target_date: date, collection: MessageCollection
    ) -> None:
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
            version=self.SCHEMA_VERSION,
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
