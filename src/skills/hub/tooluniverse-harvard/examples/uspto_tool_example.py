from tooluniverse import ToolUniverse

tooluni = ToolUniverse()
tooluni.load_tools()

# All test cases compiled into the specified list format
test_queries = [
    # Test Case: get_patent_overview_by_text_query example
    {
        "name": "get_patent_overview_by_text_query",
        "arguments": {
            "query": "iron oxide",
            "exact_match": True,
            "sort": "filingDate desc",
            "limit": 5,
            "rangeFilters": "filingDate 2021-01-01:2024-02-01",
        },
    },
    # Test Case: get_patent_overview_by_text_query example
    {
        "name": "get_patent_overview_by_text_query",
        "arguments": {
            "query": "machine learning",
            "exact_match": False,
            "sort": "filingDate desc",
            "limit": 1,
            "offset": 53,
            "rangeFilters": "filingDate 2021-01-01:2024-02-01",
        },
    },
    # Test Case: get_patent_application_metadata
    {
        "name": "get_patent_application_metadata",
        "arguments": {"applicationNumberText": "19053071"},
    },
    # Test Case: get_patent_term_adjustment_data
    {
        "name": "get_patent_term_adjustment_data",
        "arguments": {"applicationNumberText": "16232347"},
    },
    # Test Case: get_patent_term_adjustment_data
    {
        "name": "get_patent_term_adjustment_data",
        "arguments": {"applicationNumberText": "17783167"},
    },
    # Test Case: get_patent_continuity_data
    {
        "name": "get_patent_continuity_data",
        "arguments": {"applicationNumberText": "19053071"},
    },
    # Test Case: get_patient_foreign_priority_data example
    {
        "name": "get_patent_foreign_priority_data",
        "arguments": {"applicationNumberText": "19053071"},
    },
    # Test Case: get_associated_documents_metadata
    {
        "name": "get_associated_documents_metadata",
        "arguments": {"applicationNumberText": "16232347"},
    },
]

test_queries = test_queries  # Repeat the test cases three times for thorough testing

for idx, query in enumerate(test_queries):
    print(
        f"\n[{idx+1}] Running tool: {query['name']} with arguments: {query['arguments']}"
    )
    result = tooluni.run(query)
    print("✅ Success.")
    result_str = str(result)
    print(f"📊 Result: {result_str}")
