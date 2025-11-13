"""Graceful shutdown handling for daemon processes.

This module provides signal handling and graceful shutdown coordination
for long-running daemon processes.
"""

import asyncio
import logging
import signal
import sys
from types import FrameType
from typing import Optional

logger = logging.getLogger(__name__)


class ShutdownHandler:
    """Manages graceful shutdown for daemon processes."""

    def __init__(self) -> None:
        """Initialize shutdown handler."""
        self._shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        self._signals_registered = False

    def register_signals(self) -> None:
        """Register signal handlers for graceful shutdown.

        Handles SIGTERM (Docker stop) and SIGINT (Ctrl+C).
        """
        if self._signals_registered:
            logger.warning("Signal handlers already registered")
            return

        # Windows doesn't support SIGTERM, only SIGINT and SIGBREAK
        if sys.platform == "win32":
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGBREAK, self._signal_handler)
            logger.info("Registered shutdown signals: SIGINT, SIGBREAK")
        else:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            logger.info("Registered shutdown signals: SIGTERM, SIGINT")

        self._signals_registered = True

    def _signal_handler(self, signum: int, frame: Optional[FrameType]) -> None:
        """Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = signal.Signals(signum).name
        logger.info(
            f"Received {signal_name}, initiating graceful shutdown",
            extra={"signal": signal_name, "signal_number": signum},
        )
        self.request_shutdown()

    def request_shutdown(self) -> None:
        """Request graceful shutdown.

        Can be called programmatically or by signal handlers.
        """
        if not self._shutdown_requested:
            self._shutdown_requested = True
            self._shutdown_event.set()
            logger.info("Shutdown requested")

    @property
    def should_shutdown(self) -> bool:
        """Check if shutdown has been requested.

        Returns:
            True if shutdown requested, False otherwise
        """
        return self._shutdown_requested

    async def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown signal.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            True if shutdown signaled, False if timeout reached
        """
        if timeout:
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=timeout)
                return True
            except asyncio.TimeoutError:
                return False
        else:
            await self._shutdown_event.wait()
            return True

    def reset(self) -> None:
        """Reset shutdown state.

        Useful for testing or restarting services.
        """
        self._shutdown_requested = False
        self._shutdown_event.clear()
        logger.debug("Shutdown state reset")


# Global shutdown handler instance
_global_shutdown_handler: Optional[ShutdownHandler] = None


def get_shutdown_handler() -> ShutdownHandler:
    """Get global shutdown handler instance.

    Returns:
        Global ShutdownHandler instance
    """
    global _global_shutdown_handler
    if _global_shutdown_handler is None:
        _global_shutdown_handler = ShutdownHandler()
    return _global_shutdown_handler


def register_shutdown_signals() -> ShutdownHandler:
    """Register signal handlers and return shutdown handler.

    Convenience function for common initialization pattern.

    Returns:
        Configured ShutdownHandler instance
    """
    handler = get_shutdown_handler()
    handler.register_signals()
    return handler


async def shutdown_on_signal(
    operation: asyncio.Task, check_interval: float = 1.0
) -> None:
    """Monitor for shutdown signal and cancel operation.

    Args:
        operation: Task to cancel on shutdown
        check_interval: How often to check for shutdown signal
    """
    handler = get_shutdown_handler()

    try:
        while not handler.should_shutdown:
            if operation.done():
                return
            await asyncio.sleep(check_interval)

        logger.info("Shutdown signal received, cancelling operation")
        operation.cancel()
    except asyncio.CancelledError:
        logger.debug("Shutdown monitor cancelled")
