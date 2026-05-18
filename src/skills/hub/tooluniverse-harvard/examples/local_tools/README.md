# Local Tools Examples

This folder contains examples for creating and using local tools with ToolUniverse.

## Overview

Local tools are Python classes decorated with `@register_tool` that run within the ToolUniverse process. They provide:

- **Performance**: Direct execution without network overhead
- **Simplicity**: Easy to create and debug
- **Integration**: Seamless access to ToolUniverse features
- **Flexibility**: Full Python ecosystem access

## Examples

### 1. Simple Tool (`simple_tool.py`)
Shows how to create basic local tools using the `@register_tool` decorator.

**Features:**
- Hello world tool
- Math operations tool
- Parameter handling
- Error handling
- Tool registration testing

**Run:**
```bash
python simple_tool.py
```

## Quick Start

1. **Run the example:**
   ```bash
   python simple_tool.py
   ```

## Testing

For comprehensive testing of local tools functionality, run the test suite:

```bash
# Run all local tools tests
pytest tests/examples/test_local_tools_*.py

# Run specific test files
pytest tests/examples/test_local_tools_simple_integration.py
pytest tests/examples/test_local_tools_tooluniverse_integration.py
```

## Requirements

- ToolUniverse
- Python 3.7+
- Standard library modules (math, json, etc.)
