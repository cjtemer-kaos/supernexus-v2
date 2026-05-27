#!/usr/bin/env python3
"""Tests for ToolUniverse batch execution scheduling."""

import os
import time
import threading

import pytest

os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool


class SlowTool(BaseTool):
    active = 0
    max_active = 0
    lock = threading.Lock()

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.delay = float(tool_config.get("delay", 0.05))

    def run(self, arguments=None, **kwargs):
        with SlowTool.lock:
            SlowTool.active += 1
            SlowTool.max_active = max(SlowTool.max_active, SlowTool.active)
        try:
            time.sleep(self.delay)
        finally:
            with SlowTool.lock:
                SlowTool.active -= 1
        return {"value": arguments.get("value") if arguments else None}


@pytest.mark.unit
@pytest.mark.timeout(10)
def test_batch_respects_per_tool_concurrency():
    SlowTool.active = 0
    SlowTool.max_active = 0

    tu = ToolUniverse(tool_files={}, keep_default_tools=False)
    tool_config = {
        "name": "SlowTool",
        "type": "SlowTool",
        "description": "Slow tool for concurrency tests",
        "cacheable": False,
        "batch_max_concurrency": 3,
        "delay": 0.05,
        "parameter": {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
    }

    tu.register_custom_tool(SlowTool, tool_config=tool_config)

    tool_instance = tu._get_tool_instance("SlowTool", cache=True)
    assert tool_instance.get_batch_concurrency_limit() == 3

    calls = [
        {"name": "SlowTool", "arguments": {"value": i}}
        for i in range(20)
    ]

    tu.run(calls, use_cache=False, max_workers=10)

    assert SlowTool.max_active <= 3
    assert SlowTool.active == 0
