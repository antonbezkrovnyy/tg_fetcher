"""
Graceful shutdown and healthcheck utilities
"""

import asyncio
import json
import logging
import os
import signal
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Global shutdown flag
_shutdown_requested = False
_current_task: Optional[str] = None

HEALTHCHECK_FILE = Path("/tmp/.fetcher_healthy")


def is_shutdown_requested() -> bool:
    """Check if shutdown was requested"""
    return _shutdown_requested


def set_current_task(task_description: str):
    """Set description of current task being processed"""
    global _current_task
    _current_task = task_description
    update_healthcheck(status="running", current_task=task_description)


def get_current_task() -> Optional[str]:
    """Get description of current task"""
    return _current_task


def request_shutdown(signum=None, frame=None):
    """Request graceful shutdown"""
    global _shutdown_requested

    if _shutdown_requested:
        logger.warning("Shutdown already requested, forcing exit...")
        os._exit(1)

    _shutdown_requested = True
    signal_name = signal.Signals(signum).name if signum else "UNKNOWN"

    logger.warning(
        f"Shutdown requested via signal {signal_name}",
        extra={
            "signal": signal_name,
            "signal_number": signum,
            "current_task": _current_task,
        },
    )

    if _current_task:
        logger.info(f"Will shutdown after completing: {_current_task}")
    else:
        logger.info("Initiating immediate shutdown")


def setup_signal_handlers():
    """Setup handlers for graceful shutdown"""
    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    logger.info("Signal handlers configured for graceful shutdown")


async def shutdown_with_timeout(coro, timeout: int = 30):
    """
    Execute coroutine with timeout for graceful shutdown

    Args:
        coro: Coroutine to execute
        timeout: Max seconds to wait
    """
    try:
        await asyncio.wait_for(coro, timeout=timeout)
        logger.info("Graceful shutdown completed successfully")
    except asyncio.TimeoutError:
        logger.error(
            f"Graceful shutdown timed out after {timeout}s",
            extra={"timeout_seconds": timeout},
        )
    except Exception as e:
        logger.error(
            f"Error during graceful shutdown: {e}",
            extra={"error_type": type(e).__name__},
            exc_info=True,
        )


def update_healthcheck(
    status: str = "healthy",
    current_task: Optional[str] = None,
    last_success: Optional[datetime] = None,
    error: Optional[str] = None,
):
    """
    Update healthcheck file

    Args:
        status: Current status (healthy, running, error)
        current_task: Description of current task
        last_success: Timestamp of last successful operation
        error: Error message if any
    """
    try:
        health_data = {
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "current_task": current_task,
            "last_success": last_success.isoformat() if last_success else None,
            "error": error,
            "pid": os.getpid(),
        }

        HEALTHCHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HEALTHCHECK_FILE, "w") as f:
            json.dump(health_data, f, indent=2)

    except Exception as e:
        # Don't fail if healthcheck update fails
        logger.debug(f"Failed to update healthcheck file: {e}")


def mark_healthy():
    """Mark service as healthy"""
    update_healthcheck(status="healthy", last_success=datetime.now(UTC))


def mark_error(error_message: str):
    """Mark service as having an error"""
    update_healthcheck(status="error", error=error_message)


def check_health() -> dict:
    """
    Read current health status
    Returns dict with health information
    """
    try:
        if not HEALTHCHECK_FILE.exists():
            return {"status": "unknown", "message": "No healthcheck file found"}

        with open(HEALTHCHECK_FILE, "r") as f:
            data = json.load(f)

        # Check if healthcheck is recent (within last 5 minutes)
        timestamp = datetime.fromisoformat(data["timestamp"])
        age_seconds = (datetime.now(UTC) - timestamp).total_seconds()

        if age_seconds > 300:  # 5 minutes
            data["status"] = "stale"
            data["age_seconds"] = age_seconds

        return data

    except Exception as e:
        return {"status": "error", "message": f"Failed to read healthcheck: {e}"}


# Create healthcheck script for Docker
def create_healthcheck_script():
    """Create standalone healthcheck script for Docker HEALTHCHECK"""
    script = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

HEALTHCHECK_FILE = Path("/tmp/.fetcher_healthy")

try:
    if not HEALTHCHECK_FILE.exists():
        print("UNHEALTHY: No healthcheck file found")
        sys.exit(1)

    with open(HEALTHCHECK_FILE, 'r') as f:
        data = json.load(f)

    status = data.get('status', 'unknown')
    timestamp = datetime.fromisoformat(data['timestamp'])
    age_seconds = (datetime.now(UTC) - timestamp).total_seconds()

    if age_seconds > 300:  # 5 minutes stale
        print(f"UNHEALTHY: Healthcheck stale ({age_seconds:.0f}s old)")
        sys.exit(1)

    if status == 'error':
        print(f"UNHEALTHY: {data.get('error', 'Unknown error')}")
        sys.exit(1)

    print(f"HEALTHY: {status} - {data.get('current_task', 'idle')}")
    sys.exit(0)

except Exception as e:
    print(f"UNHEALTHY: Failed to check health: {e}")
    sys.exit(1)
"""

    healthcheck_script_path = Path("/app/healthcheck.py")
    healthcheck_script_path.write_text(script)
    healthcheck_script_path.chmod(0o755)
    logger.info(f"Healthcheck script created at {healthcheck_script_path}")
