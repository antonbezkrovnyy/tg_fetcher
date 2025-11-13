"""Main entry point and CLI for Telegram Fetcher Service.

Provides both module entry point (python -m src) and a console CLI with
subcommands to run all configured chats or a single chat. Arguments override
environment-based configuration selectively.
"""

import argparse
import asyncio
import contextlib
import sys

from pydantic import ValidationError

from src.core.config import FetcherConfig
from src.di.container import Container
from src.observability.logging_config import get_logger, setup_logging


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level CLI parser with subcommands.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="tg-fetch",
        description=(
            "Telegram fetcher CLI. If no subcommand is provided, the default is 'run'."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    # run: process all chats from configuration
    run_parser = subparsers.add_parser(
        "run", help="Run fetcher for all configured chats (default)"
    )
    run_parser.add_argument(
        "--mode",
        dest="fetch_mode",
        choices=["yesterday", "full", "incremental", "continuous", "date", "range"],
        help="Fetch mode to use (overrides FETCH_MODE)",
    )
    run_parser.add_argument(
        "--date",
        dest="fetch_date",
        help="Date for mode=date in YYYY-MM-DD",
    )
    run_parser.add_argument(
        "--start",
        dest="fetch_start",
        help="Start date for mode=range in YYYY-MM-DD",
    )
    run_parser.add_argument(
        "--end",
        dest="fetch_end",
        help="End date for mode=range in YYYY-MM-DD",
    )
    run_parser.add_argument(
        "--chats",
        dest="telegram_chats",
        nargs="+",
        help="Override chat list (space-separated, e.g. @ru_python @pythonstepikchat)",
    )

    # single: process one chat optionally for a specific date
    single_parser = subparsers.add_parser(
        "single", help="Run fetcher for a single chat"
    )
    single_parser.add_argument(
        "chat",
        help="Chat identifier (e.g., @ru_python or https://t.me/ru_python)",
    )
    single_parser.add_argument(
        "--date",
        dest="date_str",
        help="Optional date in YYYY-MM-DD (defaults follow FETCH_MODE)",
    )

    # listen: long-lived worker consuming commands from Redis queue
    listen_parser = subparsers.add_parser(
        "listen", help="Listen Redis commands queue and run fetch jobs"
    )
    listen_parser.add_argument(
        "--worker-id",
        dest="worker_id",
        help="Optional worker identifier (defaults to SERVICE_NAME)",
    )
    listen_parser.add_argument(
        "--queue",
        dest="commands_queue",
        help="Override Redis commands queue name (COMMANDS_QUEUE)",
    )
    listen_parser.add_argument(
        "--timeout",
        dest="commands_blpop_timeout",
        type=int,
        help="Override BLPOP timeout in seconds (COMMANDS_BLPOP_TIMEOUT)",
    )

    return parser


def _load_config(command: str, args: argparse.Namespace) -> FetcherConfig | None:
    """Load configuration from environment and apply CLI overrides.

    Returns None if validation/loading failed (errors are printed).
    """
    try:
        overrides = {}
        if command == "run":
            overrides = {
                **{
                    k: v
                    for k, v in {
                        "fetch_mode": getattr(args, "fetch_mode", None),
                        "fetch_date": getattr(args, "fetch_date", None),
                        "fetch_start": getattr(args, "fetch_start", None),
                        "fetch_end": getattr(args, "fetch_end", None),
                        "telegram_chats": getattr(args, "telegram_chats", None),
                    }.items()
                    if v is not None
                }
            }
        elif command == "listen":
            overrides = {
                **{
                    k: v
                    for k, v in {
                        "commands_queue": getattr(args, "commands_queue", None),
                        "commands_blpop_timeout": getattr(
                            args, "commands_blpop_timeout", None
                        ),
                    }.items()
                    if v is not None
                }
            }
        config = FetcherConfig(**overrides)
        config.validate_mode_requirements()
        return config
    except ValidationError as e:  # pragma: no cover - args parsing paths
        print(f"Configuration validation error:\n{e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return None
    except Exception as e:  # pragma: no cover - unexpected env issues
        print(f"Failed to load configuration: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return None


async def _run_command(
    command: str, args: argparse.Namespace, config: FetcherConfig
) -> int:
    """Execute the selected CLI command using provided configuration."""
    # Setup logging early
    setup_logging(
        level=config.log_level,
        log_format=config.log_format,
        service_name=config.service_name,
        loki_url=config.loki_url,
    )
    logger = get_logger(__name__)

    logger.info(
        "Starting Telegram Fetcher Service",
        extra={
            "fetch_mode": config.fetch_mode,
            "chats_count": len(config.telegram_chats),
            "data_dir": str(config.data_dir),
        },
    )

    try:
        if command == "listen":
            # Long-running worker listening to Redis queue
            container = Container(config=config)
            container.initialize_runtime()
            subscriber = container.provide_command_subscriber(
                worker_id=getattr(args, "worker_id", None)
            )
            subscriber.connect()
            try:
                await subscriber.listen()
            finally:
                # Ensure proper disconnect on exit
                with contextlib.suppress(Exception):
                    subscriber.stop()
                with contextlib.suppress(Exception):
                    subscriber.disconnect()
        else:
            # Local import to keep CLI type-check lightweight
            from src.services.fetcher_service import FetcherService as _FetcherService

            service = _FetcherService(config)
            if command == "single":
                result = await service.fetch_single_chat(
                    chat_identifier=args.chat,
                    date_str=getattr(args, "date_str", None),
                )
                logger.info(
                    "Single chat fetch completed",
                    extra={
                        "chat": args.chat,
                        "message_count": result.get("message_count", 0),
                    },
                )
            else:
                await service.run()

        logger.info("Fetcher service completed successfully")

        # Optionally push metrics to Pushgateway for one-shot runs
        try:
            if (
                config.enable_metrics
                and config.pushgateway_url
                and config.metrics_mode in ("push", "both")
                and command != "listen"
            ):
                import os

                from prometheus_client import REGISTRY, push_to_gateway

                instance = os.getenv("HOSTNAME", "fetcher-1")
                # Push default registry as is; group by job and instance
                push_to_gateway(
                    config.pushgateway_url.replace("http://", "").replace(
                        "https://", ""
                    ),
                    job=config.service_name,
                    registry=REGISTRY,
                    grouping_key={"instance": instance},
                )
                logger.info(
                    "Metrics pushed to Pushgateway",
                    extra={
                        "pushgateway_url": config.pushgateway_url,
                        "instance": instance,
                    },
                )
        except Exception:
            logger.debug("Metrics push failed (non-fatal)", exc_info=True)
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 0
    except Exception as e:
        logger.exception(f"Fatal error in fetcher service: {e}")
        return 1


async def main(argv: list[str] | None = None) -> int:
    """Main application entry point with CLI support.

    Args:
        argv: Optional list of arguments to parse; defaults to sys.argv[1:]

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Determine subcommand; default to 'run' if none
    command = args.command or "run"

    config = _load_config(command, args)
    if config is None:
        return 1

    return await _run_command(command, args, config)


def cli() -> None:
    """Synchronous CLI entrypoint for console_scripts.

    Wraps the async main() to integrate with setuptools/PEP 621 scripts.
    """
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
