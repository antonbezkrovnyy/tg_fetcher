from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.models.schemas import Message
from src.services.preprocess.message_preprocessor import MessagePreprocessor


def _mk_msg(mid: int, text: str, sender: int, dt: datetime) -> Message:
    return Message(id=mid, date=dt, text=text, sender_id=sender)


def test_enrich_and_merge_short_messages():
    # Delegates
    normalize = lambda url: url.lower()
    estimate = lambda text: len(text or "") // 2
    classify = lambda text, msg, _ctx: "question" if "?" in (text or "") else "other"
    detect = lambda text: "en"

    pp = MessagePreprocessor(
        link_normalize_enabled=True,
        token_estimate_enabled=True,
        message_classifier_enabled=True,
        language_detect_enabled=True,
        merge_short_messages_enabled=True,
        merge_short_messages_max_length=50,
        merge_short_messages_max_gap_seconds=60,
        normalize_url_fn=normalize,
        estimate_tokens_fn=estimate,
        classify_message_fn=classify,
        detect_language_fn=detect,
    )

    now = datetime.now(tz=timezone.utc)
    m1 = _mk_msg(1, "See https://Example.COM", 42, now)
    m2 = _mk_msg(2, "And t.me/chan?", 42, now + timedelta(seconds=30))

    # Enrich both
    m1 = pp.enrich(m1)
    m2 = pp.enrich(m2)

    # Links normalized and token counts estimated
    assert any("example.com" in ln for ln in m1.normalized_links)
    assert m2.token_count == len(m2.text) // 2
    assert m2.message_type == "question"
    assert m2.lang == "en"

    # Eligible for merge (same sender, short length, within gap)
    merged = pp.maybe_merge_short(m1, m2)
    assert merged is True
    assert "And t.me/chan?" in (m1.text or "")
    # Token count recalculated for merged text
    assert m1.token_count == len(m1.text) // 2


import datetime as dt

from src.models.schemas import Message
from src.services.preprocess.message_preprocessor import MessagePreprocessor


def _norm(u: str) -> str:  # passthrough for tests
    return u


def _estimate(text: str) -> int:
    return len(text.split())


def _classify(text: str, message: Message, _: object) -> str:  # noqa: ARG001
    return "other"


def _detect(text: str) -> str:  # noqa: ARG001
    return "other"


def test_maybe_merge_short_happy_path() -> None:
    p = MessagePreprocessor(
        link_normalize_enabled=True,
        token_estimate_enabled=True,
        message_classifier_enabled=False,
        language_detect_enabled=False,
        merge_short_messages_enabled=True,
        merge_short_messages_max_length=16,
        merge_short_messages_max_gap_seconds=60,
        normalize_url_fn=_norm,
        estimate_tokens_fn=_estimate,
        classify_message_fn=_classify,
        detect_language_fn=_detect,
    )

    now = dt.datetime.now(dt.timezone.utc)
    prev = Message(
        id=1,
        date=now,
        text="Hi",
        sender_id=100,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )
    curr = Message(
        id=2,
        date=now + dt.timedelta(seconds=10),
        text="there",
        sender_id=100,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )

    # Enrich not required for merge, but safe to call
    prev = p.enrich(prev)
    curr = p.enrich(curr)

    merged = p.maybe_merge_short(prev, curr)

    assert merged is True
    assert prev.text == "Hi\n\nthere"
    # token estimate is len(words)
    assert prev.token_count == 2


def test_maybe_merge_short_rejects_large_gap_or_sender_mismatch() -> None:
    p = MessagePreprocessor(
        link_normalize_enabled=False,
        token_estimate_enabled=False,
        message_classifier_enabled=False,
        language_detect_enabled=False,
        merge_short_messages_enabled=True,
        merge_short_messages_max_length=16,
        merge_short_messages_max_gap_seconds=30,
        normalize_url_fn=_norm,
        estimate_tokens_fn=_estimate,
        classify_message_fn=_classify,
        detect_language_fn=_detect,
    )

    base = dt.datetime.now(dt.timezone.utc)
    prev = Message(
        id=1,
        date=base,
        text="a",
        sender_id=200,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )
    # Too large gap
    curr1 = Message(
        id=2,
        date=base + dt.timedelta(seconds=120),
        text="b",
        sender_id=200,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )
    # Different sender
    curr2 = Message(
        id=3,
        date=base + dt.timedelta(seconds=10),
        text="b",
        sender_id=201,
        reply_to_msg_id=None,
        forward_from=None,
        reactions=[],
        comments=[],
    )

    assert p.maybe_merge_short(prev, curr1) is False
    assert p.maybe_merge_short(prev, curr2) is False
