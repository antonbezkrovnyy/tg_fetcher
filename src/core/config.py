"""Configuration management using Pydantic BaseSettings.

This module provides strongly-typed configuration with automatic validation
and environment variable loading.
"""

from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FetcherConfig(BaseSettings):
    """Fetcher service configuration with Pydantic validation.

    All settings are loaded from environment variables with type validation
    and custom validators for complex fields.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # === Required Telegram Credentials ===
    telegram_api_id: int = Field(
        ..., description="Telegram API ID from https://my.telegram.org/apps"
    )
    telegram_api_hash: str = Field(
        ...,
        min_length=32,
        max_length=32,
        description="Telegram API Hash (32 characters)",
    )
    telegram_phone: str = Field(
        ...,
        pattern=r"^\+\d{10,15}$",
        description="Phone number in international format (+1234567890)",
    )

    # === Required Sources ===
    telegram_chats: list[str] = Field(
        ..., description="Comma-separated list of channels/chats to fetch from"
    )

    # === Fetch Mode ===
    fetch_mode: str = Field(
        default="yesterday",
        pattern=r"^(yesterday|full|incremental|continuous|date|range)$",
        description="Fetch mode: yesterday, full, incremental, continuous, date, range",
    )

    # === Mode-specific dates ===
    fetch_date: Optional[date] = Field(
        default=None, description="Specific date for fetch_mode=date (YYYY-MM-DD)"
    )
    fetch_start: Optional[date] = Field(
        default=None, description="Start date for fetch_mode=range (YYYY-MM-DD)"
    )
    fetch_end: Optional[date] = Field(
        default=None, description="End date for fetch_mode=range (YYYY-MM-DD)"
    )

    # === Paths ===
    data_dir: Path = Field(
        default=Path("./data"), description="Directory for storing fetched messages"
    )
    session_dir: Path = Field(
        default=Path("./sessions"), description="Directory for Telegram session files"
    )
    progress_file: Path = Field(
        default=Path("data/progress.json"),
        description="File for tracking fetch progress",
    )

    # === Optional: Multiple Credentials (Future) ===
    telegram_credentials_dir: Optional[Path] = Field(
        default=None,
        description="Directory with multiple credential files for rotation",
    )

    # === Rate Limiting ===
    rate_limit_calls_per_sec: float = Field(
        default=10.0, ge=0.1, le=100.0, description="API calls per second limit"
    )
    max_parallel_channels: int = Field(
        default=3, ge=1, le=10, description="Maximum channels to process in parallel"
    )

    # === Per-Chat Concurrency ===
    fetch_concurrency_per_chat: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum parallel date ranges per chat",
    )

    # === Retry Settings ===
    max_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed operations",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Exponential backoff factor for retries",
    )

    # === Progress Reset ===
    progress_reset: bool = Field(
        default=False, description="Reset all progress and start from scratch"
    )

    # === Force Refetch ===
    force_refetch: bool = Field(
        default=False,
        description="Force re-fetching even if data already exists (ignores progress)",
    )

    # === Progress Events ===
    enable_progress_events: bool = Field(
        default=True, description="Enable Redis progress events publishing"
    )
    # === Final/Stage Events ===
    enable_events: bool = Field(
        default=True,
        description=("Enable publishing of start/complete/failed/skipped/stage events"),
    )
    progress_interval: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Publish progress event every N processed messages",
    )

    # === Preprocessing Feature Flags ===
    link_normalize_enabled: bool = Field(
        default=True,
        description="Enable URL extraction and normalization for messages",
    )
    token_estimate_enabled: bool = Field(
        default=True,
        description="Enable token count estimation for messages",
    )
    merge_short_messages_enabled: bool = Field(
        default=True,
        description=(
            "Enable merging of consecutive short messages from the same sender"
        ),
    )
    merge_short_messages_max_length: int = Field(
        default=120,
        ge=10,
        le=1000,
        description="Maximum length of a message to qualify for merge",
    )
    merge_short_messages_max_gap_seconds: int = Field(
        default=90,
        ge=5,
        le=3600,
        description="Maximum time gap in seconds between messages to allow merge",
    )
    message_classifier_enabled: bool = Field(
        default=True, description="Enable rule-based message_type classification"
    )
    language_detect_enabled: bool = Field(
        default=True, description="Enable lightweight language detection (ru/en/other)"
    )

    # === Deduplication ===
    dedup_in_run_enabled: bool = Field(
        default=False,
        description=(
            "Enable deduplication within a single run "
            "(skip duplicate message IDs encountered in the same execution). "
            "Cross-run idempotency via last_processed_id always applies."
        ),
    )

    # === Telegram Discussions / Comments ===
    comments_limit_per_message: int = Field(
        default=50,
        ge=0,
        le=1000,
        description=(
            "Max number of discussion comments to fetch per channel post; "
            "0 disables comments fetching"
        ),
    )

    # === Logging ===
    log_level: str = Field(
        default="INFO",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )
    log_format: str = Field(
        default="json",
        pattern=r"^(json|text)$",
        description="Log output format: json or text",
    )

    # === Observability ===
    enable_metrics: bool = Field(
        default=True, description="Enable Prometheus metrics export"
    )
    metrics_port: int = Field(
        default=9090, ge=1024, le=65535, description="Port for metrics HTTP server"
    )
    metrics_mode: str = Field(
        default="scrape",
        pattern=r"^(scrape|push|both)$",
        description=(
            "How to expose metrics: scrape via HTTP, push to Pushgateway, or both"
        ),
    )
    loki_url: Optional[str] = Field(
        default=None, description="Loki URL for log shipping (e.g., http://loki:3100)"
    )
    pushgateway_url: Optional[str] = Field(
        default=None,
        description="Prometheus Pushgateway URL (e.g., http://pushgateway:9091)",
    )

    # === Events Bus (Redis Pub/Sub) ===
    events_channel: str = Field(
        default="tg_events",
        description="Redis Pub/Sub channel name for fetcher events",
    )
    service_name: str = Field(
        default="tg_fetcher",
        description="Service name to include in emitted events/metrics",
    )

    # === Redis (for PubSub and queue) ===
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL (redis://host:port)",
    )
    redis_password: Optional[str] = Field(
        default=None, description="Redis password (if required)"
    )

    # === Redis Commands Queue (BLPOP) ===
    commands_queue: str = Field(
        default="tg_commands", description="Redis list name for commands queue"
    )
    commands_blpop_timeout: int = Field(
        default=5,
        ge=1,
        le=3600,
        description="Default BLPOP timeout in seconds for command subscriber",
    )

    # === Schema / Versioning ===
    data_schema_version: str = Field(
        default="1.0", description="Version string for stored data schema"
    )
    progress_schema_version: str = Field(
        default="1.0", description="Version string for progress file schema"
    )
    preprocessing_version: str = Field(
        default="1", description="Preprocessing pipeline version label"
    )

    # === Storage Backend ===
    storage_backend: str = Field(
        default="fs",
        pattern=r"^(fs|mongo)$",
        description="Storage backend to use for message persistence: fs or mongo",
    )
    mongo_url: Optional[str] = Field(
        default=None,
        description="MongoDB connection string (e.g., mongodb://localhost:27017)",
    )
    mongo_db: Optional[str] = Field(
        default=None, description="MongoDB database name for message storage"
    )
    mongo_collection: Optional[str] = Field(
        default=None, description="MongoDB collection name for messages"
    )

    @field_validator("fetch_date", "fetch_start", "fetch_end", mode="before")
    @classmethod
    def parse_date_fields(cls, v: str | date | None) -> date | None:
        """Parse date from string format YYYY-MM-DD."""
        if v is None or isinstance(v, date):
            return v
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError as e:
                raise ValueError(f"Invalid date format, expected YYYY-MM-DD: {e}")
        raise ValueError("Date must be string in YYYY-MM-DD format or date object")

    @field_validator("data_dir", "session_dir", mode="after")
    @classmethod
    def ensure_directories_exist(cls, v: Path) -> Path:
        """Create directories if they don't exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    def validate_mode_requirements(self) -> None:
        """Validate mode-specific requirements.

        Raises:
            ValueError: If mode requirements are not met
        """
        if self.fetch_mode == "date" and self.fetch_date is None:
            raise ValueError("fetch_date is required when fetch_mode=date")

        if self.fetch_mode == "range":
            if self.fetch_start is None or self.fetch_end is None:
                raise ValueError(
                    "fetch_start and fetch_end are required when fetch_mode=range"
                )
            if self.fetch_start > self.fetch_end:
                raise ValueError("fetch_start must be before or equal to fetch_end")

    def get_session_file(self, phone: str) -> Path:
        """Get session file path for a phone number.

        Args:
            phone: Phone number in international format

        Returns:
            Path to session file
        """
        # Remove + and create safe filename
        safe_phone = phone.replace("+", "")
        return self.session_dir / f"session_{safe_phone}.session"
