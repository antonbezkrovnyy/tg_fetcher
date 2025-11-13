from datetime import date

import pytest
from pydantic import ValidationError

from src.core.config import FetcherConfig
from src.services.strategy.factory import StrategyFactory
from src.services.strategy.yesterday import YesterdayOnlyStrategy


def make_config(mode: str, fetch_date: date | None = None) -> FetcherConfig:
    # Minimal viable config; other fields can use defaults
    return FetcherConfig(
        fetch_mode=mode,
        fetch_date=fetch_date,
        # Provide required fields with reasonable defaults
        api_id=12345,
        api_hash="hash",
        session_name="test",
        redis_url="redis://localhost:6379/0",
    )


def test_factory_yesterday():
    cfg = make_config("yesterday")
    s = StrategyFactory(cfg).create()
    assert isinstance(s, YesterdayOnlyStrategy)


def test_factory_date_from_arg():
    cfg = make_config("date")
    s = StrategyFactory(cfg).create("2025-11-01")
    # Strategy class imported lazily; verify get_strategy_name
    assert s.get_strategy_name() == "date"


def test_factory_date_from_config():
    cfg = make_config("date", fetch_date=date(2025, 11, 2))
    s = StrategyFactory(cfg).create()
    assert s.get_strategy_name() == "date"


def test_factory_date_missing_raises():
    cfg = make_config("date")
    with pytest.raises(ValueError):
        StrategyFactory(cfg).create()


def test_factory_unsupported_mode():
    # Invalid mode is rejected at config-validation time
    with pytest.raises(ValidationError):
        make_config("unknown")
