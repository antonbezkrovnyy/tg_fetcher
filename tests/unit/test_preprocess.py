"""Unit tests for preprocessing strategies and MessagePreprocessor."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.models.schemas import Message
from src.services.preprocess import strategies as pp
from src.services.preprocess.message_preprocessor import MessagePreprocessor


class DummyMsg(SimpleNamespace):
    """Lightweight stand-in for Telethon Message where needed."""


def test_normalize_url_removes_tracking_and_adds_scheme():
    """normalize_url should drop tracking params and ensure https scheme."""
    url = "example.com/path?utm_source=google&ref=abc&id=1"
    norm = pp.normalize_url(url)
    assert norm.startswith("https://example.com/path")
    assert "utm_source" not in norm and "ref=" not in norm
    assert "id=1" in norm


def test_normalize_url_trims_trailing_punctuation():
    """normalize_url should trim trailing punctuation characters."""
    url = "https://t.me/somechannel/,)"
    norm = pp.normalize_url(url)
    assert norm == "https://t.me/somechannel"


def test_estimate_tokens_simple():
    """estimate_tokens returns integer and handles empty input as 0."""
    assert pp.estimate_tokens("") == 0
    val = pp.estimate_tokens("Hello world")
    assert isinstance(val, int) and val >= 2


def test_classify_message_variants():
    """classify_message identifies question/code/log/spam/answer/service."""
    # question
    m = DummyMsg(action=None)
    assert pp.classify_message("Как сделать это?", m, None) == "question"
    # code
    assert pp.classify_message("def foo(x):\n    return x", m, None) == "code"
    # log
    assert pp.classify_message("Traceback: error happened", m, None) == "log"
    # spam (many links)
    text = "visit http://a.com and https://b.com t.me/c plus http://d.com"
    assert pp.classify_message(text, m, None) == "spam"
    # answer
    assert pp.classify_message("Ответ: так-то", m, None) == "answer"
    # service
    m2 = DummyMsg(action=object())
    assert pp.classify_message("", m2, None) == "service"


def test_detect_language():
    """detect_language recognizes ru, en and falls back to other."""
    assert pp.detect_language("") == "other"
    assert pp.detect_language("Это по-русски, проверка языка") == "ru"
    assert pp.detect_language("This is clearly English text") == "en"


@pytest.mark.parametrize(
    "flags",
    [
        {"links": True, "tokens": True, "cls": True, "lang": True},
        {"links": False, "tokens": False, "cls": False, "lang": False},
    ],
)
def test_message_preprocessor_enrich(flags):
    """Preprocessor.enrich populates fields according to feature flags."""
    p = MessagePreprocessor(
        link_normalize_enabled=flags["links"],
        token_estimate_enabled=flags["tokens"],
        message_classifier_enabled=flags["cls"],
        language_detect_enabled=flags["lang"],
        merge_short_messages_enabled=True,
        merge_short_messages_max_length=200,
        merge_short_messages_max_gap_seconds=120,
        normalize_url_fn=pp.normalize_url,
        estimate_tokens_fn=pp.estimate_tokens,
        classify_message_fn=pp.classify_message,
        detect_language_fn=pp.detect_language,
    )
    msg = Message(
        id=1,
        date=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        text="How to foo? visit example.com",
        sender_id=1,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )
    out = p.enrich(msg)
    if flags["links"]:
        assert out.normalized_links and out.normalized_links[0].startswith("https://")
    else:
        assert out.normalized_links == []
    if flags["tokens"]:
        assert isinstance(out.token_count, int)
    else:
        assert out.token_count is None
    if flags["cls"]:
        allowed = {
            "question",
            "answer",
            "code",
            "log",
            "spam",
            "service",
            "other",
        }
        assert out.message_type in allowed
    else:
        assert out.message_type is None
    if flags["lang"]:
        assert out.lang in {"ru", "en", "other"}
    else:
        assert out.lang is None


def test_message_preprocessor_merge_short():
    """maybe_merge_short combines short consecutive messages and recomputes tokens."""
    p = MessagePreprocessor(
        link_normalize_enabled=True,
        token_estimate_enabled=True,
        message_classifier_enabled=False,
        language_detect_enabled=False,
        merge_short_messages_enabled=True,
        merge_short_messages_max_length=50,
        merge_short_messages_max_gap_seconds=300,
        normalize_url_fn=pp.normalize_url,
        estimate_tokens_fn=pp.estimate_tokens,
        classify_message_fn=pp.classify_message,
        detect_language_fn=pp.detect_language,
    )
    from datetime import datetime, timedelta, timezone

    base_ts = datetime.now(timezone.utc)
    m1 = Message(
        id=1,
        date=base_ts,
        text="first",
        sender_id=42,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )
    m2 = Message(
        id=2,
        date=base_ts + timedelta(seconds=60),
        text="second",
        sender_id=42,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )

    p.enrich(m1)
    p.enrich(m2)
    merged = p.maybe_merge_short(m1, m2)
    assert merged is True
    assert "first" in m1.text and "second" in m1.text
    assert m1.token_count is not None and m1.token_count >= 2
