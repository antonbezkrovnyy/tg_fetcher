"""MessagePreprocessor module.

Encapsulates message enrichment (links, tokens, classification, language)
and short-message merge policy.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from src.models.schemas import Message


class MessagePreprocessor:
    """Encapsulates message enrichment and merge policy.

    Responsibilities:
    - Link normalization (delegated)
    - Token estimate
    - Message classification
    - Language detection
    - Short-message merge policy

    Delegates to provided callables to avoid duplication during initial extraction.
    """

    def __init__(
        self,
        *,
        link_normalize_enabled: bool,
        token_estimate_enabled: bool,
        message_classifier_enabled: bool,
        language_detect_enabled: bool,
        merge_short_messages_enabled: bool,
        merge_short_messages_max_length: int,
        merge_short_messages_max_gap_seconds: int,
        # Delegates from FetcherService for now
        normalize_url_fn: Callable[[str], str],
        estimate_tokens_fn: Callable[[str], int],
        classify_message_fn: Callable[[str, Message, Any], str],
        detect_language_fn: Callable[[str], str],
    ) -> None:
        """Initialize preprocessor with feature flags and delegate functions."""
        self.link_normalize_enabled = link_normalize_enabled
        self.token_estimate_enabled = token_estimate_enabled
        self.message_classifier_enabled = message_classifier_enabled
        self.language_detect_enabled = language_detect_enabled
        self.merge_short_messages_enabled = merge_short_messages_enabled
        self.merge_short_messages_max_length = merge_short_messages_max_length
        self.merge_short_messages_max_gap_seconds = merge_short_messages_max_gap_seconds
        self._normalize_url = normalize_url_fn
        self._estimate_tokens = estimate_tokens_fn
        self._classify_message = classify_message_fn
        self._detect_language = detect_language_fn

    def enrich(self, message: Message) -> Message:
        """Apply lightweight enrichments to a single message instance."""
        text = message.text or ""
        # Links
        if self.link_normalize_enabled:
            message.normalized_links = self._extract_and_normalize_links(text)
        # Tokens
        if self.token_estimate_enabled:
            message.token_count = self._estimate_tokens(text)
        # Classifier
        if self.message_classifier_enabled:
            # `source_info` is not needed inside classifier for now; pass None
            message.message_type = self._classify_message(text, message, None)
        # Lang
        if self.language_detect_enabled:
            message.lang = self._detect_language(text)
        return message

    def _can_merge_short(self, prev: Optional[Message], curr: Message) -> bool:
        """Check whether two consecutive messages are eligible for merge.

        Args:
            prev: Previous message in collection (if any)
            curr: Current message candidate

        Returns:
            True if both messages satisfy merge policy (same sender, within
            length and time window, and with non-empty text), otherwise False.
        """
        if not self.merge_short_messages_enabled or prev is None:
            return False
        if prev.sender_id is None or curr.sender_id is None:
            return False
        if prev.sender_id != curr.sender_id:
            return False
        if not prev.text or not curr.text:
            return False
        within_length = (
            len(prev.text) <= self.merge_short_messages_max_length
            and len(curr.text) <= self.merge_short_messages_max_length
        )
        if not within_length:
            return False
        time_gap = (curr.date - prev.date).total_seconds()
        if time_gap > self.merge_short_messages_max_gap_seconds:
            return False
        return True

    def maybe_merge_short(self, prev: Optional[Message], curr: Message) -> bool:
        """Merge short consecutive messages.

        Returns True if merged into prev.
        """
        if not self._can_merge_short(prev, curr):
            return False
        # merge
        # mypy: prev is not None due to guard above
        assert prev is not None
        prev.text = f"{prev.text}\n\n{curr.text}" if prev.text else curr.text
        if self.link_normalize_enabled and curr.normalized_links:
            for ln in curr.normalized_links:
                if ln not in prev.normalized_links:
                    prev.normalized_links.append(ln)
        if self.token_estimate_enabled:
            prev.token_count = self._estimate_tokens(prev.text or "")
        prev.reactions.extend(curr.reactions)
        prev.comments.extend(curr.comments)
        return True

    def _extract_and_normalize_links(self, text: str) -> list[str]:
        import re

        if not text:
            return []
        patterns = [
            r"https?://\S+",
            r"t\.me/\S+",
            r"[\w.-]+\.(?:com|org|io|dev|ru)(?:/\S*)?",
        ]
        candidates: list[str] = []
        for pat in patterns:
            candidates.extend(re.findall(pat, text, flags=re.IGNORECASE))
        links: list[str] = []
        for raw in candidates:
            norm = self._normalize_url(raw)
            if norm not in links:
                links.append(norm)
        return links
