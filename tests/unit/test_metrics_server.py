import types

import pytest

import src.observability.metrics as metrics


def test_metrics_server_idempotent(monkeypatch):
    calls = {"count": 0}

    def fake_start(port: int):
        calls["count"] += 1

    # Ensure clean state
    metrics._server_started = False  # type: ignore[attr-defined]
    monkeypatch.setattr(metrics, "start_http_server", fake_start)

    metrics.ensure_metrics_server(9999)
    metrics.ensure_metrics_server(9999)

    assert calls["count"] == 1
    assert metrics._server_started is True  # type: ignore[attr-defined]


def test_metrics_server_swallow_exception(monkeypatch):
    def boom(port: int):
        raise RuntimeError("cannot bind")

    metrics._server_started = False  # type: ignore[attr-defined]
    monkeypatch.setattr(metrics, "start_http_server", boom)

    # Should not raise and should not mark as started
    metrics.ensure_metrics_server(9998)
    assert metrics._server_started is False  # type: ignore[attr-defined]
