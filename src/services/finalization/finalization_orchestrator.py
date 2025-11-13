"""Finalization Orchestrator.

Handles postprocess stage, artifact generation, and completion event
publishing to keep FetcherService slim and focused.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from src.models.schemas import MessageCollection, SourceInfo
from src.services.postprocess.finalizer import ResultFinalizer
from src.services.progress.progress_service import ProgressService


class FinalizationOrchestrator:
    """Coordinates finalization steps for a completed date range."""

    def __init__(
        self,
        *,
        finalizer: ResultFinalizer,
        progress_service: ProgressService,
        schema_version: str = "1.0",
        preprocessing_version: str = "1",
    ) -> None:
        """Initialize orchestrator with collaborators.

        Args:
            finalizer: Artifact persistence component
            progress_service: Progress/events facade
            schema_version: Version string recorded in summary artifacts to
                denote the message data schema version
            preprocessing_version: Version string for preprocessing pipeline
                used to produce summary/calculated fields
        """
        self._finalizer = finalizer
        self._progress = progress_service
        self._schema_version = schema_version
        self._preproc_version = preprocessing_version

    def _build_threads(self, collection: MessageCollection) -> dict[str, Any]:
        parent_to_children: dict[str, list[int]] = {}
        roots: list[int] = []
        depth: dict[str, int] = {}
        id_to_parent: dict[int, Optional[int]] = {}
        for m in collection.messages:
            if m.reply_to_msg_id:
                id_to_parent[m.id] = m.reply_to_msg_id
                parent_to_children.setdefault(str(m.reply_to_msg_id), []).append(m.id)
            else:
                id_to_parent[m.id] = None
                roots.append(m.id)

        def calc_depth(mid: int) -> int:
            d = 0
            cur = id_to_parent.get(mid)
            while cur:
                d += 1
                cur = id_to_parent.get(cur)
            return d

        for m in collection.messages:
            depth[str(m.id)] = calc_depth(m.id)
        return {
            "roots": roots,
            "parent_to_children": parent_to_children,
            "depth": depth,
        }

    def finalize(
        self,
        *,
        source_info: SourceInfo,
        start_date: date,
        collection: MessageCollection,
        messages_fetched: int,
        duration: float,
        file_path: Optional[str],
        checksum_fn: Callable[[str | Path | None], Optional[str]],
    ) -> None:
        """Run postprocess, save artifacts, and publish completion event."""
        first_ts_dt = (
            collection.messages[0].date if collection.messages else None
        )
        last_ts_dt = (
            collection.messages[-1].date if collection.messages else None
        )
        first_ts = first_ts_dt.isoformat() if first_ts_dt else None
        last_ts = last_ts_dt.isoformat() if last_ts_dt else None
        checksum = checksum_fn(file_path) if file_path else None
        estimated_tokens_total = sum([m.token_count or 0 for m in collection.messages])

        # Stage: postprocess
        self._progress.publish_stage(
            chat=source_info.id,
            date=start_date.isoformat(),
            stage="postprocess",
        )

        # Save artifacts
        self._finalizer.save_artifacts(
            source_id=source_info.id,
            target_date=start_date,
            summary={
                "chat": source_info.id,
                "date": start_date.isoformat(),
                "schema_version": self._schema_version,
                "preprocessing_version": self._preproc_version,
                "timezone": "UTC",
                "first_message_ts": first_ts,
                "last_message_ts": last_ts,
                "message_count": messages_fetched,
                "estimated_tokens_total": estimated_tokens_total,
                "file_checksum_sha256": checksum,
            },
            threads=self._build_threads(collection),
            participants=collection.senders,
        )

        # Observe freshness lag if possible
        try:
            from os import getenv
            from src.observability.metrics import fetch_lag_seconds

            worker = getenv("HOSTNAME", "fetcher-1")
            if last_ts_dt is not None:
                now_utc = datetime.now(tz=timezone.utc)
                lag = max(0.0, (now_utc - last_ts_dt).total_seconds())
                fetch_lag_seconds.labels(
                    chat=source_info.id, date=start_date.isoformat(), worker=worker
                ).observe(lag)
        except Exception:
            pass

        # Publish completion
        self._progress.publish_complete(
            chat=source_info.id,
            date=start_date.isoformat(),
            message_count=messages_fetched,
            file_path=str(file_path) if file_path else "",
            duration_seconds=duration,
        )
