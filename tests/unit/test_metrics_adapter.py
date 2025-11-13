import os

from src.observability.metrics_adapter import (
    NoopMetricsAdapter,
    PrometheusMetricsAdapter,
)


def test_noop_metrics_adapter_methods_do_nothing():
    m = NoopMetricsAdapter()
    m.set_progress("@chat", "2025-11-01", 10)
    m.reset_progress("@chat", "2025-11-01")
    m.inc_command_received("queue", "w1")
    m.inc_command_success("queue", "w1")
    m.inc_command_failed("queue", "w1", "ValueError")
    m.inc_command_timeout("queue", "w1")


def test_prometheus_metrics_adapter_basic_calls_no_raise(monkeypatch):
    # Ensure worker id is stable
    monkeypatch.setenv("HOSTNAME", "test-worker")
    m = PrometheusMetricsAdapter()

    # These should not raise even if prometheus client has defaults
    m.set_progress("@chat", "2025-11-01", 5)
    m.reset_progress("@chat", "2025-11-01")
    m.inc_command_received("cmdq", "worker-1")
    m.inc_command_success("cmdq", "worker-1")
    m.inc_command_failed("cmdq", "worker-1", "RuntimeError")
    m.inc_command_timeout("cmdq", "worker-1")
