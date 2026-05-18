from tooluniverse import ToolUniverse

# Step 1: Initialize tool universe
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define test queries for the opentargets tool
test_queries = [
    {"name": "Tool_Finder", "arguments": {"diseaseName": "Bardet-Biedl syndrome"}},
    {
        "name": "OpenTargets_get_drug_adverse_events_by_chemblId",
        "arguments": {"chemblId": "CHEMBL980"},
    },
]

# Step 3: Run all test queries
for idx, query in enumerate(test_queries):
    # try:
    print(
        f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
    )
    result = tooluni.run(query)
    print("✅ Success. Example output snippet:")
    print(
        result if isinstance(result, dict) else str(result)
    )  # Print snippet if result is big
# except Exception as e:
#     print(f"❌ Failed. Error: {str(e)}")
