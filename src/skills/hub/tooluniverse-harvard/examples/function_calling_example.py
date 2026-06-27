#!/usr/bin/env python3
"""
ToolUniverse Function Calling Examples

Demonstrates various methods for calling tools in ToolUniverse
"""

from tooluniverse import ToolUniverse

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# =============================================================================
# Method 1: Direct Function-Style Calling
# =============================================================================
# Syntax: tu.tools.ToolName(parameter=value)
# Description: Most intuitive way to call tools, like calling regular Python functions
result1 = tu.tools.UniProt_get_entry_by_accession(accession="P05067")

# =============================================================================
# Method 2: Function-Style with Caching
# =============================================================================
# Syntax: tu.tools.ToolName(parameter=value, use_cache=True)
# Description: Enables caching for repeated calls with same parameters
result2 = tu.tools.UniProt_get_entry_by_accession(
    accession="P05067", 
    use_cache=True
)

# =============================================================================
# Method 3: Traditional JSON-Based Calling
# =============================================================================
# Syntax: tu.run_one_function({'name': 'ToolName', 'arguments': {...}})
# Description: Original method using JSON structure for tool name and arguments
result3 = tu.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})

# =============================================================================
# Method 4: Multiple Individual Calls
# =============================================================================
# Description: Execute multiple tools individually (alternative to batch calling)
# Syntax: Multiple tu.run_one_function() calls
result4a = tu.run_one_function({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": "P05067"}
})

result4b = tu.run_one_function({
    "name": "UniProt_get_entry_by_accession", 
    "arguments": {"accession": "P12345"}
})

# =============================================================================
# Method 5: Tool Discovery and Dynamic Calling
# =============================================================================
# Syntax: getattr(tu.tools, 'ToolName')(parameters)
# Description: Dynamically select and call tools based on runtime conditions
tool_name = "UniProt_get_entry_by_accession"
if hasattr(tu.tools, tool_name):
    tool_func = getattr(tu.tools, tool_name)
    result5 = tool_func(accession="P05067")


# =============================================================================
# Method 10: Async-Style Calling (if supported)
# =============================================================================
# Syntax: await tu.tools.ToolName(parameters) - if async support exists
# Description: Asynchronous calling for non-blocking operations
# Note: Check if your ToolUniverse version supports async calling
# async def example_async_call():
#     result = await tu.tools.UniProt_get_entry_by_accession(accession="P05067")

# =============================================================================
# Summary of Methods
# =============================================================================
# All methods return the same type of result objects.
# Choose the method that best fits your use case:
# - Direct calling: Most intuitive for single tool calls
# - JSON-based: Useful for dynamic tool selection
# - Batch calling: Efficient for multiple tool calls
# - Dynamic calling: Good for programmatic tool selection
# - Error handling: Essential for robust applications
