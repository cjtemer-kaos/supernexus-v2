# test_dailymed.py

from tooluniverse import ToolUniverse

# === test_dailymed.py ===

# Step 1: Initialize ToolUniverse and load all tools (including our DailyMed tools)
tooluni = ToolUniverse()
tooluni.load_tools()

# Step 2: Define test queries for DailyMed tools
# NOTE: Before running this script, please confirm that "DailyMed_search_spls" call returns at least one data element,
#       and extract a valid setid from it. Then replace the example setid below to avoid 404 or 415 errors.

test_queries = [
    # ---- Tests for DailyMed_search_spls ----
    # 1. Only pass drug_name, use default pagesize=100, page=1
    {
        "name": "DailyMed_search_spls",
        "arguments": {"drug_name": "TAMSULOSIN HYDROCHLORIDE"},
    },
    # 2. Specify drug_name + pagesize=2, check if returns no more than 2 records
    {
        "name": "DailyMed_search_spls",
        "arguments": {"drug_name": "TAMSULOSIN HYDROCHLORIDE", "pagesize": 2},
    },
    # 3. Use published_date filter to get recent records
    {
        "name": "DailyMed_search_spls",
        "arguments": {
            "drug_name": "TAMSULOSIN HYDROCHLORIDE",
            "published_date_gte": "2025-05-01",
            "pagesize": 3,
        },
    },
    # ---- Tests for DailyMed_get_spl_by_setid ----
    # 4. Use setid from first record above (example setid), request XML format
    {
        "name": "DailyMed_get_spl_by_setid",
        "arguments": {
            # Example setid, please replace with actual first setid from query
            "setid": "35bbb655-19e2-00c2-e063-6394a90afbe3",
            "format": "xml",
        },
    },
]

# Step 3: Iterate over all test queries and print results
for idx, query in enumerate(test_queries):
    name = query["name"]
    args = query["arguments"]
    print(f"\n[{idx+1}] Running tool: {name} with arguments: {args}")
    try:
        result = tooluni.run(query)
        # Print brief results: if dict, print first few lines; otherwise print first 500 chars
        if isinstance(result, dict):
            # If contains 'error' key, print complete error dict; otherwise print first 500 chars
            if "error" in result:
                print("❌ Error returned:", result)
            else:
                snippet = str(result)[:500]
                print("✅ Success. Result snippet (first 500 chars):")
                print(snippet)
        else:
            snippet = str(result)[:500]
            print("✅ Success. Result snippet (first 500 chars):")
            print(snippet)
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
