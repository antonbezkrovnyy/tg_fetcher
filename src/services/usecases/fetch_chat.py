"""Use case to process a chat's date ranges with bounded concurrency."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, AsyncIterator, Protocol

from telethon import TelegramClient

from src.core.config import FetcherConfig
from src.models.schemas import SourceInfo

logger = logging.getLogger(__name__)


class _TelegramGateway(Protocol):
    async def get_entity(self, client: TelegramClient, chat_identifier: str) -> Any: ...


class _SourceMapper(Protocol):
    def extract_source_info(self, entity: Any, chat_identifier: str) -> SourceInfo: ...


class _Strategy(Protocol):
    def get_strategy_name(self) -> str: ...

    def get_date_ranges(
        self, client: TelegramClient, chat_identifier: str
    ) -> AsyncIterator[tuple[date, date]]: ...


class _DateRangeUseCase(Protocol):
    async def execute(
        self,
        *,
        client: TelegramClient,
        entity: Any,
        source_info: SourceInfo,
        start_date: date,
        end_date: date,
        correlation_id: str,
    ) -> int: ...


@dataclass
class FetchChatDeps:
    """Dependencies required by FetchChatUseCase."""

    config: FetcherConfig
    telegram_gateway: _TelegramGateway
    source_mapper: _SourceMapper
    date_range_use_case: _DateRangeUseCase


class FetchChatUseCase:
    """Process strategy ranges for a chat using a semaphore for concurrency."""

    def __init__(self, deps: FetchChatDeps) -> None:
        """Initialize use case with dependencies."""
        self.d = deps

    async def execute(
        self,
        *,
        client: TelegramClient,
        chat_identifier: str,
        strategy: _Strategy,
        correlation_id: str,
        concurrency: int | None = None,
    ) -> int:
        """Execute the use case.

        Args:
            client: Authenticated Telegram client
            chat_identifier: Chat username or ID
            strategy: Strategy providing date ranges
            correlation_id: Correlation id for logging
            concurrency: Optional override for per-chat concurrency
        """
        # Resolve entity and source info
        entity = await self.d.telegram_gateway.get_entity(client, chat_identifier)
        source_info = self.d.source_mapper.extract_source_info(entity, chat_identifier)

        sem = asyncio.Semaphore(concurrency or self.d.config.fetch_concurrency_per_chat)
        fetched_total = 0
        tasks: list[asyncio.Task[int]] = []

        async def run_one(sd: date, ed: date) -> int:
            async with sem:
                return await self.d.date_range_use_case.execute(
                    client=client,
                    entity=entity,
                    source_info=source_info,
                    start_date=sd,
                    end_date=ed,
                    correlation_id=correlation_id,
                )

        ranges = strategy.get_date_ranges(client, chat_identifier)
        async for start_date, end_date in ranges:
            tasks.append(asyncio.create_task(run_one(start_date, end_date)))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    logger.warning("Date range task failed", exc_info=True)
                elif isinstance(r, int):
                    fetched_total += r

        return fetched_total
