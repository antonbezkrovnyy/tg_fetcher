import re
from types import SimpleNamespace

from src.utils.correlation import (
    CorrelationContext,
    ensure_correlation_id,
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
)


def test_generate_correlation_id_uuid_format():
    cid = generate_correlation_id()
    assert re.match(r"^[0-9a-f\-]{36}$", cid)


def test_ensure_sets_when_missing_and_returns_same():
    # Ensure no id set yet (start from None)
    set_correlation_id(None)  # type: ignore[arg-type]
    first = ensure_correlation_id()
    second = ensure_correlation_id()
    assert first == second
    assert get_correlation_id() == first


def test_context_manager_sets_and_resets():
    prev = get_correlation_id()
    with CorrelationContext("custom-123") as cid:
        assert cid == "custom-123"
        assert get_correlation_id() == "custom-123"
    # After context exit, previous value restored
    assert get_correlation_id() == prev
