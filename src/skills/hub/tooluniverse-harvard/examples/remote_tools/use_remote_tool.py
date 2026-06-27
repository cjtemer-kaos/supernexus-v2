#!/usr/bin/env python3
"""
Use Remote Tool Example

This example shows how to use remote tools created with register_mcp_tool.
It demonstrates different ways to call remote tools and handle responses.

Prerequisites:
    - Remote tool server must be running (run create_remote_tool.py first)

Usage:
    python use_remote_tool.py
"""

import sys
import os
import json
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse import ToolUniverse


# =============================================================================
# CONFIGURATION
# =============================================================================

def create_config_file():
    """Create configuration file for loading remote tools."""
    
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
# TOOL USAGE EXAMPLES
# =============================================================================

def test_basic_usage(tu, tool_name):
    """Test basic remote tool usage with tu.run()."""
    
    print("\n🔧 Testing Basic Usage (tu.run())")
    print("-" * 40)
    
    test_cases = [
        {
            "text": "Hello World",
            "operation": "uppercase",
            "expected": "HELLO WORLD"
        },
        {
            "text": "Python Programming",
            "operation": "lowercase",
            "expected": "python programming"
        },
        {
            "text": "ToolUniverse",
            "operation": "reverse",
            "expected": "esrevinUlooT"
        },
        {
            "text": "This is a test sentence",
            "operation": "word_count",
            "expected": "5"
        },
        {
            "text": "Hello",
            "operation": "char_count",
            "expected": "5"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            print(f"\nTest {i}: {test_case['operation']}")
            print(f"Input: '{test_case['text']}'")
            
            result = tu.run({
                "name": tool_name,
                "arguments": {
                    "text": test_case["text"],
                    "operation": test_case["operation"]
                }
            })
            
            print(f"Result: {result}")
            
            if result.get("success") and result.get("result") == test_case["expected"]:
                print("✅ Test passed")
            else:
                print("❌ Test failed")
                print(f"Expected: {test_case['expected']}")
                print(f"Got: {result.get('result', 'N/A')}")
                
        except Exception as e:
            print(f"❌ Test failed with error: {e}")


def test_direct_access(tu, tool_name):
    """Test direct tool access with tu.tools attribute."""
    
    print("\n🔧 Testing Direct Access (tu.tools)")
    print("-" * 40)
    
    try:
        # Test direct tool access
        tool_callable = getattr(tu.tools, tool_name)
        result = tool_callable(
            text="Direct Access Test",
            operation="uppercase"
        )
        
        print(f"Direct access result: {result}")
        
        if result.get("success"):
            print("✅ Direct access works")
        else:
            print("❌ Direct access failed")
            
    except Exception as e:
        print(f"❌ Direct access failed with error: {e}")


def test_batch_processing(tu, tool_name):
    """Test batch processing with multiple operations."""
    
    print("\n🔧 Testing Batch Processing")
    print("-" * 40)
    
    texts = [
        "First text",
        "Second text",
        "Third text"
    ]
    
    operations = ["uppercase", "lowercase", "reverse"]
    
    try:
        # Create batch requests
        batch_requests = []
        for i, text in enumerate(texts):
            batch_requests.append({
                "name": tool_name,
                "arguments": {
                    "text": text,
                    "operation": operations[i % len(operations)]
                }
            })
        
        print(f"Processing {len(batch_requests)} requests...")
        
        # Execute batch
        results = tu.run(batch_requests)
        
        print(f"Batch results:")
        for i, result in enumerate(results):
            print(f"  {i+1}: {result}")
        
        print("✅ Batch processing completed")
        
    except Exception as e:
        print(f"❌ Batch processing failed: {e}")


def test_error_handling(tu, tool_name):
    """Test error handling with invalid inputs."""
    
    print("\n🔧 Testing Error Handling")
    print("-" * 40)
    
    error_cases = [
        {
            "text": "",
            "operation": "uppercase",
            "description": "Empty text"
        },
        {
            "text": "Test",
            "operation": "invalid_operation",
            "description": "Invalid operation"
        },
        {
            "text": "Test",
            "operation": "uppercase",
            "language": "invalid_lang",
            "description": "Invalid language parameter"
        }
    ]
    
    for i, case in enumerate(error_cases, 1):
        try:
            print(f"\nError Test {i}: {case['description']}")
            
            result = tu.run({
                "name": tool_name,
                "arguments": case
            })
            
            print(f"Result: {result}")
            
            if not result.get("success"):
                print("✅ Error handled correctly")
            else:
                print("❌ Error not handled as expected")
                
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to demonstrate remote tool usage."""
    
    print("🚀 Remote Tool Usage Example")
    print("=" * 50)
    
    # Create configuration file
    config_file = create_config_file()
    
    try:
        # Initialize ToolUniverse
        print("\n📦 Initializing ToolUniverse (remote tools only)...")
        tu = ToolUniverse(tool_files={}, keep_default_tools=False)
        
        # Load remote tools
        print("🔄 Loading remote tools...")
        tu.load_tools(tool_config_files={"remote_tools": config_file})
        
        remote_tools = []
        for name in tu.all_tool_dict.keys():
            if name.startswith("remote_") or "remote_text_processor" in name:
                remote_tools.append(name)
        print(f"✅ Loaded {len(remote_tools)} remote tool(s): {', '.join(remote_tools) or 'None'}")

        remote_tool_name = next(
            (name for name in remote_tools if name.endswith("remote_text_processor")),
            None,
        )
        if not remote_tool_name and "remote_text_processor" in tu.all_tool_dict:
            remote_tool_name = "remote_text_processor"

        if remote_tool_name:
            print(f"✅ Remote tool '{remote_tool_name}' is available")
        else:
            print("❌ Remote text processor tool not found")
            if tu.all_tool_dict:
                print("Currently loaded tool names (first 10 shown):")
                for tool_name in list(tu.all_tool_dict.keys())[:10]:
                    print(f"  - {tool_name}")
            return
        
        # Run tests
        test_basic_usage(tu, remote_tool_name)
        test_direct_access(tu, remote_tool_name)
        test_batch_processing(tu, remote_tool_name)
        test_error_handling(tu, remote_tool_name)
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure the remote tool server is running:")
        print("   python create_remote_tool.py")
        
    finally:
        # Clean up
        if os.path.exists(config_file):
            os.remove(config_file)
            print(f"\n🧹 Cleaned up configuration file")


if __name__ == "__main__":
    main()
