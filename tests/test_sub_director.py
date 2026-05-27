import pytest
from src.core.sub_director import SubDirector, SubDirectorConfig, SubDirectorRegistry
from src.core.command_protocol import Command, CommandResult, CommandStatus, CommandDispatcher


def test_sub_director_creation():
    sd = SubDirector(SubDirectorConfig(
        name="code",
        domain="code",
        capabilities=["code", "refactor", "debug", "test", "architect"],
        agents=["gema-coder", "gema-debugger", "gema-architect", "gema-tester"],
        token_budget=50000,
    ))
    assert sd.config.name == "code"
    assert sd.remaining_budget == 50000


def test_sub_director_accepts_matching_command():
    sd = SubDirector(SubDirectorConfig(
        name="code", domain="code",
        capabilities=["code", "refactor"],
        agents=["gema-coder"],
        token_budget=50000,
    ))
    cmd = Command(target="sub-director-code", action="execute",
                  instruction={"task": "refactorizar auth"})
    assert sd.can_handle(cmd) is True


def test_sub_director_rejects_non_matching():
    sd = SubDirector(SubDirectorConfig(
        name="code", domain="code",
        capabilities=["code"],
        agents=["gema-coder"],
        token_budget=50000,
    ))
    cmd = Command(target="sub-director-research", action="execute",
                  instruction={"task": "investigar APIs"})
    assert sd.can_handle(cmd) is False


def test_sub_director_budget_tracking():
    sd = SubDirector(SubDirectorConfig(
        name="code", domain="code",
        capabilities=["code"],
        agents=["gema-coder"],
        token_budget=10000,
    ))
    sd.consume_budget(3000)
    assert sd.remaining_budget == 7000
    sd.consume_budget(8000)
    assert sd.remaining_budget == 0
    assert sd.is_over_budget is True


def test_registry_creates_default_sub_directors():
    registry = SubDirectorRegistry.create_defaults()
    assert len(registry.sub_directors) == 4
    names = [sd.config.name for sd in registry.sub_directors]
    assert "code" in names
    assert "research" in names
    assert "ops" in names
    assert "voice" in names


def test_registry_route_command():
    registry = SubDirectorRegistry.create_defaults()
    cmd = Command(target="sub-director-code", action="execute",
                  instruction={"task": "test"})
    sd = registry.route(cmd)
    assert sd is not None
    assert sd.config.name == "code"
