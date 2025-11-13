import asyncio
from typing import Any

import pytest

from src.core.config import FetcherConfig
from src.core.exceptions import ChatNotFoundError
from src.services.runners.fetch_runner import FetchRunner, FetchRunnerDeps


class _Session:
    def __init__(self) -> None:
        self.opened = False

    async def __aenter__(self) -> Any:  # simulate TelegramClient
        self.opened = True
        await asyncio.sleep(0)
        return object()

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        await asyncio.sleep(0)
        self.opened = False


class _ChatUC:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def execute(self, **kwargs) -> int:  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        await asyncio.sleep(0)
        return 1


class _ErrChatUC(_ChatUC):
    async def execute(self, **kwargs) -> int:  # type: ignore[no-untyped-def]
        if kwargs.get("chat_identifier") == "@bad":
            raise ChatNotFoundError("bad chat")
        return await super().execute(**kwargs)


class _Strategy:
    def get_strategy_name(self) -> str:
        return "test"


@pytest.mark.asyncio
async def test_fetch_runner_runs_all_chats():
    cfg = FetcherConfig()
    cfg.telegram_chats = ["@a", "@b"]

    uc = _ChatUC()
    deps = FetchRunnerDeps(config=cfg, session_manager=_Session(), chat_use_case=uc)
    runner = FetchRunner(deps)

    await runner.run_all(strategy=_Strategy(), correlation_id="cid")

    assert [c["chat_identifier"] for c in uc.calls] == ["@a", "@b"]
    # concurrency passed from config (None by default)
    assert all("concurrency" in c for c in uc.calls)


@pytest.mark.asyncio
async def test_fetch_runner_handles_errors_and_continues():
    cfg = FetcherConfig()
    cfg.telegram_chats = ["@good", "@bad", "@good2"]

    uc = _ErrChatUC()
    deps = FetchRunnerDeps(config=cfg, session_manager=_Session(), chat_use_case=uc)
    runner = FetchRunner(deps)

    await runner.run_all(strategy=_Strategy(), correlation_id="cid")

    # Calls were recorded for non-failing chats
    assert [c["chat_identifier"] for c in uc.calls] == ["@good", "@good2"]
