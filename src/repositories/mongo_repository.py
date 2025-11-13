"""MongoDB repository adapter (optional backend).

This adapter conforms to MessageRepositoryProtocol but requires MongoDB
configuration to be provided. It is not enabled by default. When selected via
config.storage_backend='mongo', ensure pymongo is installed and environment
variables are set.

Note: This is a minimal scaffold to enable DI selection without impacting
existing file-based flows. Full implementation (indexes, queries, upserts)
can be completed when Mongo is provisioned in the environment.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

try:
    from pymongo import MongoClient  # type: ignore
    from pymongo.collection import Collection  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    MongoClient = None  # type: ignore
    Collection = None  # type: ignore

from src.models.schemas import Message, MessageCollection, SourceInfo
from src.repositories.protocols import MessageRepositoryProtocol

logger = logging.getLogger(__name__)


class MongoMessageRepository(MessageRepositoryProtocol):
    """MongoDB-backed repository for message storage.

    Minimal, non-production implementation placeholder. Raises at runtime if
    pymongo is unavailable or config is incomplete.
    """

    def __init__(self, *, url: str | None, db: str | None, collection: str | None):
        self._url = url
        self._db_name = db
        self._coll_name = collection
        self._client: Optional[MongoClient] = None  # type: ignore
        self._coll: Optional[Collection] = None  # type: ignore
        self._ensure_ready()

    def _ensure_ready(self) -> None:
        if MongoClient is None:
            raise RuntimeError(
                "pymongo is not installed. Install pymongo to use Mongo backend."
            )
        if not self._url or not self._db_name or not self._coll_name:
            raise RuntimeError(
                "Mongo backend selected but mongo_url/mongo_db/mongo_collection are not configured"
            )
        self._client = MongoClient(self._url)
        db = self._client[self._db_name]
        self._coll = db[self._coll_name]
        try:
            # Basic indexes; refine as needed
            self._coll.create_index([("chat", 1), ("date", 1)])
            self._coll.create_index([("chat", 1), ("date", 1), ("messages.id", 1)])
        except Exception:
            logger.debug("Index creation failed (non-fatal in scaffold)", exc_info=True)

    # Protocol methods
    def save_collection(
        self, source_name: str, target_date: date, collection: MessageCollection
    ) -> str:
        assert self._coll is not None
        doc = {
            "chat": source_name,
            "date": target_date.isoformat(),
            "version": collection.version,
            "timezone": collection.timezone,
            "source_info": collection.source_info.model_dump(mode="json"),
            "senders": collection.senders,
            "messages": [m.model_dump(mode="json") for m in collection.messages],
        }
        self._coll.update_one(
            {"chat": source_name, "date": target_date.isoformat()},
            {"$set": doc},
            upsert=True,
        )
        # Return a pseudo-path reference for compatibility
        return f"mongo://{self._db_name}/{self._coll_name}/{source_name}/{target_date.isoformat()}"

    def load_collection(
        self, source_name: str, target_date: date
    ) -> Optional[MessageCollection]:
        assert self._coll is not None
        doc = self._coll.find_one({"chat": source_name, "date": target_date.isoformat()})
        if not doc:
            return None
        return MessageCollection.model_validate(
            {
                "version": doc.get("version", "1.0"),
                "timezone": doc.get("timezone", "UTC"),
                "source_info": doc.get("source_info", {}),
                "senders": doc.get("senders", {}),
                "messages": doc.get("messages", []),
            }
        )

    def file_exists(self, source_name: str, target_date: date) -> bool:
        assert self._coll is not None
        return (
            self._coll.count_documents(
                {"chat": source_name, "date": target_date.isoformat()}, limit=1
            )
            > 0
        )

    def create_collection(
        self, source_info: SourceInfo, messages: Optional[list[Message]] = None
    ) -> MessageCollection:
        return MessageCollection(source_info=source_info, messages=messages or [])

    # Artifact path helpers are not applicable for Mongo; return pseudo-paths
    def get_output_file_path(self, source_name: str, target_date: date):  # type: ignore[override]
        return f"mongo://{self._db_name}/{self._coll_name}/{source_name}/{target_date.isoformat()}"

    def get_summary_path(self, source_name: str, target_date: date):  # type: ignore[override]
        return f"mongo://{self._db_name}/{self._coll_name}/{source_name}/{target_date.isoformat()}_summary"

    def get_threads_path(self, source_name: str, target_date: date):  # type: ignore[override]
        return f"mongo://{self._db_name}/{self._coll_name}/{source_name}/{target_date.isoformat()}_threads"

    def get_participants_path(self, source_name: str, target_date: date):  # type: ignore[override]
        return f"mongo://{self._db_name}/{self._coll_name}/{source_name}/{target_date.isoformat()}_participants"

    # Artifact persistence for Mongo is deferred in this scaffold
    def save_summary(self, source_name: str, target_date: date, summary: dict) -> str:
        assert self._coll is not None
        self._coll.update_one(
            {"chat": source_name, "date": target_date.isoformat()},
            {"$set": {"summary": summary}},
            upsert=True,
        )
        return self.get_summary_path(source_name, target_date)

    def save_threads(self, source_name: str, target_date: date, threads: dict) -> str:
        assert self._coll is not None
        self._coll.update_one(
            {"chat": source_name, "date": target_date.isoformat()},
            {"$set": {"threads": threads}},
            upsert=True,
        )
        return self.get_threads_path(source_name, target_date)

    def save_participants(
        self, source_name: str, target_date: date, participants: dict[str, str]
    ) -> str:
        assert self._coll is not None
        self._coll.update_one(
            {"chat": source_name, "date": target_date.isoformat()},
            {"$set": {"participants": participants}},
            upsert=True,
        )
        return self.get_participants_path(source_name, target_date)
