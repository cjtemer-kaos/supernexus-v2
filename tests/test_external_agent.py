import pytest
import json
from src.core.external_agent import (
    ExternalAgent, ExternalAgentRegistry, AgentAdapter,
    CLIAdapter, HTTPAdapter, MessageBoardAdapter, MockAdapter,
)
from src.core.command_protocol import Command, CommandResult, CommandStatus


def test_external_agent_dataclass():
    agent = ExternalAgent(
        name="claude-code",
        capabilities=["code", "refactor", "test", "debug"],
        protocol="cli",
        endpoint="claude",
        cost="token-based",
        max_concurrent=1,
        timeout_s=300,
    )
    assert agent.name == "claude-code"
    assert agent.reliability == 1.0
    assert "code" in agent.capabilities


def test_registry_register_and_list():
    registry = ExternalAgentRegistry()
    registry.register(ExternalAgent(
        name="opencode", capabilities=["code"], protocol="cli",
        endpoint="opencode", cost="free",
    ))
    registry.register(ExternalAgent(
        name="antigravity", capabilities=["research"], protocol="http",
        endpoint="http://localhost:8080", cost="free",
    ))
    assert len(registry.agents) == 2
    assert "opencode" in [a.name for a in registry.agents]


def test_registry_best_agent_for_task():
    registry = ExternalAgentRegistry()
    registry.register(ExternalAgent(
        name="coder", capabilities=["code", "refactor"], protocol="mock",
        endpoint="", cost="free",
    ))
    registry.register(ExternalAgent(
        name="researcher", capabilities=["research", "search"], protocol="mock",
        endpoint="", cost="free",
    ))
    best = registry.best_for(task="refactorizar auth module", prefer_free=True)
    assert best.name == "coder"


def test_registry_best_agent_prefers_free():
    registry = ExternalAgentRegistry()
    registry.register(ExternalAgent(
        name="expensive", capabilities=["code"], protocol="mock",
        endpoint="", cost="api-credits",
    ))
    registry.register(ExternalAgent(
        name="free-one", capabilities=["code"], protocol="mock",
        endpoint="", cost="free",
    ))
    best = registry.best_for(task="write code", prefer_free=True)
    assert best.name == "free-one"


def test_registry_best_agent_considers_reliability():
    registry = ExternalAgentRegistry()
    registry.register(ExternalAgent(
        name="unreliable", capabilities=["code"], protocol="mock",
        endpoint="", cost="free", reliability=0.3,
    ))
    registry.register(ExternalAgent(
        name="reliable", capabilities=["code"], protocol="mock",
        endpoint="", cost="free", reliability=0.95,
    ))
    best = registry.best_for(task="write code")
    assert best.name == "reliable"


def test_registry_update_reliability():
    registry = ExternalAgentRegistry()
    registry.register(ExternalAgent(
        name="agent1", capabilities=["code"], protocol="mock",
        endpoint="", cost="free",
    ))
    registry.record_result("agent1", success=True)
    registry.record_result("agent1", success=True)
    registry.record_result("agent1", success=False)
    agent = registry.get("agent1")
    assert 0.6 < agent.reliability < 0.8


@pytest.mark.asyncio
async def test_mock_adapter():
    adapter = MockAdapter(response_output="mocked result")
    cmd = Command(target="test", action="execute", instruction={"task": "x"})
    result = await adapter.send_command(cmd)
    assert result.status == CommandStatus.COMPLETED
    assert result.output == "mocked result"
