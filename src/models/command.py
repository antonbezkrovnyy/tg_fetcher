"""Fetch command models for Redis queue-based processing.

This module defines strongly-typed command models for validating
and processing fetch requests from Redis queues.
"""

import uuid
from datetime import date as Date
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class FetchMode(str, Enum):
    """Supported fetch modes."""

    DATE = "date"
    DAYS = "days"
    RANGE = "range"


class FetchStrategy(str, Enum):
    """Fetch execution strategies."""

    BATCH = "batch"  # Fetch all at once
    PER_DAY = "per_day"  # Fetch day by day


class FetchCommand(BaseModel):
    """Validated fetch command from Redis queue.

    Supports three modes:
    - date: Fetch specific date
    - days: Fetch N days back from today
    - range: Fetch date range (from...to)

    Examples:
        {"command":"fetch","chat":"@ru_python","mode":"date","date":"2025-11-07"}
        {"command":"fetch","chat":"@ru_python","mode":"days","days":7}
        {"command":"fetch","chat":"@ru_python","mode":"range","from":"2025-11-01","to":"2025-11-07"}
        {"command":"fetch","chat":"@ru_python","mode":"date","date":"2025-11-07","force":true}
    """

    command: str = Field(
        ..., pattern=r"^fetch$", description="Command type (must be 'fetch')"
    )
    chat: str = Field(
        ...,
        min_length=1,
        description="Chat identifier (e.g., @channel_name or username)",
    )
    mode: FetchMode = Field(..., description="Fetch mode: date, days, or range")

    # Mode-specific fields
    date: Optional[Date] = Field(
        default=None, description="Target date for mode=date (YYYY-MM-DD)"
    )
    days: Optional[int] = Field(
        default=None, ge=1, le=365, description="Number of days back for mode=days"
    )
    from_date: Optional[Date] = Field(
        default=None, alias="from", description="Start date for mode=range (YYYY-MM-DD)"
    )
    to_date: Optional[Date] = Field(
        default=None, alias="to", description="End date for mode=range (YYYY-MM-DD)"
    )

    # Optional parameters
    strategy: FetchStrategy = Field(
        default=FetchStrategy.BATCH, description="Execution strategy"
    )
    force: bool = Field(
        default=False,
        description="Force re-fetch even if data exists (ignores progress)",
    )
    limit: Optional[int] = Field(
        default=None, ge=1, description="Optional message limit for testing"
    )

    # Internal tracking
    command_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique command ID"
    )

    @model_validator(mode="after")
    def validate_mode_specific_fields(self) -> "FetchCommand":
        """Validate that mode-specific fields are provided."""
        if self.mode == FetchMode.DATE:
            if self.date is None:
                raise ValueError("mode=date requires 'date' field")
        elif self.mode == FetchMode.DAYS:
            if self.days is None:
                raise ValueError("mode=days requires 'days' field")
        elif self.mode == FetchMode.RANGE:
            if self.from_date is None or self.to_date is None:
                raise ValueError("mode=range requires both 'from' and 'to' fields")
            if self.from_date > self.to_date:
                raise ValueError("'from' date must be <= 'to' date")

        return self

    @field_validator("chat")
    @classmethod
    def normalize_chat(cls, v: str) -> str:
        """Normalize chat identifier (ensure @ prefix for usernames)."""
        v = v.strip()
        # Don't add @ to numeric IDs or negative IDs
        if v and not v.startswith("@") and not v.startswith("http"):
            # Check if it's a numeric ID (possibly negative)
            if v.lstrip('-').isdigit():
                return v
            return f"@{v}"
        return v

    def expand_dates(self) -> list[Date]:
        """Expand command into list of target dates.

        Returns:
            List of dates to fetch, sorted chronologically

        Raises:
            ValueError: If mode is invalid or required fields are missing
        """
        if self.mode == FetchMode.DATE:
            if self.date is None:
                raise ValueError("mode=date requires 'date' field")
            return [self.date]

        elif self.mode == FetchMode.DAYS:
            if self.days is None:
                raise ValueError("mode=days requires 'days' field")
            today = datetime.now().date()
            return [today - timedelta(days=i) for i in range(1, self.days + 1)]

        elif self.mode == FetchMode.RANGE:
            if self.from_date is None or self.to_date is None:
                raise ValueError("mode=range requires both 'from' and 'to' fields")

            dates = []
            current = self.from_date
            while current <= self.to_date:
                dates.append(current)
                current += timedelta(days=1)
            return dates

        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def get_output_path(self, base_dir: str, target_date: Date) -> str:
        """Generate output file path for given date.

        Args:
            base_dir: Base data directory
            target_date: Target date

        Returns:
            Path in format: base_dir/chat/YYYY/discussions_YYYY-MM-DD.json
        """
        chat_name = self.chat.lstrip("@")
        year = target_date.year
        filename = f"discussions_{target_date.isoformat()}.json"
        return f"{base_dir}/{chat_name}/{year}/{filename}"

    def to_event_params(self) -> dict[str, Any]:
        """Convert command to event parameters dict.

        Returns:
            Dictionary suitable for event publishing
        """
        params: dict[str, Any] = {
            "mode": self.mode.value,
            "strategy": self.strategy.value,
            "force": self.force,
        }

        if self.mode == FetchMode.DATE and self.date:
            params["date"] = self.date.isoformat()
        elif self.mode == FetchMode.DAYS and self.days:
            params["days"] = self.days
        elif self.mode == FetchMode.RANGE:
            if self.from_date and self.to_date:
                params["from"] = self.from_date.isoformat()
                params["to"] = self.to_date.isoformat()

        if self.limit:
            params["limit"] = self.limit

        return params

    class Config:
        """Pydantic configuration."""

        populate_by_name = True  # Allow both 'from' and 'from_date'
