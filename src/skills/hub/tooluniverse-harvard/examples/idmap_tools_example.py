"""
Concise Test Script - OpenTargets ID Mapping Tools
Test three main ID mapping tools:
1. Get disease IDs by name
2. Get cross-reference IDs by EFO ID
3. Bidirectional mapping between external IDs and diseases
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize tools
    print("🔧 Initializing ToolUniverse...")
    tooluni = ToolUniverse()
    tooluni.load_tools()
    print("✅ Tools loaded successfully\n")

    # Test cases
    test_cases = [
        {
            "name": "OpenTargets_get_disease_ids_by_name",
            "arguments": {"name": "neuroblastoma"},
            "description": "Get disease IDs by name",
        },
        {
            "name": "OpenTargets_get_disease_ids_by_efoId",
            "arguments": {"efoId": "EFO_0000621"},
            "description": "Get cross-references by EFO ID",
        },
        {
            "name": "OpenTargets_map_any_disease_id_to_all_other_ids",
            "arguments": {"inputId": "EFO_0000621"},
            "description": "Map disease ID to all other IDs",
        },
    ]

    # Run tests
    print("🧪 Starting ID Mapping tools tests:\n")

    for i, test in enumerate(test_cases, 1):
        print(f"[{i}] {test['description']}")
        print(f"    Tool: {test['name']}")
        print(f"    Arguments: {test['arguments']}")

        try:
            result = tooluni.run(test)
            if result:
                print("    ✅ Success")
                print(f"    📊 Result: {str(result)}")
            else:
                print("    ⚠️  No data returned")
        except Exception as e:
            print(f"    ❌ Failed: {str(e)}")
        print()

    print("🎉 Testing completed!")


if __name__ == "__main__":
    main()
