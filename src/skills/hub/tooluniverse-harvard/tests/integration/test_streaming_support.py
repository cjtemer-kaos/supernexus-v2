import sys
import types

import pytest


# Stub out heavy dependencies that attempt network calls during import
if "rcsbapi" not in sys.modules:
    rcsbapi_module = types.ModuleType("rcsbapi")
    rcsbapi_data_module = types.ModuleType("rcsbapi.data")

    class _DummyDataQuery:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):  # pragma: no cover - behavior not used in tests
            return {}

    rcsbapi_data_module.DataQuery = _DummyDataQuery
    rcsbapi_module.data = rcsbapi_data_module
    sys.modules["rcsbapi"] = rcsbapi_module
    sys.modules["rcsbapi.data"] = rcsbapi_data_module


from tooluniverse.base_tool import BaseTool
from tooluniverse.execute_function import ToolUniverse


class _RecordingStreamingTool(BaseTool):
    calls = []
    STREAM_FLAG_KEY = "_tooluniverse_stream"

    def run(self, arguments, stream_callback=None):
        # record arguments passed into the tool for assertions
        _RecordingStreamingTool.calls.append(
            {
                "arguments": dict(arguments),
                "has_stream": stream_callback is not None,
            }
        )
        if stream_callback:
            stream_callback("chunk-1")
            stream_callback("chunk-2")
        return "stream-done"


class _RecordingNonStreamingTool(BaseTool):
    calls = []

    def run(self, arguments):
        _RecordingNonStreamingTool.calls.append(dict(arguments))
        return "nonstream-done"


def _make_tool_universe():
    # Avoid loading hundreds of default tools; rely only on manually registered ones
    return ToolUniverse(tool_files={}, keep_default_tools=False)


def _register_tool(tool_universe, tool_cls, name, properties=None, required=None):
    config = {
        "name": name,
        "type": name,
        "description": name,
        "parameter": {
            "type": "object",
            "properties": properties or {},
            "required": required or [],
        },
    }
    tool_universe.register_custom_tool(tool_cls, tool_name=name, tool_config=config)


def test_run_one_function_forwards_stream_callback_when_supported():
    tu = _make_tool_universe()
    _RecordingStreamingTool.calls.clear()
    _register_tool(tu, _RecordingStreamingTool, "StreamingTool")

    captured = []
    result = tu.run_one_function(
        {"name": "StreamingTool", "arguments": {}},
        stream_callback=captured.append,
    )

    assert result == "stream-done"
    assert captured == ["chunk-1", "chunk-2"]
    assert len(_RecordingStreamingTool.calls) == 1
    call = _RecordingStreamingTool.calls[0]
    assert call["arguments"] == {"_tooluniverse_stream": True}
    assert call["has_stream"] is True


def test_run_one_function_ignores_stream_callback_when_tool_has_no_support():
    tu = _make_tool_universe()
    _RecordingNonStreamingTool.calls.clear()
    _register_tool(
        tu,
        _RecordingNonStreamingTool,
        "PlainTool",
        properties={"foo": {"type": "string"}},
    )

    captured = []
    result = tu.run_one_function(
        {"name": "PlainTool", "arguments": {"foo": "bar"}},
        stream_callback=captured.append,
    )

    assert result == "nonstream-done"
    assert captured == []
    assert _RecordingNonStreamingTool.calls == [{"foo": "bar"}]


def test_stream_flag_preserved_for_tools_that_inspect_arguments():
    tu = _make_tool_universe()
    _RecordingStreamingTool.calls.clear()
    _register_tool(
        tu,
        _RecordingStreamingTool,
        "StreamingToolFlag",
        properties={"value": {"type": "integer"}},
    )

    tu.run_one_function(
        {"name": "StreamingToolFlag", "arguments": {"value": 42}},
        stream_callback=lambda _: None,
    )

    call = _RecordingStreamingTool.calls[-1]
    assert call["arguments"] == {"value": 42, "_tooluniverse_stream": True}
    assert call["has_stream"] is True
