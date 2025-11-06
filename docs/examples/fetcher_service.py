"""
Unified FetcherService class that consolidates logic from fetcher.py and fetch_yesterday.py.

This module implements the Strategy pattern to handle different fetching modes:
- Continuous fetching (from last processed date to today)
- Yesterday-only fetching (just previous day)
"""

import os
import json
import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, UTC, date
from pathlib import Path
from typing import List, Optional, Dict, Any
from telethon import TelegramClient

from config import FetcherConfig, FetchMode
from fetcher_utils import prepare_message, build_output_path, save_json
from retry_utils import retry_on_error_enhanced, RateLimiter

# Use common observability module
from common_observability import StandardMetrics, get_logger_safe, setup_logging_safe, OBSERVABILITY_AVAILABLE
from session_manager import SessionManager


def load_progress(progress_file: Path) -> Dict[str, str]:
    """Load progress data from file."""
    if not progress_file.exists():
        return {}

    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_progress(progress_file: Path, progress_data: Dict[str, str]) -> None:
    """Save progress data to file."""
    progress_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Warning: Could not save progress: {e}")


class FetchStrategy(ABC):
    """Abstract base class for different fetching strategies."""

    def __init__(self, service: 'FetcherService'):
        self.service = service

    @abstractmethod
    async def get_dates_to_fetch(self, channel: str) -> List[date]:
        """Get list of dates that need to be fetched for the channel."""
        pass

    @abstractmethod
    async def run(self) -> None:
        """Execute the fetching strategy."""
        pass


class ContinuousFetchStrategy(FetchStrategy):
    """Strategy for continuous fetching from last processed date to today."""

    async def get_dates_to_fetch(self, channel: str) -> List[date]:
        """Calculate dates from last processed to today."""
        progress_data = load_progress(self.service.config.progress_file)

        # Get last processed date
        last_date_str = progress_data.get(channel)
        if last_date_str:
            last_date = datetime.fromisoformat(last_date_str).date()
            start_date = last_date + timedelta(days=1)
        else:
            # If no progress, start from a reasonable default (e.g., 30 days ago)
            start_date = datetime.now(UTC).date() - timedelta(days=30)

        # Fetch up to today
        end_date = datetime.now(UTC).date()

        dates = []
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)

        return dates

    async def run(self) -> None:
        """Execute continuous fetching for all channels."""
        async with self.service.create_client() as client:
            await client.start()

            for channel in self.service.config.chats:
                print(f"\n=== Processing {channel} ===")

                dates_to_fetch = await self.get_dates_to_fetch(channel)

                for fetch_date in dates_to_fetch:
                    try:
                        messages_count = await self.service.fetch_day(client, channel, fetch_date)

                        # Update progress
                        progress_data = load_progress(self.service.config.progress_file)
                        progress_data[channel] = fetch_date.isoformat()
                        save_progress(self.service.config.progress_file, progress_data)

                        # Record metrics
                        self.service.metrics.record_messages_fetched(channel, messages_count)

                    except Exception as e:
                        print(f"Error processing {channel} for {fetch_date}: {e}")
                        self.service.metrics.record_fetch_error(channel, type(e).__name__)
                        continue


class YesterdayFetchStrategy(FetchStrategy):
    """Strategy for fetching only yesterday's messages."""

    async def get_dates_to_fetch(self, channel: str) -> List[date]:
        """Return only yesterday's date."""
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        return [yesterday]

    async def run(self) -> None:
        """Execute yesterday-only fetching for all channels."""
        async with self.service.create_client() as client:
            await client.start()

            yesterday = datetime.now(UTC).date() - timedelta(days=1)

            for channel in self.service.config.chats:
                print(f"\n=== Processing {channel} for {yesterday} ===")

                try:
                    messages_count = await self.service.fetch_day(client, channel, yesterday)

                    # Record metrics
                    self.service.metrics.record_messages_fetched(channel, messages_count)
                    self.service.metrics.record_channel_processed()

                    print(f"✓ Processed {channel}: {messages_count} messages")

                except Exception as e:
                    print(f"✗ Error processing {channel}: {e}")
                    self.service.metrics.record_fetch_error(channel, type(e).__name__)
                    continue


