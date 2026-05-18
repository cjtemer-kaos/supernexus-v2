# Remote Tools Examples

This folder contains examples for creating and using remote tools with ToolUniverse.

## Overview

Remote tools are Python classes decorated with `@register_mcp_tool` that run on separate servers and are accessed via MCP (Model Context Protocol). They provide:

- **Scalability**: Offload heavy computation to dedicated servers
- **Integration**: Connect with existing systems and services  
- **Flexibility**: Use tools in different programming languages
- **Isolation**: Keep sensitive operations separate

## Examples

### 1. Create Remote Tool (`create_remote_tool.py`)
Shows how to create a remote tool using the `@register_mcp_tool` decorator.

**Features:**
- Text processing tool with multiple operations
- MCP server configuration
- Parameter validation
- Error handling

**Run:**
```bash
python create_remote_tool.py
```

### 2. Use Remote Tool (`use_remote_tool.py`)
Shows how to load and use remote tools in ToolUniverse.

**Features:**
- Configuration-based tool loading
- Multiple API usage patterns
- Error handling and testing

**Run:**
```bash
python use_remote_tool.py
```

## Quick Start

1. **Create a remote tool:**
   ```bash
   python create_remote_tool.py
   ```

2. **In another terminal, use the remote tool:**
   ```bash
   python use_remote_tool.py
   ```

## Configuration Files

- `expert_feedback_config.json` - Example configuration for expert feedback tools

## Requirements

- ToolUniverse
- MCP (Model Context Protocol) support
- Python 3.7+
