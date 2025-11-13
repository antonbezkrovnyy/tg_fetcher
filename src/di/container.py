"""Application DI container.

Builds and provides core services and use-cases to keep facades thin.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any, Awaitable, Callable, Optional

from telethon import TelegramClient
from telethon.hints import Entity

from src.core.config import FetcherConfig
from src.models.schemas import SourceInfo
from src.observability.metrics import ensure_metrics_server
from src.observability.metrics_adapter import (
    MetricsAdapter,
    NoopMetricsAdapter,
    PrometheusMetricsAdapter,
)
from src.repositories.message_repository import MessageRepository
from src.repositories.mongo_repository import MongoMessageRepository
from src.services.command_subscriber import CommandSubscriber
from src.services.event_publisher import EventPublisher, EventPublisherProtocol
from src.services.extractors.message_extractor import MessageExtractor
from src.services.fetching.date_range_processor import DateRangeProcessor
from src.services.finalization.finalization_orchestrator import FinalizationOrchestrator
from src.services.gateway.telegram_gateway import TelegramGateway
from src.services.mappers.source_mapper import SourceInfoMapper
from src.services.postprocess.finalizer import ResultFinalizer
from src.services.preprocess import strategies as pp_strategies
from src.services.preprocess.message_preprocessor import MessagePreprocessor
from src.services.progress.progress_service import ProgressService
from src.services.progress_tracker import ProgressTracker
from src.services.runners.fetch_runner import FetchRunner, FetchRunnerDeps
from src.services.session_manager import SessionManager
from src.services.strategy.factory import StrategyFactory
from src.services.strategy.protocols import StrategyProtocol
from src.services.usecases.fetch_chat import (
    FetchChatDeps,
    FetchChatUseCase,
)
from src.services.usecases.fetch_date_range import (
    FetchDateRangeDeps,
    FetchDateRangeUseCase,
)


class Container:
    """Container building all primary services for the fetcher app."""

    def __init__(self, *, config: FetcherConfig) -> None:
        """Build and wire core components from configuration."""
        self._config = config

        # Session
        self._session = SessionManager(
            api_id=config.telegram_api_id,
            api_hash=config.telegram_api_hash,
            phone=config.telegram_phone,
            session_dir=config.session_dir,
        )

        # Repository and post-processing
        if config.storage_backend == "mongo":
            self._repository = MongoMessageRepository(
                url=config.mongo_url,
                db=config.mongo_db,
                collection=config.mongo_collection,
            )
        else:
            self._repository = MessageRepository(
                config.data_dir, schema_version=config.data_schema_version
            )
        self._finalizer = ResultFinalizer(self._repository)

        # Events and metrics
        self._event_publisher: EventPublisherProtocol = EventPublisher(
            redis_url=config.redis_url,
            redis_password=config.redis_password,
            enabled=config.enable_events,
            events_channel=config.events_channel,
            service_name=config.service_name,
        )
        self._metrics: MetricsAdapter = (
            PrometheusMetricsAdapter()
            if config.enable_metrics
            else NoopMetricsAdapter()
        )

        # Progress
        self._progress_tracker = ProgressTracker(
            config.progress_file, schema_version=config.progress_schema_version
        )
        self._progress = ProgressService(
            metrics=self._metrics,
            event_publisher=self._event_publisher,
            enable_events=config.enable_progress_events,
        )

        # Mapping, preprocessing, gateway
        self._source_mapper = SourceInfoMapper()
        self._preprocessor = MessagePreprocessor(
            link_normalize_enabled=config.link_normalize_enabled,
            token_estimate_enabled=config.token_estimate_enabled,
            message_classifier_enabled=config.message_classifier_enabled,
            language_detect_enabled=config.language_detect_enabled,
            merge_short_messages_enabled=config.merge_short_messages_enabled,
            merge_short_messages_max_length=config.merge_short_messages_max_length,
            merge_short_messages_max_gap_seconds=(
                config.merge_short_messages_max_gap_seconds
            ),
            normalize_url_fn=pp_strategies.normalize_url,
            estimate_tokens_fn=pp_strategies.estimate_tokens,
            classify_message_fn=pp_strategies.classify_message,
            detect_language_fn=pp_strategies.detect_language,
        )
        self._telegram_gateway = TelegramGateway()
        self._message_extractor = MessageExtractor(
            self._telegram_gateway,
            comments_limit=config.comments_limit_per_message,
        )

        # Iteration helper and strategy factory
        self._date_range_processor = DateRangeProcessor(
            config=self._config,
            event_publisher=self._event_publisher,
            metrics=self._metrics,
            strategy_name=self._config.fetch_mode,
        )
        self._strategy_factory = StrategyFactory(self._config)

    def initialize_runtime(self) -> None:
        """Perform side-effectful initialization (connect events, metrics server)."""
        from contextlib import suppress

        with suppress(Exception):
            self._event_publisher.connect()
        if self._config.enable_metrics and self._config.metrics_mode in ("scrape", "both"):
            with suppress(Exception):
                ensure_metrics_server(self._config.metrics_port)

    def provide_telegram_gateway(self) -> TelegramGateway:
        """Provide Telegram gateway instance."""
        return self._telegram_gateway

    def provide_finalization_orchestrator(self) -> FinalizationOrchestrator:
        """Provide finalization orchestrator instance."""
        return FinalizationOrchestrator(
            finalizer=self._finalizer,
            progress_service=self._progress,
            schema_version=self._config.data_schema_version,
            preprocessing_version=self._config.preprocessing_version,
        )

    def provide_progress_service(self) -> ProgressService:
        """Provide progress service facade."""
        return self._progress

    def provide_session_manager(self) -> SessionManager:
        """Provide Telegram session manager."""
        return self._session

    def provide_strategy(self, date_str: Optional[str] = None) -> StrategyProtocol:
        """Provide active fetch strategy based on config or explicit date."""
        strategy = self._strategy_factory.create(date_str)
        # keep processor labels in sync
        with suppress(Exception):
            self._date_range_processor.set_strategy_name(strategy.get_strategy_name())
        return strategy

    def provide_progress_tracker(self) -> ProgressTracker:
        """Provide progress tracker instance."""
        return self._progress_tracker

    def provide_repository(self) -> MessageRepository:
        """Provide message repository instance."""
        return self._repository

    def provide_event_publisher(self) -> EventPublisherProtocol:
        """Provide event publisher instance."""
        return self._event_publisher

    def provide_metrics(self) -> MetricsAdapter:
        """Provide metrics adapter instance."""
        return self._metrics

    def provide_fetch_date_range_use_case(
        self,
        *,
        extract_message_data: (
            Callable[[TelegramClient, Entity, Any, SourceInfo], Awaitable[Any]] | None
        ) = None,
    ) -> FetchDateRangeUseCase:
        """Provide FetchDateRangeUseCase wired with stored dependencies.

        Args:
            extract_message_data: Callable to extract Message model from
                Telethon message

        Returns:
            Configured FetchDateRangeUseCase
        """
        deps = FetchDateRangeDeps(
            config=self._config,
            repository=self._repository,
            preprocessor=self._preprocessor,
            source_mapper=self._source_mapper,
            date_range_processor=self._date_range_processor,
            progress_service=self._progress,
            progress_tracker=self._progress_tracker,
            finalization_orchestrator=self.provide_finalization_orchestrator(),
            extract_message_data=(
                extract_message_data
                if extract_message_data is not None
                else self._message_extractor.extract
            ),
        )
        return FetchDateRangeUseCase(deps)

    def provide_fetch_chat_use_case(
        self, *, date_range_use_case: FetchDateRangeUseCase
    ) -> FetchChatUseCase:
        """Provide FetchChatUseCase using gateway and mapper.

        Args:
            date_range_use_case: Previously provisioned FetchDateRangeUseCase
        """
        deps = FetchChatDeps(
            config=self._config,
            telegram_gateway=self.provide_telegram_gateway(),
            source_mapper=self._source_mapper,
            date_range_use_case=date_range_use_case,
        )
        return FetchChatUseCase(deps)

    def provide_message_extractor(self) -> MessageExtractor:
        """Provide message extractor for core/message fields and comments."""
        return self._message_extractor

    def provide_fetch_runner(self) -> FetchRunner:
        """Provide FetchRunner coordinator with composed dependencies."""
        deps = FetchRunnerDeps(
            config=self._config,
            session_manager=self._session,
            chat_use_case=self.provide_fetch_chat_use_case(
                date_range_use_case=self.provide_fetch_date_range_use_case()
            ),
        )
        return FetchRunner(deps)

    def provide_command_handler(self) -> Callable[[dict[str, Any]], Awaitable[None]]:
        """Provide default async handler for Redis commands.

        Supported command JSON keys:
        - command: must be 'fetch'
        - chat: chat identifier (required)
        - date: optional date string YYYY-MM-DD to influence strategy
        Other keys are currently ignored.
        """

        async def _handler(command_data: dict[str, Any]) -> None:
            # Lazy imports to avoid any potential import cycles at module import time
            from src.utils.correlation import ensure_correlation_id

            if command_data.get("command") != "fetch":
                # Ignore unsupported commands; validation is done in subscriber as well
                return

            chat = command_data.get("chat")
            date_str = command_data.get("date")
            if not chat:
                # Nothing to do without a target chat
                return

            strategy = self.provide_strategy(date_str)
            runner = self.provide_fetch_runner()
            await runner.run_single(
                strategy=strategy,
                chat_identifier=str(chat),
                correlation_id=ensure_correlation_id(),
            )

        return _handler

    def provide_command_subscriber(
        self, *, worker_id: Optional[str] = None
    ) -> CommandSubscriber:
        """Provide Redis BLPOP-based command subscriber instance.

        Args:
            worker_id: Optional identifier for this worker; defaults to service_name

        Returns:
            Configured CommandSubscriber
        """
        return CommandSubscriber(
            redis_url=self._config.redis_url,
            redis_password=self._config.redis_password,
            command_handler=self.provide_command_handler(),
            worker_id=worker_id or self._config.service_name,
            commands_queue=self._config.commands_queue,
            blpop_timeout=self._config.commands_blpop_timeout,
            metrics=self._metrics,
        )
