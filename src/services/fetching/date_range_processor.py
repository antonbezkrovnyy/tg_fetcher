"""Date range iteration helper to slim down FetcherService.

Constructs MessageIterator with injected dependencies and runs the provided
handler for each message.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Awaitable, Callable, Tuple

from telethon import TelegramClient
from telethon.hints import Entity
from telethon.tl.custom import Message as TelethonMessage

from src.core.config import FetcherConfig
from src.models.schemas import SourceInfo
from src.observability.metrics_adapter import MetricsAdapter
from src.services.event_publisher import EventPublisherProtocol
from src.services.fetching.message_iterator import MessageIterator


class DateRangeProcessor:
    """Adapter that encapsulates message iteration for a date range."""

    def __init__(
        self,
        *,
        config: FetcherConfig,
        event_publisher: EventPublisherProtocol | None,
        metrics: MetricsAdapter,
        strategy_name: str,
    ) -> None:
        self._config = config
        self._event_publisher = event_publisher
        self._metrics = metrics
        self._strategy_name = strategy_name

    def set_strategy_name(self, name: str) -> None:
        """Update strategy name for metrics/progress labelling."""
        self._strategy_name = name

    async def iterate(
        self,
        *,
        client: TelegramClient,
        entity: Entity,
        source_info: SourceInfo,
        start_date: date,
        start_datetime: datetime,
        end_datetime: datetime,
        correlation_id: str,
        handle: Callable[[TelethonMessage], Awaitable[bool]],
    ) -> Tuple[int, int]:
        iterator = MessageIterator(
            client=client,
            entity=entity,
            source_id=source_info.id,
            start_date=start_date,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            config=self._config,
            event_publisher=self._event_publisher,
            metrics=self._metrics,
            strategy_name=self._strategy_name,
            correlation_id=correlation_id,
        )
        return await iterator.run(handle)
