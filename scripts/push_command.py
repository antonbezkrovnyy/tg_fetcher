"""Utility to enqueue a fetch command into Redis commands queue.

Reads configuration from environment (FetcherConfig) and pushes a JSON command
into the configured Redis list (COMMANDS_QUEUE). Useful for manual testing of
'tg-fetch listen' workers.

Usage (PowerShell):
    # Push command for @ru_python for a given date
    .venv/Scripts/python.exe scripts/push_command.py --chat @ru_python --date 2025-11-12

Code style: PEP8 with type hints and Google-style docstrings.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Optional

import redis

from src.core.config import FetcherConfig


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser.

    Returns:
        Configured parser for pushing a command.
    """
    parser = argparse.ArgumentParser(
        prog="push-command",
        description=("Push a fetch command JSON into Redis commands queue"),
    )
    parser.add_argument(
        "--chat",
        required=True,
        help="Chat identifier (e.g., @ru_python)",
    )
    parser.add_argument(
        "--date",
        required=False,
        help="Optional date in YYYY-MM-DD. If omitted, worker strategy defaults apply.",
    )
    parser.add_argument(
        "--requested-by",
        default="manual",
        help="Requester label for auditing (default: manual)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Entrypoint for the command push helper.

    Args:
        argv: Optional list of CLI args

    Returns:
        0 on success, 1 on error
    """
    args = build_parser().parse_args(argv)

    config = FetcherConfig()
    payload = {
        "command": "fetch",
        "chat": args.chat,
        "date": args.date,
        "requested_by": args.requested_by,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    client = redis.from_url(
        config.redis_url,
        password=config.redis_password,
        decode_responses=True,
    )
    # Ensure connection
    client.ping()

    # Push to queue head to prioritize recent (LPUSH) or tail (RPUSH) for strict FIFO
    client.rpush(config.commands_queue, json.dumps(payload))

    print(
        "Enqueued command to '"
        + str(config.commands_queue)
        + "': "
        + json.dumps(payload, ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
