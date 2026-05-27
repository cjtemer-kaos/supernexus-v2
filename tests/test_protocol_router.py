import pytest
from src.core.protocol_router import ProtocolRouter, DiscoveryService, ServiceEntry, Protocol


@pytest.fixture
def sample_services():
    ds = DiscoveryService()
    ds.register(ServiceEntry(name="opencode", protocol=Protocol.ACP, endpoint="opencode",
                             capabilities=["code", "refactor"]))
    ds.register(ServiceEntry(name="agent-zero", protocol=Protocol.HTTP, endpoint="http://localhost:50080",
                             capabilities=["code", "research"]))
    ds.register(ServiceEntry(name="broken-agent", protocol=Protocol.ACP, endpoint="broken",
                             capabilities=["code"], healthy=False))
    return ds


def test_discovery_register_and_find(sample_services):
    entry = sample_services.get("opencode")
    assert entry is not None
    assert entry.protocol == Protocol.ACP
    assert entry.endpoint == "opencode"


def test_discovery_capability_filter(sample_services):
    code_services = sample_services.discover("code")
    assert len(code_services) == 2  # opencode + broken-agent excluded by healthy=False
    # wait, broken-agent has healthy=False, so discover only returns healthy
    # Actually discover checks healthy=True, so only opencode and agent-zero have code
    assert len(code_services) == 2  # opencode and agent-zero


def test_discovery_unhealthy_excluded(sample_services):
    all_services = sample_services.services
    broken = [s for s in all_services if s.name == "broken-agent"]
    assert len(broken) == 1
    assert broken[0].healthy is False
    # discover should not return unhealthy
    assert sample_services.discover("code")[0].name != "broken-agent"


def test_router_route_to_protocol(sample_services):
    router = ProtocolRouter()
    router.discovery = sample_services
    router.register_protocol(Protocol.ACP, "acp-handler")
    route = router.route("opencode")
    assert route is not None
    assert route[0] == Protocol.ACP
    assert route[1] == "acp-handler"


def test_router_unknown_target(sample_services):
    router = ProtocolRouter()
    router.discovery = sample_services
    assert router.route("ghost") is None


def test_best_for_capability_prefers_acp(sample_services):
    router = ProtocolRouter()
    router.discovery = sample_services
    best = router.best_for_capability("code")
    assert best is not None
    assert best.protocol == Protocol.ACP  # ACP has priority 0


def test_router_status(sample_services):
    router = ProtocolRouter()
    router.discovery = sample_services
    router.register_protocol(Protocol.ACP, "handler")
    status = router.status()
    assert "acp" in status["protocols"]
    assert status["discovery"]["total"] == 3
