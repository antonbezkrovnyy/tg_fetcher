from src.core.exceptions import (
    ChatNotFoundError,
    DataValidationError,
    FloodWaitError,
    NetworkError,
    TelegramAuthError,
    TelegramError,
)


def test_telegram_error_base_attributes():
    err = TelegramError("oops", correlation_id="cid-1")
    assert str(err) == "oops"
    assert err.correlation_id == "cid-1"


def test_auth_error_includes_phone_and_correlation():
    err = TelegramAuthError("auth failed", phone="+10000000000", correlation_id="c2")
    assert "auth failed" in str(err)
    assert err.phone == "+10000000000"
    assert err.correlation_id == "c2"


def test_flood_wait_holds_wait_and_chat():
    err = FloodWaitError(
        "slow down", wait_seconds=7, chat="@ru_python", correlation_id="c3"
    )
    assert err.wait_seconds == 7
    assert err.chat == "@ru_python"
    assert err.correlation_id == "c3"


def test_network_error_retry_count():
    err = NetworkError("net down", retry_count=2)
    assert err.retry_count == 2


def test_data_validation_error_list_attached():
    err = DataValidationError("bad data", validation_errors=[{"field": "x"}])
    assert err.validation_errors == [{"field": "x"}]
