import json

from src.services.event_publisher import EventPublisher


def test_event_publisher_payload_structure_and_content():
    pub = EventPublisher(
        redis_url="redis://localhost:6379",
        enabled=True,
        events_channel="tg_events",
        service_name="test_service",
    )

    published = {}

    class StubRedis:
        def publish(self, channel, payload):  # noqa: D401
            published["channel"] = channel
            published["payload"] = payload
            return 1  # one subscriber

    # Inject stub client directly
    pub._redis_client = StubRedis()  # type: ignore[attr-defined]

    pub.publish_fetch_complete(
        chat="@ru_python",
        date="2025-01-02",
        message_count=42,
        file_path="/data/ru_python/2025-01-02.json",
        duration_seconds=3.14159,
        checksum_sha256="abc123",
        estimated_tokens_total=1000,
        first_message_ts="2025-01-02T00:00:01+00:00",
        last_message_ts="2025-01-02T23:59:59+00:00",
        schema_version="1.0",
        preprocessing_version="0.2",
        summary_file_path="/data/summary.json",
        threads_file_path="/data/threads.json",
        participants_file_path="/data/participants.json",
    )

    assert published["channel"] == "tg_events"
    data = json.loads(published["payload"])  # published payload is JSON string

    # Base fields
    assert data["event"] == "messages_fetched"
    assert data["service"] == "test_service"
    assert "timestamp" in data and isinstance(data["timestamp"], str)
    assert "correlation_id" in data  # may be None or string; not asserting type

    # Payload-specific fields
    assert data["chat"] == "@ru_python"
    assert data["date"] == "2025-01-02"
    assert data["message_count"] == 42
    assert data["file_path"].endswith("ru_python/2025-01-02.json")
    # duration_seconds is rounded to 2 decimals in publisher
    assert isinstance(data["duration_seconds"], float)
    assert abs(data["duration_seconds"] - 3.14) < 1e-9

    assert data["checksum_sha256"] == "abc123"
    assert data["estimated_tokens_total"] == 1000
    assert data["first_message_ts"].startswith("2025-01-02T")
    assert data["last_message_ts"].startswith("2025-01-02T")
    assert data["schema_version"] == "1.0"
    assert data["preprocessing_version"] == "0.2"
    assert data["summary_file_path"].endswith("summary.json")
    assert data["threads_file_path"].endswith("threads.json")
    assert data["participants_file_path"].endswith("participants.json")
