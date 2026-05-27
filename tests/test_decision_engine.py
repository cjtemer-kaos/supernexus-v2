import pytest
from src.core.decision_engine import (
    DecisionEngine, CapabilityTable, PriorityScorer,
)
from src.core.command_protocol import Command


def test_capability_table_register_and_lookup():
    table = CapabilityTable()
    table.register("gema-coder", ["code", "refactor", "debug", "test"])
    table.register("gema-scholar", ["research", "search", "analyze"])
    assert table.best_match("refactorizar el modulo auth") == "gema-coder"
    assert table.best_match("research about circuit breakers") == "gema-scholar"


def test_capability_table_no_match_returns_default():
    table = CapabilityTable()
    table.register("gema-coder", ["code"])
    result = table.best_match("hacer cafe")
    assert result == "director"


def test_task_template_decompose_simple():
    engine = DecisionEngine()
    commands = engine.decompose("refactorizar auth middleware")
    assert len(commands) >= 1
    assert all(isinstance(c, Command) for c in commands)
    assert commands[0].action == "execute"


def test_task_template_decompose_complex():
    engine = DecisionEngine()
    commands = engine.decompose("implementar cache para API + tests + documentacion")
    assert len(commands) >= 2


def test_priority_scorer():
    scorer = PriorityScorer()
    assert scorer.score("fix critical bug in auth") <= 2
    assert scorer.score("refactor old module") >= 3


def test_evaluate_success():
    engine = DecisionEngine()
    verdict = engine.evaluate(output="diff --git a/file.py", exit_code=0, error=None)
    assert verdict.passed is True


def test_evaluate_failure():
    engine = DecisionEngine()
    verdict = engine.evaluate(output="", exit_code=1, error="SyntaxError: invalid syntax")
    assert verdict.passed is False
    assert "SyntaxError" in verdict.reason


def test_budget_allocate():
    engine = DecisionEngine()
    budget = engine.budget_allocate(domain="code", task_size="medium")
    assert 1000 <= budget <= 20000


def test_decompose_with_assignment():
    engine = DecisionEngine()
    engine.capabilities.register("gema-coder", ["code", "refactor", "implement"])
    engine.capabilities.register("gema-tester", ["test", "qa", "validate"])
    commands = engine.decompose("implementar feature X y escribir tests")
    targets = [c.target for c in commands]
    assert "gema-coder" in targets or "gema-tester" in targets
