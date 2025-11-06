"""
Unified session management for Telegram clients.
Handles session paths, naming, and client creation consistently.
"""

import os
from pathlib import Path
from typing import Union

from telethon import TelegramClient

from config import FetcherConfig


class SessionManager:
    """Manages Telegram session files and client creation."""

    def __init__(self, config: FetcherConfig):
        self.config = config
        self.session_dir = config.session_dir
        self.session_name = config.session_name

        # Ensure session directory exists
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def get_session_path(self) -> Path:
        """Get full path to session file."""
        return self.session_dir / self.session_name

    def create_client(self) -> TelegramClient:
        """Create configured Telegram client."""
        session_path = str(self.get_session_path())

        return TelegramClient(session_path, self.config.api_id, self.config.api_hash)

    def session_exists(self) -> bool:
        """Check if session file exists."""
        session_file = self.get_session_path().with_suffix(".session")
        return session_file.exists()

    def delete_session(self):
        """Delete session file (for cleanup/reset)."""
        session_file = self.get_session_path().with_suffix(".session")
        if session_file.exists():
            session_file.unlink()

    def get_session_info(self) -> dict:
        """Get information about current session."""
        session_file = self.get_session_path().with_suffix(".session")

        info = {
            "session_path": str(self.get_session_path()),
            "session_file": str(session_file),
            "exists": session_file.exists(),
            "session_dir": str(self.session_dir),
            "session_name": self.session_name,
        }

        if info["exists"]:
            stat = session_file.stat()
            info.update(
                {
                    "size_bytes": stat.st_size,
                    "modified_time": stat.st_mtime,
                    "created_time": stat.st_ctime,
                }
            )

        return info


# Legacy support functions for backward compatibility
def get_legacy_session_path() -> str:
    """Get session path in legacy format for old code."""
    # Default to /sessions/session_digest for backward compatibility
    return "/sessions/session_digest"


def create_client_legacy(
    api_id: int, api_hash: str, session_path: str = None
) -> TelegramClient:
    """Create client using legacy parameters."""
    if session_path is None:
        session_path = get_legacy_session_path()

    return TelegramClient(session_path, api_id, api_hash)
