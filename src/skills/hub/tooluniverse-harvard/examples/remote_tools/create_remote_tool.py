#!/usr/bin/env python3
"""
Create Remote Tool Example

This example shows how to create a remote tool using the @register_mcp_tool decorator.
The tool runs on a separate MCP server and can be accessed by ToolUniverse clients.

Usage:
    python create_remote_tool.py

This will:
1. Create a text processing remote tool
2. Start an MCP server on port 8001
3. Generate a configuration file for ToolUniverse
"""

import sys
import os
import json
from typing import Dict, Any

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

# =============================================================================
# REMOTE TOOL DEFINITION
# =============================================================================

@register_mcp_tool(
    tool_type_name="remote_text_processor",
    config={
        "description": "Processes text using remote computation resources",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string", 
                    "description": "Text to process"
                },
                "operation": {
                    "type": "string", 
                    "enum": ["uppercase", "lowercase", "reverse", "word_count", "char_count"],
                    "description": "Operation to perform on the text"
                },
                "language": {
                    "type": "string",
                    "default": "en",
                    "description": "Language of the text (for future language-specific processing)"
                }
            },
            "required": ["text", "operation"]
        }
    },
    mcp_config={
        "server_name": "Text Processing Remote Server",
        "host": "0.0.0.0",
        "port": 8008,
        "transport": "http"
    }
)
class RemoteTextProcessor:
    """
    Remote text processing tool that runs on a separate MCP server.
    
    This tool demonstrates how to create a remote tool that can be accessed
    by ToolUniverse clients through the MCP protocol.
    """
    
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute text processing operation.
        
        Args:
            arguments: Dictionary containing:
                - text (str): Text to process
                - operation (str): Operation to perform
                - language (str, optional): Language of the text
        
        Returns:
            Dictionary containing:
                - result (str): Processed text
                - operation (str): Operation performed
                - metadata (dict): Additional information
                - success (bool): Whether operation succeeded
        """
        try:
            text = arguments.get("text", "")
            operation = arguments.get("operation", "uppercase")
            language = arguments.get("language", "en")
            
            if not text:
                return {
                    "result": "",
                    "operation": operation,
                    "metadata": {"error": "No text provided"},
                    "success": False
                }
            
            # Perform the requested operation
            if operation == "uppercase":
                result = text.upper()
            elif operation == "lowercase":
                result = text.lower()
            elif operation == "reverse":
                result = text[::-1]
            elif operation == "word_count":
                result = str(len(text.split()))
            elif operation == "char_count":
                result = str(len(text))
            else:
                return {
                    "result": text,
                    "operation": operation,
                    "metadata": {"error": f"Unknown operation: {operation}"},
                    "success": False
                }
            
            return {
                "result": result,
                "operation": operation,
                "metadata": {
                    "language": language,
                    "input_length": len(text),
                    "output_length": len(str(result))
                },
                "success": True
            }
            
        except Exception as e:
            return {
                "result": "",
                "operation": arguments.get("operation", "unknown"),
                "metadata": {"error": str(e)},
                "success": False
            }

# =============================================================================
# CONFIGURATION FILE GENERATION
# =============================================================================

def create_config_file():
    """Create configuration file for ToolUniverse to load this remote tool."""
    
    config = [
        {
            "name": "mcp_auto_loader_text_processor",
            "description": "Automatically discover and load text processing tools from MCP Server",
            "type": "MCPAutoLoaderTool",
            "tool_prefix": "",  # 改为空字符串，避免重复前缀
            "server_url": "http://localhost:8008/mcp",
            "timeout": 30,  # 增加超时时间到30秒
            "required_api_keys": []
        }
    ]
    
    config_file = "remote_tools_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Configuration file created: {config_file}")
    return config_file

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to start the remote tool server."""
    
    print("🚀 Remote Tool Server Example")
    print("=" * 50)
    
    # Create configuration file
    config_file = create_config_file()
    
    print(f"\n📋 Tool Information:")
    print(f"   Name: remote_text_processor")
    print(f"   Server: http://localhost:8008")
    print(f"   Config: {config_file}")
    
    print(f"\n🔧 Available Operations:")
    print(f"   - uppercase: Convert text to uppercase")
    print(f"   - lowercase: Convert text to lowercase") 
    print(f"   - reverse: Reverse the text")
    print(f"   - word_count: Count words in text")
    print(f"   - char_count: Count characters in text")
    
    print(f"\n📖 Usage Example:")
    print(f"   In another terminal, run:")
    print(f"   python use_remote_tool.py")
    
    print(f"\n🌐 Starting MCP server on port 8008...")
    print(f"   Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Start the MCP server
        print("🔧 Starting MCP server...")
        start_mcp_server()
    except KeyboardInterrupt:
        print(f"\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up configuration file
        if os.path.exists(config_file):
            os.remove(config_file)
            print(f"🧹 Cleaned up configuration file")

if __name__ == "__main__":
    main()
