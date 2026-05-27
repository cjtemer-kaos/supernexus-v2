#!/usr/bin/env python3
"""
Example: Using run() parameters in custom tools

This example demonstrates how custom tools can access and use the
stream_callback, use_cache, and validate parameters passed from
run_one_function().
"""

from tooluniverse import ToolUniverse
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool

# =============================================================================
# Method 1: Cache-Aware Tool
# =============================================================================
# Description: A tool that optimizes behavior based on cache status
# Syntax: @register_tool decorator with cache-aware logic

@register_tool('CacheAwareTool', config={
    "name": "cache_aware_search",
    "type": "CacheAwareTool",
    "description": "A tool that optimizes based on cache status",
    "parameter": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            }
        },
        "required": ["query"]
    }
})
class CacheAwareTool(BaseTool):
    """A tool that behaves differently based on caching settings."""
    
    def run(self, arguments=None, use_cache=False, **kwargs):
        """
        Execute the tool with cache awareness.
        
        If caching is enabled, we might skip expensive operations
        since the result will be cached anyway.
        """
        query = arguments.get("query", "")
        
        if use_cache:
            # Caching is enabled - can be more aggressive with operations
            result = f"[CACHED MODE] Deep analysis of: {query}"
        else:
            # No caching - maybe use lighter operations
            result = f"[FRESH MODE] Quick analysis of: {query}"
        
        return {
            "query": query,
            "result": result,
            "used_cache": use_cache
        }

# =============================================================================
# Method 2: Validation-Aware Tool
# =============================================================================
# Description: A tool that knows if validation was performed
# Syntax: @register_tool decorator with validation-aware logic

@register_tool('ValidationAwareTool', config={
    "name": "validation_aware_processor",
    "type": "ValidationAwareTool",
    "description": "A tool that knows if validation was performed",
    "parameter": {
        "type": "object",
        "properties": {
            "data": {
                "type": "string",
                "description": "Data to process"
            }
        },
        "required": ["data"]
    }
})
class ValidationAwareTool(BaseTool):
    """A tool that can perform additional checks if validation was skipped."""
    
    def run(self, arguments=None, validate=True, **kwargs):
        """
        Execute the tool with validation awareness.
        
        If validation was skipped, the tool can perform its own
        quick checks to ensure safety.
        """
        data = arguments.get("data", "")
        
        if not validate:
            # Validation was skipped - do quick sanity checks
            if not data:
                return {
                    "error": "Data cannot be empty",
                    "validation_performed": False
                }
        
        return {
            "data": data,
            "processed": data.upper(),
            "validation_status": "validated" if validate else "self-checked"
        }

# =============================================================================
# Method 3: Streaming-Aware Tool
# =============================================================================
# Description: A tool that uses streaming if available
# Syntax: @register_tool decorator with streaming logic

@register_tool('StreamingAwareTool', config={
    "name": "streaming_reporter",
    "type": "StreamingAwareTool",
    "description": "A tool that uses streaming if available",
    "parameter": {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Task to execute"
            }
        },
        "required": ["task"]
    }
})
class StreamingAwareTool(BaseTool):
    """A tool that streams progress if a callback is provided."""
    
    def run(self, arguments=None, stream_callback=None, **kwargs):
        """
        Execute the tool with optional streaming.
        
        If stream_callback is provided, send progress updates.
        Otherwise, just return the final result.
        """
        task = arguments.get("task", "")
        
        steps = [
            f"Initializing {task}...",
            f"Processing {task}...",
            f"Finalizing {task}...",
            f"Completed {task}!"
        ]
        
        if stream_callback:
            for step in steps:
                stream_callback(step + "\n")
        
        return {
            "task": task,
            "steps": len(steps),
            "streaming_used": stream_callback is not None
        }

# =============================================================================
# Method 4: Comprehensive Tool with All Parameters
# =============================================================================
# Description: A tool that uses all available parameters
# Syntax: @register_tool decorator with comprehensive parameter handling

@register_tool('ComprehensiveTool', config={
    "name": "comprehensive_tool",
    "type": "ComprehensiveTool",
    "description": "A tool that uses all available parameters",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "Operation to perform"
            }
        },
        "required": ["operation"]
    }
})
class ComprehensiveTool(BaseTool):
    """A tool that demonstrates using all parameters together."""
    
    def run(self, arguments=None, stream_callback=None, use_cache=False, validate=True):
        """
        Execute with full context about the execution environment.
        
        This tool can make informed decisions based on:
        - Whether streaming is available
        - Whether results will be cached
        - Whether validation was performed
        """
        operation = arguments.get("operation", "")
        
        # Build execution strategy based on parameters
        strategy = []
        
        if use_cache:
            strategy.append("Results will be cached")
        else:
            strategy.append("Fresh execution")
        
        if validate:
            strategy.append("Parameters validated")
        else:
            strategy.append("Validation skipped")
        
        if stream_callback:
            strategy.append("Streaming enabled")
            stream_callback(f"Executing: {operation}\n")
            stream_callback(f"Strategy: {', '.join(strategy)}\n")
        else:
            strategy.append("No streaming")
        
        return {
            "operation": operation,
            "execution_strategy": strategy,
            "context": {
                "streaming": stream_callback is not None,
                "caching": use_cache,
                "validated": validate
            }
        }

# =============================================================================
# Method 5: Tool Usage Examples
# =============================================================================
# Description: Demonstrate how to use tools with different parameter combinations
# Syntax: tu.run_one_function() with various parameter combinations

tu = ToolUniverse()
tu.load_tools()

# Example 1: Cache-aware tool usage
result1 = tu.run_one_function({
    "name": "cache_aware_search",
    "arguments": {"query": "python"}
}, use_cache=False)

result2 = tu.run_one_function({
    "name": "cache_aware_search", 
    "arguments": {"query": "python"}
}, use_cache=True)

# Example 2: Validation-aware tool usage
result3 = tu.run_one_function({
    "name": "validation_aware_processor", 
    "arguments": {"data": "hello"}
}, validate=True)

result4 = tu.run_one_function({
    "name": "validation_aware_processor", 
    "arguments": {"data": "world"}
}, validate=False)

# Example 3: Streaming-aware tool usage
def my_callback(chunk):
    # Process streaming chunks
    pass

result5 = tu.run_one_function({
    "name": "streaming_reporter", 
    "arguments": {"task": "analysis"}
}, stream_callback=None)

result6 = tu.run_one_function({
    "name": "streaming_reporter", 
    "arguments": {"task": "processing"}
}, stream_callback=my_callback)

# Example 4: Comprehensive tool with all parameters
result7 = tu.run_one_function({
    "name": "comprehensive_tool", 
    "arguments": {"operation": "full_analysis"}
}, stream_callback=my_callback, use_cache=True, validate=True)

# Example 5: Using dynamic API
result8 = tu.tools.cache_aware_search(
    query="dynamic call",
    use_cache=True
)

# =============================================================================
# Summary of Parameter Usage
# =============================================================================
# Tools can access these execution parameters:
# - arguments: Tool-specific parameters from user
# - stream_callback: Function for real-time progress updates
# - use_cache: Whether results should be cached
# - validate: Whether input validation should be performed
# 
# These parameters allow tools to:
# - Adapt behavior based on execution context
# - Provide streaming output when needed
# - Optimize performance based on caching settings
# - Perform additional validation when needed
# - Make informed decisions about execution strategy