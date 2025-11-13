"""Result models for service operations.

Defines Pydantic models used as return types for service methods to
improve contracts, validation, and interoperability.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SingleChatFetchResult(BaseModel):
    """Result of fetching messages for a single chat and date range.

    Note: Some callers in the codebase may expect a dict. When needed,
    use ``model_dump()`` to convert to a plain dict without losing fields.
    """

    message_count: int = Field(0, description="How many messages were fetched")
    file_path: str = Field("", description="Path to the saved JSON with messages")
    source_id: str = Field("", description="Chat identifier (@name or numeric id)")
    dates: list[str] = Field(default_factory=list, description="Processed dates")

    checksum_sha256: Optional[str] = Field(
        None, description="Checksum of the saved JSON file (sha256)"
    )
    estimated_tokens_total: int = Field(
        0, description="Estimated total token count across messages"
    )
    first_message_ts: Optional[str] = Field(
        None, description="ISO timestamp of the first message in the collection"
    )
    last_message_ts: Optional[str] = Field(
        None, description="ISO timestamp of the last message in the collection"
    )

    summary_file_path: Optional[str] = Field(
        None, description="Path to generated summary artifact"
    )
    threads_file_path: Optional[str] = Field(
        None, description="Path to generated threads artifact"
    )
    participants_file_path: Optional[str] = Field(
        None, description="Path to generated participants artifact"
    )
