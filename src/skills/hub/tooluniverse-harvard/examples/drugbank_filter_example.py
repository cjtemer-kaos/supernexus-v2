from tooluniverse import ToolUniverse
from typing import Any, Dict, List
import json

# Initialize tool universe
tooluni = ToolUniverse()
tooluni.load_tools()

print("=== DrugBank Filter Tool Usage Examples ===\n")

# 详细的使用示例，展示如何使用各种过滤器
filter_examples: List[Dict[str, Any]] = [
    {
        "name": "Example 1: Find all insulin-related drugs",
        "query": {
            "name": "drugbank_filter",
            "arguments": {
                "filters": {"Common name": {"contains": "insulin"}},
                "limit": 5,
            },
        },
    },
    {
        "name": "Example 2: Find drugs with specific DrugBank ID pattern",
        "query": {
            "name": "drugbank_filter",
            "arguments": {
                "filters": {"DrugBank ID": {"starts_with": "DB001"}},
                "limit": 5,
            },
        },
    },
    {
        "name": "Example 3: Find drugs with CAS numbers (quality check)",
        "query": {
            "name": "drugbank_filter",
            "arguments": {"filters": {"CAS": {"not_empty": True}}, "limit": 3},
        },
    },
    {
        "name": "Example 4: Find interferon drugs with UNII identifiers",
        "query": {
            "name": "drugbank_filter",
            "arguments": {
                "filters": {
                    "Common name": {"contains": "interferon"},
                    "UNII": {"not_empty": True},
                },
                "limit": 3,
            },
        },
    },
    {
        "name": "Example 5: Find drugs ending with 'acid'",
        "query": {
            "name": "drugbank_filter",
            "arguments": {
                "filters": {"Common name": {"ends_with": "acid"}},
                "limit": 4,
            },
        },
    },
    {
        "name": "Example 6: Simple string filter (aspirin in synonyms)",
        "query": {
            "name": "drugbank_filter",
            "arguments": {"filters": {"Synonyms": "aspirin"}, "limit": 3},
        },
    },
    {
        "name": "Example 7: Exact drug name match",
        "query": {
            "name": "drugbank_filter",
            "arguments": {
                "filters": {"Common name": {"exact": "Lepirudin"}},
                "limit": 5,
            },
        },
    },
    {
        "name": "Example 8: Complex multi-field filter",
        "query": {
            "name": "drugbank_filter",
            "arguments": {
                "filters": {
                    "DrugBank ID": {"starts_with": "DB00"},
                    "CAS": {"not_empty": True},
                    "Common name": {"contains": "alfa"},
                },
                "limit": 3,
            },
        },
    },
]

for idx, example in enumerate(filter_examples, 1):
    print(f"[{idx}] {example['name']}")
    print("Filter Arguments:")
    print(json.dumps(example["query"]["arguments"], indent=2, ensure_ascii=False))

    try:
        result = tooluni.run(example["query"])

        if isinstance(result, dict) and "results" in result:
            total = result.get("total_matches", 0)
            returned = result.get("returned_results", 0)
            print(f"✅ Success: Found {total} matches, showing {returned} results")

            # Show first result details
            if result["results"]:
                first = result["results"][0]
                print(
                    f"   First result: {first.get('Common name', 'N/A')} (ID: {first.get('DrugBank ID', 'N/A')})"
                )
                if first.get("CAS"):
                    print(f"   CAS: {first['CAS']}")
                if first.get("UNII"):
                    print(f"   UNII: {first['UNII']}")
                if first.get("Synonyms"):
                    synonyms = (
                        first["Synonyms"][:100] + "..."
                        if len(first["Synonyms"]) > 100
                        else first["Synonyms"]
                    )
                    print(f"   Synonyms: {synonyms}")

            # Show applied filters
            if "applied_filters" in result:
                print(f"   Applied filters: {', '.join(result['applied_filters'])}")

        elif isinstance(result, dict) and "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print("❌ Unexpected result format")

    except Exception as e:
        print(f"❌ Exception: {e}")

    print("-" * 80)

print("\n=== Filter Usage Summary ===")
print(
    """
Common Filter Patterns:

1. Simple String Matching:
   {"field_name": "search_text"}

2. Contains Pattern:
   {"field_name": {"contains": "text"}}

3. Starts With Pattern:
   {"field_name": {"starts_with": "prefix"}}

4. Ends With Pattern:
   {"field_name": {"ends_with": "suffix"}}

5. Exact Match:
   {"field_name": {"exact": "exact_value"}}

6. Data Quality Check:
   {"field_name": {"not_empty": true}}

7. Multiple Conditions (AND logic):
   {
     "field1": {"contains": "text1"},
     "field2": {"not_empty": true}
   }

Available Fields:
- DrugBank ID
- Common name
- CAS
- UNII
- Synonyms
- Accession Numbers
- Standard InChI Key
"""
)
