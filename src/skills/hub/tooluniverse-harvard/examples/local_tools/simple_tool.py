#!/usr/bin/env python3
"""
Simple Local Tool Example (No SMCP dependency)

This example shows how to create a simple local tool without SMCP dependencies.
It demonstrates the basic pattern for creating tools that can be used with ToolUniverse.

Usage:
    python simple_tool.py
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

# Import only the basic modules we need
from tooluniverse.tool_registry import register_tool
from tooluniverse.base_tool import BaseTool

# =============================================================================
# SIMPLE TOOL DEFINITIONS
# =============================================================================

@register_tool('SimpleHelloTool', config={
    "name": "simple_hello_tool",
    "description": "A simple hello world tool"
})
class SimpleHelloTool(BaseTool):
    """Simple hello world tool."""
    
    def run(self, arguments=None, **kwargs):
        """Execute the hello tool."""
        return {"message": "Hello from Simple Tool!", "success": True}

@register_tool('SimpleMathTool', config={
    "name": "simple_math_tool",
    "description": "Simple mathematical operations",
    "parameter": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "Mathematical operation"
            },
            "a": {"type": "number", "description": "First number"},
            "b": {"type": "number", "description": "Second number"}
        },
        "required": ["operation", "a", "b"]
    }
})
class SimpleMathTool(BaseTool):
    """Simple math tool."""
    
    def run(self, arguments=None, **kwargs):
        """Execute mathematical operation."""
        if arguments is None:
            arguments = kwargs
        
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be a dictionary", "success": False}
        
        operation = arguments.get('operation')
        a = arguments.get('a')
        b = arguments.get('b')
        
        try:
            a = float(a)
            b = float(b)
        except (ValueError, TypeError):
            return {"error": "Invalid number format", "success": False}
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return {"error": "Division by zero", "success": False}
            result = a / b
        else:
            return {"error": f"Unknown operation: {operation}", "success": False}
        
        return {
            "result": result,
            "operation": operation,
            "a": a,
            "b": b,
            "success": True
        }

# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_tool_registration():
    """Test that tools are properly registered."""
    
    print("🧪 Testing Tool Registration")
    print("=" * 30)
    
    try:
        # Check if tools are registered
        from tooluniverse.tool_registry import get_tool_registry
        
        registry = get_tool_registry()
        print(f"✅ Tool registry accessible: {len(registry)} tools registered")
        
        # Check specific tools
        expected_tools = ["simple_hello_tool", "simple_math_tool"]
        for tool_name in expected_tools:
            if tool_name in registry:
                print(f"✅ {tool_name} is registered")
            else:
                print(f"❌ {tool_name} not found in registry")
        
        return True
        
    except Exception as e:
        print(f"❌ Tool registration test failed: {e}")
        return False

def test_tool_instantiation():
    """Test that tools can be instantiated and run."""
    
    print("\n🧪 Testing Tool Instantiation")
    print("=" * 30)
    
    try:
        # Test SimpleHelloTool
        hello_tool = SimpleHelloTool(tool_config={"name": "simple_hello_tool"})
        result = hello_tool.run()
        print(f"Hello tool result: {result}")
        
        if result.get("success"):
            print("✅ SimpleHelloTool works")
        else:
            print("❌ SimpleHelloTool failed")
            return False
        
        # Test SimpleMathTool
        math_tool = SimpleMathTool(tool_config={"name": "simple_math_tool"})
        result = math_tool.run({"operation": "add", "a": 5, "b": 3})
        print(f"Math tool result: {result}")
        
        if result.get("success") and result.get("result") == 8:
            print("✅ SimpleMathTool works")
        else:
            print("❌ SimpleMathTool failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Tool instantiation test failed: {e}")
        return False

def test_tool_validation():
    """Test tool parameter validation."""
    
    print("\n🧪 Testing Tool Validation")
    print("=" * 30)
    
    try:
        math_tool = SimpleMathTool(tool_config={"name": "simple_math_tool"})
        
        # Test valid input
        result = math_tool.run({"operation": "multiply", "a": 4, "b": 6})
        if result.get("success") and result.get("result") == 24:
            print("✅ Valid input test passed")
        else:
            print("❌ Valid input test failed")
            return False
        
        # Test invalid operation
        result = math_tool.run({"operation": "invalid", "a": 1, "b": 2})
        if not result.get("success") and "error" in result:
            print("✅ Invalid operation test passed")
        else:
            print("❌ Invalid operation test failed")
            return False
        
        # Test division by zero
        result = math_tool.run({"operation": "divide", "a": 1, "b": 0})
        if not result.get("success") and "Division by zero" in result.get("error", ""):
            print("✅ Division by zero test passed")
        else:
            print("❌ Division by zero test failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Tool validation test failed: {e}")
        return False

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function to demonstrate simple local tools."""
    
    print("🚀 Simple Local Tools Example")
    print("=" * 40)
    
    tests = [
        ("Tool Registration", test_tool_registration),
        ("Tool Instantiation", test_tool_instantiation),
        ("Tool Validation", test_tool_validation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        result = test_func()
        results.append((test_name, result))
    
    print("\n📊 Test Results:")
    print("-" * 20)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 All tests passed! Simple local tools are working correctly.")
        print("\n💡 Note: This example works without ToolUniverse initialization.")
        print("   For full functionality, you would need to initialize ToolUniverse")
        print("   and use tu.run() to execute the tools.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
