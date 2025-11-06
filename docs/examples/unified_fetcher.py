#!/usr/bin/env python3
"""
Unified Telegram Fetcher
Replaces both fetcher.py and fetch_yesterday.py with a single, configurable script.
"""

import argparse
import asyncio
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fetcher_service import FetcherService

from config import FetchMode, load_config


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified Telegram message fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode yesterday              # Fetch only yesterday's messages
  %(prog)s --mode continuous             # Fetch from last checkpoint to today
  %(prog)s --mode date --date 2024-01-01 # Fetch specific date
  %(prog)s --mode range --from 2024-01-01 --to 2024-01-31  # Fetch date range
  %(prog)s --channels channel1,channel2  # Override config channels
        """,
    )

    # Mode selection
    parser.add_argument(
        "--mode",
        choices=["yesterday", "continuous", "date", "range"],
        default="continuous",
        help="Fetch mode (default: continuous)",
    )

    # Date options
    parser.add_argument(
        "--date",
        type=str,
        help="Specific date to fetch (YYYY-MM-DD, requires --mode date)",
    )

    parser.add_argument(
        "--from",
        dest="date_from",
        type=str,
        help="Start date for range (YYYY-MM-DD, requires --mode range)",
    )

    parser.add_argument(
        "--to",
        dest="date_to",
        type=str,
        help="End date for range (YYYY-MM-DD, requires --mode range)",
    )

    # Channel override
    parser.add_argument(
        "--channels",
        type=str,
        help="Comma-separated list of channels to fetch (overrides config)",
    )

    # Config file
    parser.add_argument(
        "--config",
        type=str,
        help="Path to config file (default: use environment/defaults)",
    )

    # Dry run
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without actually doing it",
    )

    # Verbose
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    return parser.parse_args()


def validate_arguments(args):
    """Validate command line arguments."""
    if args.mode == "date" and not args.date:
        sys.stderr.write("Error: --date is required when using --mode date\n")
        return False

    if args.mode == "range":
        if not args.date_from or not args.date_to:
            sys.stderr.write(
                "Error: --from and --to are required when using --mode range\n"
            )
            return False

    # Validate date formats
    for date_str, name in [
        (args.date, "date"),
        (args.date_from, "from"),
        (args.date_to, "to"),
    ]:
        if date_str:
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                sys.stderr.write(f"Error: Invalid {name} format. Use YYYY-MM-DD\n")
                return False

    return True


async def main():
    """Main entry point with unified functionality."""
    args = parse_arguments()

    if not validate_arguments(args):
        return 1

    try:
        # Load configuration
        config = load_config(args.config if args.config else None)

        # Override channels if specified
        if args.channels:
            config.chats = [ch.strip() for ch in args.channels.split(",") if ch.strip()]

        # Configure mode based on arguments
        if args.mode == "yesterday":
            config.fetch_mode = FetchMode.YESTERDAY_ONLY.value

        elif args.mode == "continuous":
            config.fetch_mode = FetchMode.CONTINUOUS.value

        elif args.mode == "date":
            # Special single-date mode
            config.fetch_mode = (
                FetchMode.CUSTOM_DATE.value
                if hasattr(FetchMode, "CUSTOM_DATE")
                else "date"
            )
            config.target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

        elif args.mode == "range":
            # Special date range mode
            config.fetch_mode = (
                FetchMode.DATE_RANGE.value
                if hasattr(FetchMode, "DATE_RANGE")
                else "range"
            )
            config.date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
            config.date_to = datetime.strptime(args.date_to, "%Y-%m-%d").date()

        # Show configuration
        print(f"🚀 Unified Telegram Fetcher")
        print(f"Mode: {args.mode}")
        print(f"Channels: {', '.join(config.chats)}")
        print(f"Data directory: {config.data_dir}")

        if args.dry_run:
            print(f"\n📋 DRY RUN - Would fetch:")

            # Show what dates would be processed
            if args.mode == "yesterday":
                yesterday = datetime.now(UTC).date() - timedelta(days=1)
                print(f"  • Date: {yesterday}")
            elif args.mode == "date":
                print(f"  • Date: {args.date}")
            elif args.mode == "range":
                print(f"  • Range: {args.date_from} to {args.date_to}")
            elif args.mode == "continuous":
                print(f"  • From last checkpoint to today")

            print(f"  • Channels: {len(config.chats)} total")
            for ch in config.chats:
                print(f"    - {ch}")

            print(f"\nUse without --dry-run to actually fetch messages.")
            return 0

        # Create and run service
        service = FetcherService(config)
        await service.run()

        print(f"\n✅ Fetching completed successfully!")

    except KeyboardInterrupt:
        print(f"\n⚠️  Fetching interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Error during fetching: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
