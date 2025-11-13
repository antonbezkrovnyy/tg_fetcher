import asyncio
from datetime import datetime, timezone
import types
import pytest

from src.models.schemas import SourceInfo
from src.services.gateway import telegram_gateway as tg


class _ChannelStub:
    def __init__(self, id: int):
        self.id = id


class _MessageReactionsStub:
    def __init__(self, results):
        self.results = results


class _ReactionResult:
    def __init__(self, reaction, count: int):
        self.reaction = reaction
        self.count = count


class _ReactionEmoticon:
    def __init__(self, emoticon: str):
        self.emoticon = emoticon


class _RepliesStub:
    def __init__(self, channel_id: int, max_id: int, replies: int):
        self.channel_id = channel_id
        self.max_id = max_id
        self.replies = replies


class _ForwardFromId:
    def __init__(self, user_id: int):
        self.user_id = user_id


class _ForwardStub:
    def __init__(self, user_id: int, from_name: str, date: datetime):
        self.from_id = _ForwardFromId(user_id)
        self.from_name = from_name
        self.date = date


class _CommentStub:
    def __init__(self, *, id: int, message: str | None, date: datetime, sender_id: int | None, reply_to_msg_id: int | None, forward=None, reactions=None):
        self.id = id
        self.message = message
        self.date = date
        self.sender_id = sender_id
        self.reply_to_msg_id = reply_to_msg_id
        self.forward = forward
        self.reactions = reactions


@pytest.fixture(autouse=True)
def patch_telethon_types(monkeypatch):
    monkeypatch.setattr(tg, "Channel", _ChannelStub, raising=True)
    monkeypatch.setattr(tg, "MessageReactions", _MessageReactionsStub, raising=True)
    yield


@pytest.mark.asyncio
async def test_extract_reactions_none_and_parsing():
    gw = tg.TelegramGateway()

    class Msg:
        pass

    # No reactions attribute
    assert await gw.extract_reactions(Msg()) == []

    # reactions = None
    m2 = Msg()
    m2.reactions = None
    assert await gw.extract_reactions(m2) == []

    # reactions with two results: emoticon and string
    m3 = Msg()
    r1 = _ReactionResult(_ReactionEmoticon("👍"), 3)
    r2 = _ReactionResult("🔥", 2)
    m3.reactions = _MessageReactionsStub([r1, r2])

    parsed = await gw.extract_reactions(m3)
    assert [(p.emoji, p.count) for p in parsed] == [("👍", 3), ("🔥", 2)]


@pytest.mark.asyncio
async def test_extract_forward_info_variants():
    gw = tg.TelegramGateway()

    class Msg:
        pass

    # No forward
    assert gw.extract_forward_info(Msg()) is None

    # With forward
    m2 = Msg()
    when = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    m2.forward = _ForwardStub(user_id=123, from_name="Alice", date=when)
    fwd = gw.extract_forward_info(m2)
    assert fwd is not None
    assert fwd.from_id == 123
    assert fwd.from_name == "Alice"
    assert fwd.date == when


@pytest.mark.asyncio
async def test_extract_comments_paths_and_happy(monkeypatch):
    gw = tg.TelegramGateway()

    class ClientStub:
        def iter_messages(self, channel_id, reply_to, limit):  # noqa: D401
            # Simulate async generator-returning function (like Telethon)
            async def gen():
                yield _CommentStub(
                    id=1,
                    message="c1",
                    date=datetime(2025, 1, 2, tzinfo=timezone.utc),
                    sender_id=10,
                    reply_to_msg_id=None,
                    forward=_ForwardStub(1, "A", datetime(2025, 1, 2, tzinfo=timezone.utc)),
                    reactions=_MessageReactionsStub([_ReactionResult("😀", 1)]),
                )
                yield _CommentStub(
                    id=2,
                    message=None,
                    date=datetime(2025, 1, 2, tzinfo=timezone.utc),
                    sender_id=None,
                    reply_to_msg_id=1,
                    forward=None,
                    reactions=None,
                )
            return gen()

    client = ClientStub()

    class Msg:
        pass

    # Non-channel source -> []
    src_non_channel = SourceInfo(id="@c", title="t", url="u", type="chat")
    m = Msg()
    m.replies = _RepliesStub(channel_id=100, max_id=5, replies=10)
    assert await gw.extract_comments(client, _ChannelStub(100), m, src_non_channel, limit=10) == []

    # Channel but no replies attribute -> []
    src_channel = SourceInfo(id="@c", title="t", url="u", type="channel")
    m2 = Msg()
    assert await gw.extract_comments(client, _ChannelStub(100), m2, src_channel, limit=10) == []

    # replies == 0 -> []
    m3 = Msg()
    m3.replies = _RepliesStub(channel_id=100, max_id=5, replies=0)
    assert await gw.extract_comments(client, _ChannelStub(100), m3, src_channel, limit=10) == []

    # limit <= 0 -> []
    m4 = Msg()
    m4.replies = _RepliesStub(channel_id=100, max_id=5, replies=2)
    assert await gw.extract_comments(client, _ChannelStub(100), m4, src_channel, limit=0) == []

    # Happy path: two comments
    m5 = Msg()
    m5.replies = _RepliesStub(channel_id=100, max_id=5, replies=2)
    comments = await gw.extract_comments(client, _ChannelStub(100), m5, src_channel, limit=10)

    assert len(comments) == 2
    c1, c2 = comments
    assert c1.id == 1 and c1.text == "c1" and c1.reply_to_msg_id is None
    assert c2.id == 2 and c2.text is None and c2.reply_to_msg_id == 1
