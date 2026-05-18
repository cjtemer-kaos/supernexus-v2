#!/usr/bin/env python3
"""
ToolUniverse Parameter Passing Example

Demonstrates how tools receive execution context parameters
"""

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

# =============================================================================
# Custom Tool Definition
# =============================================================================
# Description: Create a demonstration tool that can respond to execution parameters
# Syntax: @register_tool decorator with config

@register_tool('DemoTool', config={
    "name": "demo_tool",
    "type": "DemoTool", 
    "description": "Demonstration tool",
    "parameter": {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"]
    }
})
class DemoTool(BaseTool):
    def run(self, arguments=None, stream_callback=None, use_cache=False, validate=True):
        message = arguments.get("message", "")
        
        # Adjust behavior based on execution parameters
        mode = "cached" if use_cache else "realtime"
        status = "validated" if validate else "unvalidated"
        
        # Stream output callback for real-time progress updates
        if stream_callback:
            stream_callback(f"Processing: {message}\n")
        
        return f"{mode} - {message} ({status})"

# =============================================================================
# Method 1: Basic Parameter Passing
# =============================================================================
# Description: Default parameter usage
# Syntax: tu.tools.tool_name(parameter=value)
tu = ToolUniverse()
tu.load_tools()

# Basic calling - default parameters
result1 = tu.tools.demo_tool(message="Hello")

# =============================================================================
# Method 2: Caching Parameter
# =============================================================================
# Description: Enable caching for repeated calls
# Syntax: tu.tools.tool_name(parameter=value, use_cache=True)

# Using cache - second call will be faster
result2 = tu.tools.demo_tool(message="World", use_cache=True)

# =============================================================================
# Method 3: Validation Parameter
# =============================================================================
# Description: Skip validation to improve performance
# Syntax: tu.tools.tool_name(parameter=value, validate=False)

# Skip validation - improve performance
result3 = tu.tools.demo_tool(message="Test", validate=False)

# =============================================================================
# Method 4: Streaming Parameter
# =============================================================================
# Description: Real-time progress display with callback
# Syntax: tu.tools.tool_name(parameter=value, stream_callback=callback)

# Stream output - real-time progress display
def callback(chunk):
    # Process streaming output chunks
    pass

result4 = tu.tools.demo_tool(message="Stream", stream_callback=callback)

# =============================================================================
# Method 5: All Parameters Combined
# =============================================================================
# Description: Use all parameter combinations for complete functionality
# Syntax: tu.tools.tool_name(param=value, stream_callback=cb, use_cache=True, validate=True)

# All parameter combinations - complete functionality demonstration
result5 = tu.tools.demo_tool(
    message="All",
    stream_callback=callback,
    use_cache=True,
    validate=True
)

# =============================================================================
# Summary of Parameters
# =============================================================================
# Tools can access these execution context parameters:
# - arguments: Tool-specific parameters passed by user
# - stream_callback: Function for real-time progress updates
# - use_cache: Whether results should be cached
# - validate: Whether input validation should be performed
# 
# These parameters allow tools to:
# - Adapt behavior based on execution context
# - Provide streaming output when needed
# - Optimize performance based on caching settings
# - Perform additional validation when needed