"""
Configuration management for Fetcher Service.

This module provides a comprehensive configuration system with:
- Environment variable loading
- Configuration file support
- Validation and type checking
- Default values and constants
- Path expansion and sanitization
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class FetchMode(Enum):
    """Available fetch modes."""
    YESTERDAY = "yesterday"
    YESTERDAY_ONLY = "yesterday"  # Alias for backward compatibility
    FULL = "full"
    INCREMENTAL = "incremental"
    CONTINUOUS = "continuous"
    CUSTOM_DATE = "date"        # Single specific date
    DATE_RANGE = "range"        # Date range

    @classmethod
    def is_valid(cls, mode: str) -> bool:
        """Check if mode is valid."""
        return mode in [item.value for item in cls]


# Default paths
DEFAULT_DATA_DIR = "/data"
DEFAULT_SESSION_DIR = "/sessions"
DEFAULT_PROGRESS_FILE = "progress.json"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    calls_per_second: float = 10.0
    burst_size: int = 5
    window_size: int = 60

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.calls_per_second <= 0:
            raise ValueError("calls_per_second must be positive")
        if self.burst_size <= 0:
            raise ValueError("burst_size must be positive")
        if self.window_size <= 0:
            raise ValueError("window_size must be positive")


@dataclass
class FetcherConfig:
    """Main configuration class for Fetcher Service."""

    # Required fields
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    chats: List[str] = field(default_factory=list)

    # Paths
    data_dir: Path = field(default_factory=lambda: Path(DEFAULT_DATA_DIR))
    session_dir: Path = field(default_factory=lambda: Path(DEFAULT_SESSION_DIR))
    session_name: str = "telegram_session"

    @property
    def progress_file(self) -> Path:
        """Get the progress file path."""
        return self.data_dir / "progress.json"

    # Retry and performance
    max_retries: int = 3
    retry_delay: float = 1.0
    concurrent_channels: int = 1

    # Rate limiting
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)

    # Fetch mode
    fetch_mode: str = FetchMode.YESTERDAY.value

    def __post_init__(self):
        """Validate and process configuration after initialization."""
        self._validate_required_fields()
        self._validate_ranges()
        self._process_paths()
        self._sanitize_chats()

    def _validate_required_fields(self):
        """Validate required configuration fields."""
        if self.api_id is None or self.api_id == 0:
            raise ConfigValidationError("api_id is required and must be non-zero")

        if not self.api_hash or not self.api_hash.strip():
            raise ConfigValidationError("api_hash is required and cannot be empty")

        if not self.chats:
            raise ConfigValidationError("at least one chat must be specified")

    def _validate_ranges(self):
        """Validate configuration value ranges."""
        if not (1 <= self.max_retries <= 10):
            raise ConfigValidationError("max_retries must be between 1 and 10")

        if not (0.1 <= self.retry_delay <= 300.0):
            raise ConfigValidationError("retry_delay must be between 0.1 and 300 seconds")

        if not (1 <= self.concurrent_channels <= 20):
            raise ConfigValidationError("concurrent_channels must be between 1 and 20")

    def _process_paths(self):
        """Expand and validate paths."""
        # Expand user home directory if needed
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir).expanduser()
        if isinstance(self.session_dir, str):
            self.session_dir = Path(self.session_dir).expanduser()

        # Ensure paths are Path objects
        if not isinstance(self.data_dir, Path):
            self.data_dir = Path(self.data_dir)
        if not isinstance(self.session_dir, Path):
            self.session_dir = Path(self.session_dir)

    def _sanitize_chats(self):
        """Clean up and validate chat list."""
        sanitized = []
        for chat in self.chats:
            if isinstance(chat, str):
                # Remove @ prefix and whitespace
                clean_chat = chat.strip().lstrip('@')
                if clean_chat:  # Only add non-empty chats
                    sanitized.append(clean_chat)

        self.chats = sanitized

        # Re-validate after sanitization
        if not self.chats:
            raise ConfigValidationError("at least one valid chat must be specified after sanitization")

    @classmethod
    def from_env(cls) -> 'FetcherConfig':
        """Create configuration from environment variables."""
        # Parse chats list
        chats_str = os.getenv('CHATS', '')
        chats = [c.strip() for c in chats_str.split(',') if c.strip()]

        # Parse rate limit config
        rate_limit = RateLimitConfig(
            calls_per_second=float(os.getenv('RATE_LIMIT_CALLS_PER_SECOND', '10.0')),
            burst_size=int(os.getenv('RATE_LIMIT_BURST_SIZE', '5')),
            window_size=int(os.getenv('RATE_LIMIT_WINDOW_SIZE', '60'))
        )

        return cls(
            api_id=int(os.getenv('API_ID', '0')) if os.getenv('API_ID') else None,
            api_hash=os.getenv('API_HASH'),
            chats=chats,
            data_dir=os.getenv('DATA_DIR', DEFAULT_DATA_DIR),
            session_dir=os.getenv('SESSION_DIR', DEFAULT_SESSION_DIR),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('RETRY_DELAY', '1.0')),
            concurrent_channels=int(os.getenv('CONCURRENT_CHANNELS', '1')),
            rate_limit=rate_limit,
            fetch_mode=os.getenv('FETCH_MODE', FetchMode.YESTERDAY.value)
        )

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> 'FetcherConfig':
        """Create configuration from JSON file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in config file: {e}")

        # Handle rate limit config
        rate_limit_data = data.pop('rate_limit', {})
        rate_limit = RateLimitConfig(**rate_limit_data)

        return cls(rate_limit=rate_limit, **data)

    @classmethod
    def from_file_with_env_override(cls, config_path: Union[str, Path]) -> 'FetcherConfig':
        """Create configuration from file with environment variable overrides."""
        # Start with file config
        config = cls.from_file(config_path)

        # Override with environment variables if they exist
        if os.getenv('API_ID'):
            config.api_id = int(os.getenv('API_ID'))

        if os.getenv('API_HASH'):
            config.api_hash = os.getenv('API_HASH')

        if os.getenv('CHATS'):
            chats_str = os.getenv('CHATS')
            config.chats = [c.strip() for c in chats_str.split(',') if c.strip()]

        if os.getenv('DATA_DIR'):
            config.data_dir = Path(os.getenv('DATA_DIR'))

        if os.getenv('SESSION_DIR'):
            config.session_dir = Path(os.getenv('SESSION_DIR'))

        if os.getenv('MAX_RETRIES'):
            config.max_retries = int(os.getenv('MAX_RETRIES'))

        if os.getenv('RETRY_DELAY'):
            config.retry_delay = float(os.getenv('RETRY_DELAY'))

        if os.getenv('CONCURRENT_CHANNELS'):
            config.concurrent_channels = int(os.getenv('CONCURRENT_CHANNELS'))

        # Re-validate after overrides
        config.__post_init__()

        return config


