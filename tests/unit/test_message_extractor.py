import pytest
from datetime import datetime, timezone

from src.services.extractors import message_extractor as me
from src.models.schemas import SourceInfo


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


class _CommentStub:
    def __init__(self, *, id: int, message: str | None, date, sender_id, reply_to_msg_id, forward=None, reactions=None):
        self.id = id
        self.message = message
        self.date = date
        self.sender_id = sender_id
        self.reply_to_msg_id = reply_to_msg_id
        self.forward = forward
        self.reactions = reactions


class _ForwardFromId:
    def __init__(self, user_id: int):
        self.user_id = user_id


class _ForwardStub:
    def __init__(self, user_id: int, from_name: str, date):
        self.from_id = _ForwardFromId(user_id)
        self.from_name = from_name
        self.date = date


@pytest.fixture(autouse=True)
def patch_types(monkeypatch):
    # Satisfy isinstance checks inside module
    monkeypatch.setattr(me, "Channel", _ChannelStub, raising=True)
    # Patch the actual telethon.tl.types.MessageReactions so that the function-level import uses our stub
    import telethon.tl.types as tt

    monkeypatch.setattr(tt, "MessageReactions", _MessageReactionsStub, raising=True)
    yield


@pytest.mark.asyncio
async def test_extract_reactions_helpers():
    class Msg:  # no reactions attr
        pass

    assert await me.extract_reactions(Msg()) == []

    m2 = Msg()
    m2.reactions = None
    assert await me.extract_reactions(m2) == []

    m3 = Msg()
    r1 = _ReactionResult(_ReactionEmoticon("👍"), 3)
    r2 = _ReactionResult("🔥", 2)
    m3.reactions = _MessageReactionsStub([r1, r2])

    out = await me.extract_reactions(m3)
    assert [(x.emoji, x.count) for x in out] == [("👍", 3), ("🔥", 2)]


@pytest.mark.asyncio
async def test_extract_forward_and_comments():
    class ClientStub:
        def iter_messages(self, channel_id, reply_to, limit):  # noqa: D401
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
        def __init__(self):
            self.id = 0

    # Forward None
    assert me.extract_forward_info(Msg()) is None

    m = Msg()
    m.forward = _ForwardStub(123, "Name", datetime(2025, 1, 2, tzinfo=timezone.utc))
    fwd = me.extract_forward_info(m)
    assert fwd is not None and fwd.from_id == 123 and fwd.from_name == "Name"

    # Non-channel -> []
    src_non = SourceInfo(id="@c", title="t", url="u", type="chat")
    ms = Msg()
    ms.replies = _RepliesStub(channel_id=1, max_id=5, replies=2)
    assert await me.extract_comments(client, _ChannelStub(1), ms, src_non) == []

    # Channel, various empty paths
    src_ch = SourceInfo(id="@c", title="t", url="u", type="channel")
    m2 = Msg()
    assert await me.extract_comments(client, _ChannelStub(1), m2, src_ch) == []

    m3 = Msg()
    m3.replies = _RepliesStub(channel_id=1, max_id=5, replies=0)
    assert await me.extract_comments(client, _ChannelStub(1), m3, src_ch) == []

    # Happy path (limit fixed inside function to 50)
    m4 = Msg()
    m4.replies = _RepliesStub(channel_id=1, max_id=5, replies=2)
    comments = await me.extract_comments(client, _ChannelStub(1), m4, src_ch)
    assert len(comments) == 2
    assert comments[0].id == 1 and comments[1].id == 2


@pytest.mark.asyncio
async def test_extract_reactions_exception_path():
    class BadResults:
        def __iter__(self):  # noqa: D401
            raise RuntimeError("boom")

    class Msg:
        def __init__(self):
            self.id = 42

    m = Msg()
    # Use patched _MessageReactionsStub to satisfy isinstance check, but provide bad results
    m.reactions = _MessageReactionsStub(BadResults())

    out = await me.extract_reactions(m)
    assert out == []  # swallowed exception, returned empty list


@pytest.mark.asyncio
async def test_extract_comments_exception_path():
    class ClientBoom:
        def iter_messages(self, channel_id, reply_to, limit):  # noqa: D401
            async def gen():
                if False:  # pragma: no cover - ensure async generator type
                    yield None
                raise RuntimeError("iter fail")

            return gen()

    class Msg:
        def __init__(self):
            self.id = 7
            self.replies = _RepliesStub(channel_id=1, max_id=5, replies=2)

    src_ch = SourceInfo(id="@c", title="t", url="u", type="channel")
    out = await me.extract_comments(ClientBoom(), _ChannelStub(1), Msg(), src_ch)
    assert out == []  # exception path swallowed


def test_extract_forward_info_exception_path():
    class BadForward:
        def __getattr__(self, name):  # noqa: D401
            raise RuntimeError("bad forward")

    class Msg:
        def __init__(self):
            self.id = 11
            self.forward = BadForward()

    assert me.extract_forward_info(Msg()) is None
