from types import SimpleNamespace

from src.services.progress.progress_service import ProgressService


class BoomMetrics:
    def set_progress(self, chat, date, value):  # noqa: ANN001
        raise RuntimeError("metrics set")

    def reset_progress(self, chat, date):  # noqa: ANN001
        raise RuntimeError("metrics reset")

    # Command counters not used here
    def inc_command_received(self, queue, worker):  # noqa: ANN001, D401
        return None

    def inc_command_success(self, queue, worker):  # noqa: ANN001, D401
        return None

    def inc_command_failed(self, queue, worker, error_type):  # noqa: ANN001, D401
        return None

    def inc_command_timeout(self, queue, worker):  # noqa: ANN001, D401
        return None


class SpyPublisher:
    def __init__(self):
        self.calls = []

    def publish_fetch_stage(self, **data):  # noqa: ANN001
        self.calls.append(("stage", data))

    def publish_fetch_skipped(self, **data):  # noqa: ANN001
        self.calls.append(("skipped", data))

    def publish_fetch_complete(self, **data):  # noqa: ANN001
        self.calls.append(("complete", data))


class RaisingPublisher:
    def publish_fetch_stage(self, **data):  # noqa: ANN001, D401
        raise RuntimeError("stage boom")

    def publish_fetch_skipped(self, **data):  # noqa: ANN001, D401
        raise RuntimeError("skipped boom")

    def publish_fetch_complete(self, **data):  # noqa: ANN001, D401
        raise RuntimeError("complete boom")


def test_progress_service_metrics_best_effort():
    ps = ProgressService(
        metrics=BoomMetrics(), event_publisher=None, enable_events=False
    )
    # Should not raise despite metrics throwing
    ps.set_progress("@c", "2025-11-01", 5)
    ps.reset_gauge("@c", "2025-11-01")


def test_progress_service_events_emitted_when_enabled():
    pub = SpyPublisher()
    ps = ProgressService(metrics=BoomMetrics(), event_publisher=pub, enable_events=True)
    ps.publish_stage(chat="@c", date="2025-11-01", stage="start")
    ps.publish_skipped(
        chat="@c",
        date="2025-11-01",
        reason="skip",
        checksum_expected=None,
        checksum_actual=None,
    )
    ps.publish_complete(
        chat="@c",
        date="2025-11-01",
        message_count=10,
        file_path="/tmp/x.jsonl",
        duration_seconds=1.23,
    )
    kinds = [k for k, _ in pub.calls]
    assert kinds == ["stage", "skipped", "complete"]


def test_progress_service_events_disabled_noop():
    pub = SpyPublisher()
    ps = ProgressService(
        metrics=BoomMetrics(), event_publisher=pub, enable_events=False
    )
    ps.publish_stage(chat="@c", date="2025-11-01", stage="start")
    assert pub.calls == []


def test_progress_service_swallows_publisher_exceptions():
    ps = ProgressService(
        metrics=BoomMetrics(), event_publisher=RaisingPublisher(), enable_events=True
    )
    # Ensure no exceptions propagate from publisher errors
    ps.publish_stage(chat="@c", date="2025-11-01", stage="start")
    ps.publish_skipped(
        chat="@c",
        date="2025-11-01",
        reason="skip",
        checksum_expected=None,
        checksum_actual=None,
    )
    ps.publish_complete(
        chat="@c",
        date="2025-11-01",
        message_count=10,
        file_path="/tmp/x.jsonl",
        duration_seconds=1.23,
    )
