from datetime import datetime

from src.services.command_subscriber import create_fetch_command


def test_create_fetch_command_fields_present():
    cmd = create_fetch_command(
        chat="ru_python", days_back=2, limit=50, strategy="recent", requested_by="test"
    )
    assert cmd["command"] == "fetch"
    assert cmd["chat"] == "ru_python"
    assert cmd["days_back"] == 2
    assert cmd["limit"] == 50
    assert cmd["strategy"] == "recent"
    assert cmd["requested_by"] == "test"
    assert isinstance(cmd["timestamp"], str)
    assert cmd["timestamp"].endswith("Z")


def test_create_fetch_command_timestamp_isoformat():
    cmd = create_fetch_command(chat="ru_python")
    ts = cmd["timestamp"]
    # tolerance: ensure ISO-like with 'Z' and parse when stripping Z
    assert ts.endswith("Z")
    # remove trailing Z for parsing
    parsed = datetime.fromisoformat(ts[:-1])
    assert isinstance(parsed, datetime)