def load_config() -> FetcherConfig:
    """Load configuration from the best available source."""

    # Check for config file path in environment
    config_file = os.getenv('FETCHER_CONFIG_FILE')

    if config_file and Path(config_file).exists():
        # Load from file with env overrides
        return FetcherConfig.from_file_with_env_override(config_file)

    # Check for standard config file locations
    standard_locations = [
        Path('fetcher.json'),
        Path('config/fetcher.json'),
        Path('/etc/fetcher/config.json'),
        Path.home() / '.config' / 'fetcher.json'
    ]

    for location in standard_locations:
        if location.exists():
            return FetcherConfig.from_file_with_env_override(location)

    # Fallback to environment variables only
    return FetcherConfig.from_env()


def create_example_config(output_path: Union[str, Path]) -> None:
    """Create an example configuration file."""
    example_config = {
        "api_id": 12345,
        "api_hash": "your_api_hash_here",
        "chats": ["channel1", "channel2", "@channel3"],
        "data_dir": "/data",
        "session_dir": "/sessions",
        "max_retries": 3,
        "retry_delay": 1.0,
        "concurrent_channels": 2,
        "fetch_mode": "yesterday",
        "rate_limit": {
            "calls_per_second": 5.0,
            "burst_size": 3,
            "window_size": 60
        }
    }

    output_path = Path(output_path)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(example_config, f, indent=2, ensure_ascii=False)

    print(f"Example configuration created at: {output_path}")


if __name__ == "__main__":
    # CLI interface for creating example config
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "create-example":
        output = sys.argv[2] if len(sys.argv) > 2 else "fetcher.example.json"
        create_example_config(output)
    else:
        # Test configuration loading
        try:
            config = load_config()
            print("Configuration loaded successfully:")
            print(f"  API ID: {config.api_id}")
            print(f"  Chats: {config.chats}")
            print(f"  Data dir: {config.data_dir}")
            print(f"  Max retries: {config.max_retries}")
        except Exception as e:
            print(f"Configuration error: {e}")
            sys.exit(1)