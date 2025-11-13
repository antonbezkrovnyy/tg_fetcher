import pytest

from src.services.event_publisher import EventPublisher


def test_event_publisher_disabled_noop():
    pub = EventPublisher(
        redis_url="redis://localhost:6379",
        enabled=False,
        events_channel="tg_events",
        service_name="test_service",
    )

    # Should not raise on connect or publish when disabled
    pub.connect()
    pub.publish_fetch_started(chat="@c", date="2025-01-01", strategy="s")
    pub.publish_fetch_progress(
        chat="@c", date="2025-01-01", messages_processed=1, messages_fetched=1
    )
    pub.publish_fetch_stage(chat="@c", date="2025-01-01", stage="saving")
    pub.publish_fetch_skipped(chat="@c", date="2025-01-01", reason="exists")
    pub.publish_fetch_failed(chat="@c", date="2025-01-01", error="boom")
    pub.publish_fetch_complete(
        chat="@c", date="2025-01-01", message_count=1, file_path="/tmp/file.json"
    )


def test_event_publisher_not_connected_noop():
    # Enabled but not connected: publish should not raise
    pub = EventPublisher(
        redis_url="redis://localhost:6379",
        enabled=True,
        events_channel="tg_events",
        service_name="test_service",
    )
    # Do not call connect()
    pub.publish_fetch_complete(
        chat="@c", date="2025-01-01", message_count=0, file_path="/tmp/f.json"
    )


def test_event_publisher_publish_failure_is_non_fatal(monkeypatch):
    pub = EventPublisher(
        redis_url="redis://localhost:6379",
        enabled=True,
        events_channel="tg_events",
        service_name="test_service",
    )

    class StubRedis:
        def publish(self, channel, payload):  # noqa: D401 - simple stub
            raise RuntimeError("publish boom")

        def close(self):
            pass

    # Inject stub client directly to avoid real Redis
    pub._redis_client = StubRedis()  # type: ignore[attr-defined]

    # Should not raise even if client.publish fails
    pub.publish_fetch_complete(
        chat="@c",
        date="2025-01-01",
        message_count=1,
        file_path="/tmp/file.json",
    )
