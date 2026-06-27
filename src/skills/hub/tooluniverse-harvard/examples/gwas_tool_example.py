# test_gwas_tool.py

from tooluniverse import ToolUniverse

# Step 1: Initialize ToolUniverse and load all tools (including GWAS tools)
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define test queries for GWAS tools based on the examples
test_queries = [
    # Test basic association search (Question 1 from examples)
    {
        "name": "gwas_search_associations",
        "arguments": {"efo_trait": "type 2 diabetes mellitus", "size": 10},
    },
    # Test study search (Question 2 from examples)
    {
        "name": "gwas_search_studies",
        "arguments": {"disease_trait": "type 2 diabetes", "cohort": "UKB", "size": 20},
    },
    # Test SNP search (Question 3 from examples)
    {
        "name": "gwas_search_associations",
        "arguments": {
            "rs_id": "rs1050316",
            "sort": "p_value",
            "direction": "asc",
            "size": 10,
        },
    },
    # Test gene-based SNP search (Question 10 from examples)
    {"name": "gwas_search_snps", "arguments": {"mapped_gene": "HBS1L", "size": 10}},
    # Test specialized tools
    {
        "name": "gwas_get_variants_for_trait",
        "arguments": {"efo_trait": "type 2 diabetes mellitus", "size": 5},
    },
    {
        "name": "gwas_get_associations_for_trait",
        "arguments": {"efo_trait": "type 2 diabetes mellitus", "size": 5},
    },
    {
        "name": "gwas_get_associations_for_snp",
        "arguments": {"rs_id": "rs1050316", "size": 5},
    },
    {
        "name": "gwas_get_studies_for_trait",
        "arguments": {"efo_trait": "type 2 diabetes mellitus", "size": 5},
    },
    {
        "name": "gwas_get_snps_for_gene",
        "arguments": {"mapped_gene": "HBS1L", "size": 5},
    },
    # Test get by ID tools
    {"name": "gwas_get_study_by_id", "arguments": {"study_id": "GCST000001"}},
    {"name": "gwas_get_snp_by_id", "arguments": {"rs_id": "rs429358"}},
    # Test studies with summary statistics (Question 9 from examples)
    {
        "name": "gwas_get_studies_for_trait",
        "arguments": {
            "efo_trait": "type 2 diabetes mellitus",
            "full_pvalue_set": True,
            "size": 5,
        },
    },
    # Test GxE studies (Question 11 from examples)
    {
        "name": "gwas_get_studies_for_trait",
        "arguments": {
            "efo_trait": "total blood protein measurement",
            "gxe": True,
            "size": 5,
        },
    },
]


def format_value(value, max_items=10, max_length=5000):
    """Helper function to format output values"""
    if isinstance(value, dict):
        if "error" in value:
            return f"ERROR: {value['error']}"

        # Show the structure of the response
        if "data" in value and "metadata" in value:
            result = "Response Structure:\n"
            result += f"  Data: {len(value['data'])} items\n"
            if value["metadata"]:
                result += f"  Metadata: {value['metadata']}\n"

            # Show first few data items
            if value["data"]:
                result += f"\nFirst {min(max_items, len(value['data']))} data items:\n"
                for i, item in enumerate(value["data"][:max_items]):
                    item_str = str(item)
                    if len(item_str) > max_length:
                        item_str = item_str[:max_length] + "..."
                    result += f"  [{i+1}] {item_str}\n"

                if len(value["data"]) > max_items:
                    result += f"  ... and {len(value['data']) - max_items} more items\n"

            return result
        else:
            # Fallback for non-structured responses
            dict_str = str(value)
            return f"Dict ({len(dict_str)} chars): {dict_str[:max_length]}{'...' if len(dict_str) > max_length else ''}"
    elif isinstance(value, list):
        if not value:
            return "Empty list"
        items_to_show = value[:max_items]
        items_str = "\n  - ".join(
            [
                str(item)[:max_length] + ("..." if len(str(item)) > max_length else "")
                for item in items_to_show
            ]
        )
        remaining = len(value) - max_items
        return f"List with {len(value)} items:\n  - {items_str}" + (
            f"\n  ... and {remaining} more items" if remaining > 0 else ""
        )
    elif isinstance(value, str):
        return f"String ({len(value)} chars): {value[:max_length]}{'...' if len(value) > max_length else ''}"
    else:
        return f"Type: {type(value)}, Value: {value}"


# Step 3: Run all test queries
for idx, query in enumerate(test_queries, 1):
    print(
        f"\n{'='*80}\n[{idx}] Running tool: {query['name']} with arguments: {query['arguments']}"
    )
    try:
        result = tooluni.run(query)
        print("✅ Success. Output:")
        print(format_value(result))
    except (ImportError, AttributeError, KeyError, ValueError) as e:
        print(f"❌ Failed. Error: {str(e)}")
    print()
