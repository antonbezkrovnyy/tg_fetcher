#!/usr/bin/env python3
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

HEALTHCHECK_FILE = Path("/tmp/.fetcher_healthy")


def main():
    try:
        if not HEALTHCHECK_FILE.exists():
            print("UNHEALTHY: No healthcheck file found")
            sys.exit(1)

        data = json.loads(HEALTHCHECK_FILE.read_text())
        status = data.get("status", "unknown")
        ts = data.get("timestamp")
        if ts:
            timestamp = datetime.fromisoformat(ts)
            age_seconds = (datetime.now(UTC) - timestamp).total_seconds()
        else:
            age_seconds = 999999

        if age_seconds > 300:
            print(f"UNHEALTHY: Healthcheck stale ({age_seconds:.0f}s old)")
            sys.exit(1)

        if status == "error":
            print(f"UNHEALTHY: {data.get('error', 'Unknown error')}")
            sys.exit(1)

        print(f"HEALTHY: {status} - {data.get('current_task', 'idle')}")
        sys.exit(0)

    except Exception as e:
        print(f"UNHEALTHY: Failed to check health: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
