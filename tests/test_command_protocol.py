import pytest
import json
from src.core.command_protocol import Command, CommandResult, CommandStatus, CommandDispatcher


def test_command_creation():
    cmd = Command(
        target="sub-director-code",
        action="execute",
        instruction={"task": "Refactorizar auth", "files": ["src/api/server.py"]},
        constraints=["no romper tests"],
        output_format="diff",
        deadline_tokens=5000,
        priority=1,
        on_fail="report_and_wait",
    )
    assert cmd.command_id
    assert cmd.target == "sub-director-code"
    assert cmd.priority == 1
    assert cmd.to_dict()["action"] == "execute"


def test_command_result_creation():
    result = CommandResult(
        command_id="cmd-001",
        status=CommandStatus.COMPLETED,
        output="diff --git a/...",
        tokens_used=3200,
    )
    assert result.status == CommandStatus.COMPLETED
    assert result.error is None
    assert result.tokens_used == 3200


def test_command_result_failed():
    result = CommandResult(
        command_id="cmd-002",
        status=CommandStatus.FAILED,
        output="",
        error="Module not found",
    )
    assert result.status == CommandStatus.FAILED
    assert result.error == "Module not found"


def test_command_serialization_roundtrip():
    cmd = Command(
        target="gema-coder",
        action="execute",
        instruction={"task": "test"},
        priority=2,
    )
    d = cmd.to_dict()
    json_str = json.dumps(d)
    restored = json.loads(json_str)
    assert restored["target"] == "gema-coder"
    assert restored["priority"] == 2


class FakeAgent:
    def __init__(self, name, response_status=CommandStatus.COMPLETED):
        self.name = name
        self.response_status = response_status
        self.received = []

    async def handle_command(self, cmd: Command) -> CommandResult:
        self.received.append(cmd)
        return CommandResult(
            command_id=cmd.command_id,
            status=self.response_status,
            output=f"done by {self.name}",
            tokens_used=100,
        )


@pytest.mark.asyncio
async def test_dispatcher_routes_to_agent():
    agent = FakeAgent("coder")
    dispatcher = CommandDispatcher()
    dispatcher.register("gema-coder", agent.handle_command)
    cmd = Command(target="gema-coder", action="execute", instruction={"task": "test"})
    result = await dispatcher.dispatch(cmd)
    assert result.status == CommandStatus.COMPLETED
    assert "done by coder" in result.output
    assert len(agent.received) == 1


@pytest.mark.asyncio
async def test_dispatcher_unknown_target():
    dispatcher = CommandDispatcher()
    cmd = Command(target="nonexistent", action="execute", instruction={"task": "x"})
    result = await dispatcher.dispatch(cmd)
    assert result.status == CommandStatus.FAILED
    assert "unknown target" in result.error.lower()


@pytest.mark.asyncio
async def test_dispatcher_timeout():
    import asyncio

    async def slow_handler(cmd):
        await asyncio.sleep(10)
        return CommandResult(command_id=cmd.command_id, status=CommandStatus.COMPLETED, output="")

    dispatcher = CommandDispatcher(default_timeout_s=0.1)
    dispatcher.register("slow", slow_handler)
    cmd = Command(target="slow", action="execute", instruction={"task": "x"})
    result = await dispatcher.dispatch(cmd)
    assert result.status == CommandStatus.TIMEOUT
    assert "timeout" in result.error.lower()
