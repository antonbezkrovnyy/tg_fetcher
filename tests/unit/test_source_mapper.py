import types
import sys
import pytest

from src.services.mappers import source_mapper as sm


class _ChannelStub:
    def __init__(self, *, id: int, title: str | None, username: str | None, megagroup: bool):
        self.id = id
        self.title = title
        self.username = username
        self.megagroup = megagroup


class _ChatStub:
    def __init__(self, *, id: int, title: str | None, megagroup: bool):
        self.id = id
        self.title = title
        self.megagroup = megagroup


class _UserStub:
    def __init__(self, *, id: int, first_name: str | None = None, last_name: str | None = None, username: str | None = None):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username


@pytest.fixture(autouse=True)
def patch_telethon_types(monkeypatch):
    # Replace Telethon types in the mapper module to simple stubs for isinstance checks
    monkeypatch.setattr(sm, "Channel", _ChannelStub, raising=True)
    monkeypatch.setattr(sm, "Chat", _ChatStub, raising=True)
    monkeypatch.setattr(sm, "User", _UserStub, raising=True)
    yield


def test_channel_with_username():
    mapper = sm.SourceInfoMapper()
    entity = _ChannelStub(id=123, title="My Channel", username="mychan", megagroup=False)

    info = mapper.extract_source_info(entity, chat_identifier="@fallback")

    assert info.id == "@mychan"
    assert info.title == "My Channel"
    assert info.url == "https://t.me/mychan"
    assert info.type == "channel"


def test_channel_megagroup_without_username():
    mapper = sm.SourceInfoMapper()
    entity = _ChannelStub(id=999, title="SG", username=None, megagroup=True)

    info = mapper.extract_source_info(entity, chat_identifier="ru_python")

    assert info.id == "channel_999"
    assert info.title == "SG"
    assert info.url == "https://t.me/c/999"
    assert info.type == "supergroup"


def test_chat_regular_and_group():
    mapper = sm.SourceInfoMapper()

    # regular chat (not megagroup)
    chat_regular = _ChatStub(id=45, title="Regular Chat", megagroup=False)
    info_regular = mapper.extract_source_info(chat_regular, chat_identifier="chatid")
    assert info_regular.id == "chat_45"
    assert info_regular.title == "Regular Chat"
    assert info_regular.url == "https://t.me/c/45"
    assert info_regular.type == "chat"

    # group (megagroup True)
    chat_group = _ChatStub(id=77, title="Group Chat", megagroup=True)
    info_group = mapper.extract_source_info(chat_group, chat_identifier="chatid")
    assert info_group.id == "chat_77"
    assert info_group.title == "Group Chat"
    assert info_group.url == "https://t.me/c/77"
    assert info_group.type == "group"


def test_user_fullname_and_username():
    mapper = sm.SourceInfoMapper()

    user = _UserStub(id=7, first_name="Alice", last_name="Doe", username="alice")
    info = mapper.extract_source_info(user, chat_identifier="@fallback")

    assert info.id == "@alice"
    assert info.title == "Alice Doe"
    assert info.url == "https://t.me/alice"
    assert info.type == "chat"


def test_user_no_names_no_username():
    mapper = sm.SourceInfoMapper()

    user = _UserStub(id=9)
    info = mapper.extract_source_info(user, chat_identifier="ignored")

    assert info.id == "user_9"
    assert info.title == "User_9"
    # No username provided, url remains empty per implementation
    assert info.url == ""
    assert info.type == "chat"


def test_get_sender_name_variants():
    mapper = sm.SourceInfoMapper()

    # None
    assert mapper.get_sender_name(None) == "Unknown"

    # User: first + last
    user_full = _UserStub(id=1, first_name="John", last_name="Smith")
    assert mapper.get_sender_name(user_full) == "John Smith"

    # User: username only
    user_username = _UserStub(id=2, username="johnny")
    assert mapper.get_sender_name(user_username) == "@johnny"

    # User: fallback to ID
    user_id_only = _UserStub(id=3)
    assert mapper.get_sender_name(user_id_only) == "User_3"

    # Channel: missing/empty title -> fallback
    channel_no_title = _ChannelStub(id=555, title=None, username=None, megagroup=False)
    assert mapper.get_sender_name(channel_no_title) == "Channel_555"

    # Unknown type -> "Unknown"
    class Weird:  # not User/Channel/Chat
        pass

    assert mapper.get_sender_name(Weird()) == "Unknown"
