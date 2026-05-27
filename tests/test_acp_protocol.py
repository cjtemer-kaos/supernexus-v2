import pytest
from src.core.acp_protocol import ACPMessage, ACPMessageType, ACPRouter


@pytest.fixture
def echo_handler():
    async def handler(msg: ACPMessage) -> ACPMessage:
        return msg.create_response({"echo": msg.payload})
    return handler


def test_acp_message_creation():
    msg = ACPMessage(sender="opencode", target="director", msg_type=ACPMessageType.REQUEST, payload={"action": "status"})
    assert msg.sender == "opencode"
    assert msg.target == "director"
    assert msg.msg_type == ACPMessageType.REQUEST
    assert msg.version == "1.0"
    assert msg.message_id.startswith("acp-")


def test_message_to_dict():
    msg = ACPMessage(sender="a", target="b", msg_type=ACPMessageType.NOTIFICATION, payload={"done": True})
    d = msg.to_dict()
    assert d["sender"] == "a"
    assert d["target"] == "b"
    assert d["msg_type"] == "notification"
    assert d["version"] == "1.0"


def test_expired_message():
    msg = ACPMessage(sender="a", target="b", msg_type=ACPMessageType.HEARTBEAT, payload={}, ttl_s=-1)
    assert msg.is_expired()


def test_create_response_links_correlation():
    msg = ACPMessage(sender="opencode", target="director", msg_type=ACPMessageType.REQUEST, payload={"q": "status"})
    resp = msg.create_response({"answer": "ok"})
    assert resp.sender == "director"
    assert resp.target == "opencode"
    assert resp.msg_type == ACPMessageType.RESPONSE
    assert resp.correlation_id == msg.message_id


@pytest.mark.asyncio
async def test_router_sends_to_handler(echo_handler):
    router = ACPRouter()
    router.register("director", echo_handler)
    msg = ACPMessage(sender="opencode", target="director", msg_type=ACPMessageType.REQUEST, payload={"ping": "pong"})
    resp = await router.send(msg)
    assert resp is not None
    assert resp.msg_type == ACPMessageType.RESPONSE
    assert resp.payload["echo"]["ping"] == "pong"


@pytest.mark.asyncio
async def test_router_unknown_agent_returns_error():
    router = ACPRouter()
    router.register("director", None)  # won't matter since target is unknown
    msg = ACPMessage(sender="opencode", target="ghost", msg_type=ACPMessageType.REQUEST, payload={"x": 1})
    resp = await router.send(msg)
    assert resp is not None
    assert resp.msg_type == ACPMessageType.ERROR
    assert "ghost" in resp.payload["error"]


@pytest.mark.asyncio
async def test_router_broadcast(echo_handler):
    router = ACPRouter()
    router.register("agent-a", echo_handler)
    router.register("agent-b", echo_handler)
    msg = ACPMessage(sender="opencode", target="*", msg_type=ACPMessageType.REQUEST, payload={"broadcast": True})
    responses = await router.broadcast(msg)
    assert len(responses) == 2
    assert all(r.msg_type == ACPMessageType.RESPONSE for r in responses)


def test_router_status():
    router = ACPRouter()
    async def dummy(msg): return None
    router.register("director", dummy)
    status = router.status()
    assert "director" in status["agents"]
    assert status["total_messages"] == 0
