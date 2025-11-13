"""Simple circuit breaker implementation with Prometheus metrics.

States:
- 0 CLOSED: normal operation
- 1 OPEN: short-circuit; calls are blocked until reset timeout elapses
- 2 HALF_OPEN: allow a trial call; if success -> CLOSED, else -> OPEN

This breaker is intentionally minimal and dependency-free. Use per sensitive
operation (e.g., Telegram connect/auth calls) to avoid hot-loop retries.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional

from src.observability.metrics import breaker_state, breaker_open_total


CLOSED = 0
OPEN = 1
HALF_OPEN = 2


@dataclass
class BreakerConfig:
    """Configuration for CircuitBreaker."""

    failure_threshold: int = 5
    reset_timeout_seconds: float = 60.0
    target: str = "telethon"
    worker: str = "session"


class CircuitBreaker:
    """Naive circuit breaker with time-based reset.

    Not thread-safe; intended for single-threaded async context.
    """

    def __init__(self, cfg: Optional[BreakerConfig] = None) -> None:
        self.cfg = cfg or BreakerConfig()
        self._state: int = CLOSED
        self._failures: int = 0
        self._opened_at: float = 0.0
        # Initialize state gauge
        breaker_state.labels(target=self.cfg.target, worker=self.cfg.worker).set(self._state)

    def _maybe_transition_from_open(self) -> None:
        if self._state != OPEN:
            return
        elapsed = time.monotonic() - self._opened_at
        if elapsed >= self.cfg.reset_timeout_seconds:
            # Move to HALF_OPEN; allow a trial call
            self._state = HALF_OPEN
            breaker_state.labels(target=self.cfg.target, worker=self.cfg.worker).set(self._state)

    def allow_call(self) -> bool:
        """Check if a call is allowed under current state.

        Returns:
            True if call should proceed; False if short-circuited
        """
        if self._state == OPEN:
            self._maybe_transition_from_open()
        return self._state in (CLOSED, HALF_OPEN)

    def record_success(self) -> None:
        """Record a successful call and update breaker state if needed."""
        self._failures = 0
        if self._state != CLOSED:
            self._state = CLOSED
            breaker_state.labels(target=self.cfg.target, worker=self.cfg.worker).set(self._state)

    def record_failure(self, reason: str = "error") -> None:
        """Record a failed call; may transition to OPEN if threshold reached."""
        self._failures += 1
        if self._failures >= self.cfg.failure_threshold:
            # Transition to OPEN
            self._state = OPEN
            self._opened_at = time.monotonic()
            breaker_state.labels(target=self.cfg.target, worker=self.cfg.worker).set(self._state)
            breaker_open_total.labels(
                target=self.cfg.target, worker=self.cfg.worker, reason=reason
            ).inc()

    @property
    def state(self) -> int:
        return self._state

    @property
    def failures(self) -> int:
        return self._failures
