"""Tests para gemas_core.dispatch: dispatch_gema + list_gema_methods."""
import asyncio
from typing import Any, Dict

from gemas_core.base import GemaBase
from gemas_core.dispatch import dispatch_gema, list_gema_methods


class ExecuteTaskContextGema(GemaBase):
    name = "execute_task_context"
    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        return {"success": True, "gema": "execute_task_context",
                "task": task, "context": context}


class ExecuteTaskOnlyGema(GemaBase):
    name = "execute_task_only"
    async def execute(self, task: str) -> Dict[str, Any]:
        return {"success": True, "gema": "execute_task_only", "task": task}


class RunMethodGema(GemaBase):
    name = "run_method"
    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        raise NotImplementedError
    async def run(self, task: str, context: str = "") -> Dict[str, Any]:
        return {"success": True, "gema": "run_method", "task": task}


class VariadicGema(GemaBase):
    name = "variadic"
    async def execute(self, *args) -> Dict[str, Any]:
        return {"success": True, "gema": "variadic", "args": args}


class NoExecuteGema:
    """Duck-typed object sin herencia GemaBase."""
    name = "no_execute"

    async def execute(self, task: str) -> Dict[str, Any]:
        return {"success": True, "gema": "no_execute"}


class BrokenGema(GemaBase):
    name = "broken"
    async def execute(self, task: str, context: str = "") -> Dict[str, Any]:
        raise RuntimeError("intentional failure")


def test_list_gema_methods():
    g = ExecuteTaskContextGema()
    methods = list_gema_methods(g)
    assert "execute" in methods
    assert "to_dict" in methods


def test_dispatch_execute_task_context():
    g = ExecuteTaskContextGema()
    result = asyncio.run(dispatch_gema(g, "hello", "extra context"))
    assert result["success"] is True
    assert result["task"] == "hello"
    assert result["context"] == "extra context"


def test_dispatch_execute_task_only():
    g = ExecuteTaskOnlyGema()
    result = asyncio.run(dispatch_gema(g, "hello"))
    assert result["task"] == "hello"
    assert "context" not in result


def test_dispatch_run_method_fallback():
    g = RunMethodGema()
    result = asyncio.run(dispatch_gema(g, "hello", "ctx"))
    # dispatch tries 'execute' first (not present), then 'run'
    assert result["gema"] == "run_method"


def test_dispatch_variadic():
    g = VariadicGema()
    result = asyncio.run(dispatch_gema(g, "hello", "ctx"))
    assert result["gema"] == "variadic"
    assert "hello" in result["args"]


def test_dispatch_broken_returns_error():
    g = BrokenGema()
    result = asyncio.run(dispatch_gema(g, "hello"))
    assert result["success"] is False
    assert "RuntimeError" in result["error"]


def test_dispatch_duck_typed():
    """Objeto sin GemaBase pero con método execute debe funcionar."""
    g = NoExecuteGema()
    result = asyncio.run(dispatch_gema(g, "hello"))
    assert result["success"] is True
    assert result["gema"] == "no_execute"


def test_dispatch_no_method_returns_error():
    class Empty:
        name = "empty"

    result = asyncio.run(dispatch_gema(Empty(), "hello"))
    assert result["success"] is False


def test_dispatch_explicit_method():
    g = RunMethodGema()
    # Pass method="run" to skip looking for "execute"
    result = asyncio.run(dispatch_gema(g, "hi", method="run"))
    assert result["gema"] == "run_method"
