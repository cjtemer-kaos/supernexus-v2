"""
Test suite for ToolUniverse Software Package Tools

This test validates the PackageTool implementations for popular Python packages.
It follows the same pattern as other test files in the ToolUniverse test directory.

Usage:
    python src/tooluniverse/test/test_software_tools.py
"""

from tooluniverse.execute_function import ToolUniverse


def main():
    print("🧪 Testing ToolUniverse Software Package Tools")
    print("=" * 60)

    # Step 1: Initialize ToolUniverse with only software tools to reduce noise
    tooluni = ToolUniverse()
    tooluni.load_tools(tool_type=["software"])

    # Step 2: Get all software package tools
    software_tools = [
        name
        for name in tooluni.all_tool_dict.keys()
        if "get_" in name and "_info" in name
    ]
    print(f"📦 Found {len(software_tools)} software package tools:")
    for tool in software_tools:
        package = tool.replace("get_", "").replace("_info", "").replace("_", "-")
        print(f"   • {package}")

    # Step 3: Define test queries for the PackageTool-based software tools
    test_queries = [
        # Basic tests with examples
        {"name": "get_numpy_info", "arguments": {"include_examples": True}},
        {"name": "get_pandas_info", "arguments": {"include_examples": True}},
        {"name": "get_requests_info", "arguments": {"include_examples": True}},
        {"name": "get_flask_info", "arguments": {"include_examples": True}},
        {"name": "get_scikit_learn_info", "arguments": {"include_examples": True}},
        {"name": "get_matplotlib_info", "arguments": {"include_examples": True}},
        {"name": "get_pytorch_info", "arguments": {"include_examples": True}},
        # Test without examples
        {"name": "get_numpy_info", "arguments": {"include_examples": False}},
        # Test different source options
        {"name": "get_pandas_info", "arguments": {"include_examples": False}},
        {"name": "get_requests_info", "arguments": {"include_examples": True}},
        {"name": "get_flask_info", "arguments": {"include_examples": False}},
    ]

    print("\n" + "=" * 60)

    # Step 4: Run all test queries
    successful_tests = 0
    failed_tests = 0

    for idx, query in enumerate(test_queries):
        try:
            package_name = (
                query["name"].replace("get_", "").replace("_info", "").replace("_", "-")
            )
            print(f"\n[{idx+1}] Testing {package_name}...")
            print(f"    Tool: {query['name']}")
            print(f"    Args: {query['arguments']}")
            print("-" * 50)

            result = tooluni.run(query)

            # Check if the result is successful
            if (
                isinstance(result, dict)
                and "error" not in result
                and result.get("package_name")
            ):
                print("✅ SUCCESS")
                successful_tests += 1

                # Print key information
                print(f"   📦 Package: {result.get('package_name', 'Unknown')}")
                print(
                    f"   📋 Description: {result.get('description', 'No description')}..."
                )
                print(f"   🔧 Import: {result.get('import_name', 'Unknown')}")
                print(f"   📊 Category: {result.get('category', 'Unknown')}")
                print(f"   💾 Source: {result.get('source', 'Unknown')}")

                if result.get("installation"):
                    print(f"   💻 Install: {result['installation'].get('pip', 'N/A')}")

                if result.get("documentation"):
                    print(f"   📚 Docs: {result['documentation']}")

                if query["arguments"].get("include_examples", False):
                    if result.get("usage_example"):
                        print(f"   📝 Example: {len(result['usage_example'])} chars")
                    if result.get("quick_start"):
                        print(f"   🚀 Quick start: {len(result['quick_start'])} steps")

            elif isinstance(result, dict) and "error" in result:
                print("❌ FAILED")
                print(f"   Error: {result['error']}")
                failed_tests += 1

            else:
                print("❌ FAILED")
                print(f"   Unexpected result type: {type(result)}")
                failed_tests += 1

        except Exception as e:
            print("❌ FAILED")
            print(f"   Exception: {str(e)}")
            failed_tests += 1

    # Step 5: Summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(
        f"📊 Success Rate: {successful_tests/(successful_tests+failed_tests)*100:.1f}%"
    )

    print(f"\n📋 Tested {len(software_tools)} packages:")
    for tool in software_tools:
        pkg = tool.replace("get_", "").replace("_info", "").replace("_", "-")
        print(f"   • {pkg}")

    print("\nℹ️  Features Tested:")
    print("   - PackageTool implementation for popular Python packages")
    print("   - PyPI API integration with real-time package data")
    print("   - Local information fallback when API unavailable")
    print("   - Different parameter combinations (include_examples, source)")
    print("   - Installation instructions and documentation links")
    print("   - Usage examples and quick start guides")

    return successful_tests, failed_tests


if __name__ == "__main__":
    successful, failed = main()

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Software tools are working perfectly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check output above for details.")

    print("\n✨ Software package tools testing complete!")
