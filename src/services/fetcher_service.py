"""Telegram Fetcher Service with Pydantic models and full features.

Main orchestrator for fetching messages from Telegram with reactions,
comments, and progress tracking.
"""

import json
import logging
from datetime import date as _date
from pathlib import Path
from typing import Any, Optional

from src.core.config import FetcherConfig
from src.di.container import Container
from src.observability.metrics_adapter import MetricsAdapter
from src.repositories.protocols import MessageRepositoryProtocol
from src.services.event_publisher import EventPublisherProtocol

# Models are used downstream in use-cases and repositories, not directly here
from src.utils.correlation import ensure_correlation_id

# URL parsing utilities no longer needed here; link handling moved to preprocessor

# Telethon details are encapsulated behind gateways and use-cases


# Use-cases are provisioned via DI container to reduce coupling

logger = logging.getLogger(__name__)


class FetcherService:
    """Main service for fetching Telegram messages with full metadata.

    Coordinates session management, strategy execution, and data persistence.
    """

    def __init__(self, config: FetcherConfig):
        """Initialize fetcher service.

        Args:
            config: Validated FetcherConfig instance
        """
        self.config = config
        # Validate mode-specific requirements early to fail fast on misconfiguration
        try:
            self.config.validate_mode_requirements()
        except Exception:
            logger.error("Invalid configuration for fetch mode", exc_info=True)
            raise
        # Build application container
        container = Container(config=self.config)
        self._container = container

        # Initialize external resources via container (IoC)
        container.initialize_runtime()

        # Optionally reset progress via DI-managed tracker
        if config.progress_reset:
            container.provide_progress_tracker().reset_all()

        logger.info(
            "FetcherService initialized",
            extra={
                "strategy": self.config.fetch_mode,
                "chats_count": len(self.config.telegram_chats),
                "chats": self.config.telegram_chats,
                "force_refetch": self.config.force_refetch,
                "fetch_mode": self.config.fetch_mode,
            },
        )

        # Expose selected dependencies for legacy helpers compatibility
        self.repository: MessageRepositoryProtocol = container.provide_repository()
        self.event_publisher: EventPublisherProtocol = (
            container.provide_event_publisher()
        )
        self.metrics: MetricsAdapter = container.provide_metrics()

        # Use cases via container provisioning (MessageExtractor wired by default)
        self._date_range_use_case = container.provide_fetch_date_range_use_case()
        self._chat_use_case = container.provide_fetch_chat_use_case(
            date_range_use_case=self._date_range_use_case
        )

    def _create_strategy(self, date_str: Optional[str] = None) -> Any:
        """Delegate strategy creation to container's factory."""
        return self._container.provide_strategy(date_str)

    # Skip logic fully handled inside use-cases; no local checks here

    async def run(self) -> None:
        """Run fetcher service for all configured chats."""
        correlation_id = ensure_correlation_id()
        # Create strategy upfront to log its name
        strategy = self._create_strategy(
            self.config.fetch_date.isoformat()
            if (self.config.fetch_mode == "date" and self.config.fetch_date is not None)
            else None
        )

        logger.info(
            "Starting fetcher service run",
            extra={
                "correlation_id": correlation_id,
                "chats_count": len(self.config.telegram_chats),
                "strategy": getattr(strategy, "get_strategy_name", lambda: "unknown")(),
            },
        )

        # Delegate orchestration to FetchRunner to keep facade minimal
        runner = self._container.provide_fetch_runner()
        await runner.run_all(strategy=strategy, correlation_id=correlation_id)

    # Output existence checks are encapsulated within repository-aware use-cases

    # Single-chat enrichment is handled by dedicated components in use-cases

    async def fetch_single_chat(
        self,
        chat_identifier: str,
        date_str: Optional[str] = None,
    ) -> dict[str, Any]:
        """Fetch messages from a single chat (for daemon mode commands).

        Args:
            chat_identifier: Chat username or ID

        Returns:
            Dictionary with fetch results:
                - message_count: Number of messages fetched
                - file_path: Path to saved JSON file
                - source_id: Chat ID/username
                - dates: List of dates processed

        Raises:
            Exception: If fetch fails
        """
        result: dict[str, Any] = {
            "message_count": 0,
            "file_path": "",
            "source_id": chat_identifier,
            "dates": [],
            "checksum_sha256": None,
            "estimated_tokens_total": 0,
            "first_message_ts": None,
            "last_message_ts": None,
            "summary_file_path": None,
            "threads_file_path": None,
            "participants_file_path": None,
        }

        strategy = self._create_strategy(date_str)
        try:
            runner = self._container.provide_fetch_runner()
            fetched = await runner.run_single(
                strategy=strategy,
                chat_identifier=chat_identifier,
                correlation_id=ensure_correlation_id(),
            )
            result["message_count"] = fetched

            logger.info(
                f"Fetch completed for chat {chat_identifier}",
                extra={"fetched": result["message_count"]},
            )
            # Enforce result contract via Pydantic model, then return dict for
            # backward compatibility with existing callers
            try:
                from src.models.results import SingleChatFetchResult

                return SingleChatFetchResult.model_validate(result).model_dump()
            except Exception:
                # If validation unexpectedly fails, fall back to original dict
                logger.debug(
                    "Result validation failed; returning raw dict",
                    exc_info=True,
                )
                return result
        except Exception as e:
            logger.error(
                f"Failed to fetch single chat {chat_identifier}: {e}",
                extra={"chat": chat_identifier},
                exc_info=True,
            )
            raise

    # Chat processing is coordinated by FetchRunner via DI

    # Date range orchestration is delegated to FetchDateRangeUseCase

    # Finalization and persistence are handled within use-cases/orchestrator

    # Iteration over messages moved to DateRangeProcessor inside the use-case

    # Short-message merge is delegated to MessagePreprocessor.maybe_merge_short

    # Saving and progress marking live in repository/progress tracker via the use-case

    # Message extraction is provided by DI via MessageExtractor

    # Link extraction/normalization is handled by MessagePreprocessor

    # Classification, language detection, URL normalization, and token estimation
    # have been moved out of the service into the MessagePreprocessor layer.

    def _compute_file_checksum(self, file_path: str | Path | None) -> Optional[str]:
        """Delegate checksum calculation to shared utility for consistency."""
        try:
            from src.utils.checksum import compute_file_checksum as _compute

            return _compute(file_path)
        except Exception:
            logger.warning("Failed to compute checksum", exc_info=True)
            return None

    # Deprecated compatibility helpers kept for unit tests; new flow is in use-cases
    def _enrich_single_chat_result(
        self, result: dict[str, Any], source_id: str, latest_date: str
    ) -> None:
        """Populate checksum and artifact paths; compute basic summary fields.

        This helper mirrors previous behavior for unit tests. In production,
        finalization is handled by the orchestrator and use-cases.
        """
        try:
            # Compute checksum for saved file (if any)
            result["checksum_sha256"] = self._compute_file_checksum(
                result.get("file_path")
            )

            # Derive artifact paths
            d = _date.fromisoformat(latest_date)
            result["summary_file_path"] = self.repository.get_summary_path(
                source_id, d
            ).as_posix()
            result["threads_file_path"] = self.repository.get_threads_path(
                source_id, d
            ).as_posix()
            result["participants_file_path"] = self.repository.get_participants_path(
                source_id, d
            ).as_posix()

            # Load collection to compute timestamps and token totals
            coll = self.repository.load_collection(source_id, d)
            msgs = getattr(coll, "messages", [])
            if msgs:
                result["first_message_ts"] = msgs[0].date.isoformat()
                result["last_message_ts"] = msgs[-1].date.isoformat()
                result["estimated_tokens_total"] = sum(
                    (m.token_count or 0) for m in msgs
                )
            else:
                result.setdefault("first_message_ts", None)
                result.setdefault("last_message_ts", None)
                result.setdefault("estimated_tokens_total", 0)
        except Exception:
            logger.debug("_enrich_single_chat_result failed (non-fatal)", exc_info=True)

    def _maybe_skip_existing(  # noqa: C901
        self, source_info: Any, start_date: _date, *, correlation_id: str
    ) -> bool:
        """Return True if output exists with matching checksum and emit events.

        Emits fetch_skipped event and resets progress gauge when skipping.
        """
        try:
            out_path = self.repository.get_output_file_path(source_info.id, start_date)
            if not Path(out_path).exists():
                return False

            summary_path = self.repository.get_summary_path(source_info.id, start_date)
            if not Path(summary_path).exists():
                return False

            expected_checksum: Optional[str] = None
            try:
                with open(summary_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                expected_checksum = payload.get("file_checksum_sha256")
            except Exception:
                expected_checksum = None

            if not expected_checksum:
                return False

            actual_checksum = self._compute_file_checksum(out_path)
            if actual_checksum and actual_checksum == expected_checksum:
                # Report skip via events/metrics
                if getattr(self.config, "enable_progress_events", False):
                    try:
                        self.event_publisher.publish_fetch_skipped(
                            chat=source_info.id,
                            date=start_date.isoformat(),
                            reason="already_exists_same_checksum",
                            checksum_expected=expected_checksum,
                            checksum_actual=actual_checksum,
                        )
                    except Exception:
                        logger.debug(
                            "Failed to publish fetch_skipped (non-fatal)",
                            extra={"correlation_id": correlation_id},
                            exc_info=True,
                        )
                try:
                    self.metrics.reset_progress(source_info.id, start_date.isoformat())
                except Exception:
                    logger.debug("Failed to reset progress (non-fatal)", exc_info=True)
                return True

            return False
        except Exception:
            logger.debug(
                "_maybe_skip_existing failed (treat as not skipped)", exc_info=True
            )
            return False
