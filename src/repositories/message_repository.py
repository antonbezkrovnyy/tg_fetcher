"""Message repository for JSON file operations."""
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.observability.logging_config import get_logger


logger = get_logger(__name__)


class MessageRepository:
    """Repository for storing and retrieving messages in JSON format.
    
    Handles versioned schema and file operations.
    """
    
    SCHEMA_VERSION = "1.0"
    
    def __init__(self, data_dir: Path):
        """Initialize MessageRepository.
        
        Args:
            data_dir: Base directory for data storage
        """
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, source_name: str, target_date: date) -> Path:
        """Get file path for a specific source and date.
        
        Args:
            source_name: Name/username of the source (channel/chat)
            target_date: Date for the data
            
        Returns:
            Path to the JSON file
        """
        # Clean source name for filesystem
        clean_name = source_name.replace("@", "").replace("/", "_")
        source_dir = self.data_dir / clean_name
        source_dir.mkdir(parents=True, exist_ok=True)
        
        return source_dir / f"{target_date.isoformat()}.json"
    
    def save_messages(
        self,
        source_name: str,
        target_date: date,
        source_info: Dict[str, Any],
        messages: List[Dict[str, Any]],
        senders: Dict[str, str],
    ) -> Path:
        """Save messages to JSON file with versioned schema.
        
        Args:
            source_name: Name/username of the source
            target_date: Date for the messages
            source_info: Information about the source (id, title, url)
            messages: List of message dictionaries
            senders: Mapping of sender_id to display name
            
        Returns:
            Path to the saved file
        """
        file_path = self._get_file_path(source_name, target_date)
        
        data = {
            "version": self.SCHEMA_VERSION,
            "source_info": source_info,
            "senders": senders,
            "messages": messages,
        }
        
        # Atomic write: write to temp file, then rename
        temp_path = file_path.with_suffix(".tmp")
        
        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Atomic rename
            temp_path.replace(file_path)
            
            logger.info(
                "Saved messages to file",
                extra={
                    "source": source_name,
                    "date": target_date.isoformat(),
                    "message_count": len(messages),
                    "file": str(file_path),
                },
            )
            
            return file_path
            
        except Exception as e:
            logger.error(
                "Failed to save messages",
                extra={
                    "source": source_name,
                    "date": target_date.isoformat(),
                    "error": str(e),
                },
            )
            # Clean up temp file
            if temp_path.exists():
                temp_path.unlink()
            raise
    
    def load_messages(
        self, source_name: str, target_date: date
    ) -> Optional[Dict[str, Any]]:
        """Load messages from JSON file.
        
        Args:
            source_name: Name/username of the source
            target_date: Date for the messages
            
        Returns:
            Dictionary with version, source_info, messages, senders or None if not found
        """
        file_path = self._get_file_path(source_name, target_date)
        
        if not file_path.exists():
            logger.debug(
                "Messages file not found",
                extra={"source": source_name, "date": target_date.isoformat()},
            )
            return None
        
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            logger.debug(
                "Loaded messages from file",
                extra={
                    "source": source_name,
                    "date": target_date.isoformat(),
                    "message_count": len(data.get("messages", [])),
                },
            )
            
            return data
            
        except Exception as e:
            logger.error(
                "Failed to load messages",
                extra={
                    "source": source_name,
                    "date": target_date.isoformat(),
                    "error": str(e),
                },
            )
            raise
    
    def file_exists(self, source_name: str, target_date: date) -> bool:
        """Check if messages file exists for given source and date.
        
        Args:
            source_name: Name/username of the source
            target_date: Date to check
            
        Returns:
            True if file exists, False otherwise
        """
        file_path = self._get_file_path(source_name, target_date)
        return file_path.exists()
