"""FetchRunner coordinates running fetch over chats using injected use-cases.

Keeps FetcherService minimal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from telethon import TelegramClient

from src.core.config import FetcherConfig
from src.core.exceptions import ChatNotFoundError, NetworkError

logger = logging.getLogger(__name__)


class _ChatUseCase(Protocol):
    async def execute(
        self,
        *,
        client: TelegramClient,
        chat_identifier: str,
        strategy: Any,
        correlation_id: str,
        concurrency: int | None = None,
    ) -> int: ...


@dataclass
class FetchRunnerDeps:
    """Dependencies container for FetchRunner."""

    config: FetcherConfig
    session_manager: Any
    chat_use_case: _ChatUseCase


class FetchRunner:
    """Coordinates chat iteration and error handling."""

    def __init__(self, deps: FetchRunnerDeps) -> None:
        """Initialize runner with dependencies.

        Args:
            deps: Container of config, session manager, and chat use-case
        """
        self.d = deps

    async def run_all(self, *, strategy: Any, correlation_id: str) -> None:
        """Run fetching for all configured chats concurrently."""
        import asyncio

        async with self.d.session_manager as client:
            sem = asyncio.Semaphore(self.d.config.max_parallel_channels)
            tasks: list[asyncio.Task[None]] = []

            async def run_chat(chat_identifier: str) -> None:
                async with sem:
                    await self._run_one(
                        client, chat_identifier, strategy, correlation_id
                    )

            for chat_identifier in self.d.config.telegram_chats:
                tasks.append(asyncio.create_task(run_chat(chat_identifier)))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def run_single(
        self, *, strategy: Any, chat_identifier: str, correlation_id: str
    ) -> int:
        """Run fetching for a single chat and return processed count."""
        async with self.d.session_manager as client:
            return await self._safe_execute(
                client, chat_identifier, strategy, correlation_id
            )

    async def _run_one(
        self,
        client: TelegramClient,
        chat_identifier: str,
        strategy: Any,
        correlation_id: str,
    ) -> None:
        """Run fetching for one chat (fire-and-forget wrapper)."""
        await self._safe_execute(client, chat_identifier, strategy, correlation_id)

    async def _safe_execute(
        self,
        client: TelegramClient,
        chat_identifier: str,
        strategy: Any,
        correlation_id: str,
    ) -> int:
        """Safely execute use-case with error categorization and logging."""
        try:
            return await self.d.chat_use_case.execute(
                client=client,
                chat_identifier=chat_identifier,
                strategy=strategy,
                correlation_id=correlation_id,
                concurrency=self.d.config.fetch_concurrency_per_chat,
            )
        except ChatNotFoundError:
            logger.error(
                "Chat not found or inaccessible",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": "chat_not_found",
                    "chat": chat_identifier,
                },
                exc_info=True,
            )
        except NetworkError as ne:
            logger.error(
                "Network error during chat processing",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": "network_error",
                    "chat": chat_identifier,
                    "retry_count": getattr(ne, "retry_count", None),
                },
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                "Failed to process chat",
                extra={
                    "correlation_id": correlation_id,
                    "error_type": "unknown_error",
                    "error_class": type(e).__name__,
                    "chat": chat_identifier,
                },
                exc_info=True,
            )
        return 0
