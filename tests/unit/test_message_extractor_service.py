import pytest
from datetime import datetime, timezone

from src.models.schemas import SourceInfo
from src.services.extractors.message_extractor import MessageExtractor


class GW:
    def __init__(self):
        self.calls = []

    async def extract_reactions(self, message):  # noqa: ANN001
        self.calls.append(("reactions", message.id))
        # Return dicts so Pydantic can construct Reaction models
        return [{"emoji": "👍", "count": 1, "users": None}]

    async def extract_comments(self, client, entity, message, source_info, *, limit):  # noqa: ANN001
        self.calls.append(("comments", limit))
        return []

    def extract_forward_info(self, message):  # noqa: ANN001
        self.calls.append(("forward", message.id))
        return None


@pytest.mark.asyncio
async def test_message_extractor_service_builds_message():
    gw = GW()
    svc = MessageExtractor(gateway=gw, comments_limit=25)

    class Client:  # noqa: D401
        pass

    class Entity:  # noqa: D401
        pass

    class Msg:
        def __init__(self):
            self.id = 1
            self.date = datetime(2025, 1, 2, tzinfo=timezone.utc)
            self.message = "hello"
            self.sender_id = 10
            self.reply_to_msg_id = None

    msg = Msg()
    src = SourceInfo(id="@c", title="t", url="u", type="chat")

    out = await svc.extract(Client(), Entity(), msg, src)

    assert out.id == 1
    assert out.text == "hello"
    assert out.sender_id == 10
    assert out.reply_to_msg_id is None
    assert out.reactions and out.reactions[0].emoji == "👍"
    assert out.comments == []

    # Gateway was called with limit from service
    assert ("comments", 25) in gw.calls