class FetcherService:
    """Unified service for fetching Telegram messages with different strategies."""

    def __init__(self, config: FetcherConfig):
        self.config = config
        self.data_dir = config.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metrics using standard metrics
        self.metrics = StandardMetrics()

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(calls_per_second=config.rate_limit.calls_per_second)

        # Setup logging and session manager
        setup_logging_safe()
        self.logger = get_logger_safe(__name__)
        self.session_manager = SessionManager(config)

    def create_client(self) -> TelegramClient:
        """Create and configure Telegram client."""
        return self.session_manager.create_client()

    def _get_fetch_strategy(self) -> FetchStrategy:
        """Get appropriate fetch strategy based on configuration."""
        if self.config.fetch_mode == FetchMode.CONTINUOUS:
            return ContinuousFetchStrategy(self)
        elif self.config.fetch_mode == FetchMode.YESTERDAY_ONLY:
            return YesterdayFetchStrategy(self)
        else:
            # Default to continuous
            return ContinuousFetchStrategy(self)

    @retry_on_error_enhanced(max_attempts=3, backoff_factor=2.0)
    async def fetch_day(self, client: TelegramClient, channel_username: str, day_date: date) -> int:
        """Fetch messages from a single day for a channel/chat and save them into a JSON file.

        Args:
            client: Telegram client
            channel_username: Channel/chat username or ID
            day_date: Date to fetch messages for

        Returns:
            Number of messages saved
        """
        start_time = time.time()
        self.logger.info(f"Fetching {channel_username} for {day_date.isoformat()}")

        try:
            # Apply rate limiting
            await self.rate_limiter.acquire()

            # Get entity
            entity = await client.get_entity(channel_username)

            # Set up date range
            start = datetime(day_date.year, day_date.month, day_date.day, tzinfo=UTC)
            end = start + timedelta(days=1)

            messages = []
            senders = {}

            # Fetch messages
            async for msg in client.iter_messages(entity, offset_date=end, reverse=False):
                if not getattr(msg, 'date', None):
                    continue

                msg_date = msg.date
                if msg_date >= end:
                    continue
                if msg_date < start:
                    break

                # Track senders
                if getattr(msg, 'sender', None) and getattr(msg.sender, 'id', None):
                    sender_id = msg.sender.id
                    sender_name = (
                        getattr(msg.sender, 'first_name', '') or
                        getattr(msg.sender, 'title', '') or
                        'Unknown User'
                    )
                    senders[sender_id] = sender_name

                # Prepare and collect message
                processed_msg = prepare_message(msg, senders)
                if processed_msg:
                    messages.append(processed_msg)

            # Save results - build path manually with specific date
            safe_name = channel_username.lstrip('@')
            if any(kw in channel_username for kw in ("chat", "beginners")):
                output_dir = self.data_dir / "chats"
            else:
                output_dir = self.data_dir / "channels"

            channel_dir = output_dir / safe_name
            channel_dir.mkdir(parents=True, exist_ok=True)
            output_path = channel_dir / f"{day_date.isoformat()}.json"

            save_json(output_path, messages)

            # Record metrics
            duration = time.time() - start_time
            self.metrics.record_fetch_duration(channel_username, duration)

            self.logger.info(
                f"  → Saved {len(messages)} messages to {output_path.relative_to(self.data_dir)}"
            )

            return len(messages)

        except Exception as e:
            self.logger.error(f"Error fetching {channel_username} for {day_date}: {e}")
            self.metrics.record_fetch_error(channel_username, type(e).__name__)
            raise

    async def run(self) -> None:
        """Run the fetcher service using the configured strategy."""
        strategy = self._get_fetch_strategy()
        await strategy.run()