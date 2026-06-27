#!/usr/bin/env python3
"""
Dataset Tools Example

Demonstrates dataset-related tools available in ToolUniverse
"""

from tooluniverse import ToolUniverse

# =============================================================================
# Tool Initialization
# =============================================================================
# Description: Initialize ToolUniverse and load all available tools
# Syntax: tu = ToolUniverse(); tu.load_tools()
tu = ToolUniverse()
tu.load_tools()

# =============================================================================
# Method 1: DrugBank Vocabulary Search
# =============================================================================
# Description: Search DrugBank vocabulary by drug name
# Syntax: tu.run({"name": "drugbank_vocab_search", "arguments": {"query": "aspirin"}})
result1 = tu.run({
    "name": "drugbank_vocab_search",
    "arguments": {"query": "aspirin"}
})

# =============================================================================
# Method 2: Exact DrugBank ID Search
# =============================================================================
# Description: Search for exact DrugBank ID match
# Syntax: tu.run({"name": "drugbank_vocab_search", "arguments": {"query": "DB00001", "search_fields": ["DrugBank ID"], "exact_match": True}})
result2 = tu.run({
    "name": "drugbank_vocab_search",
    "arguments": {
        "query": "DB00001",
        "search_fields": ["DrugBank ID"],
        "exact_match": True
    }
})

# =============================================================================
# Method 3: Case-Sensitive Synonym Search
# =============================================================================
# Description: Search in synonyms with case sensitivity
# Syntax: tu.run({"name": "drugbank_vocab_search", "arguments": {"query": "Lepirudin", "search_fields": ["Synonyms", "Common name"], "case_sensitive": True, "limit": 10}})
result3 = tu.run({
    "name": "drugbank_vocab_search",
    "arguments": {
        "query": "Lepirudin",
        "search_fields": ["Synonyms", "Common name"],
        "case_sensitive": True,
        "limit": 10
    }
})

# =============================================================================
# Method 4: DrugBank Vocabulary Filter
# =============================================================================
# Description: Filter drugs based on field conditions
# Syntax: tu.run({"name": "drugbank_vocab_filter", "arguments": {"field": "CAS", "condition": "not_empty", "limit": 5}})
result4 = tu.run({
    "name": "drugbank_vocab_filter",
    "arguments": {
        "field": "CAS",
        "condition": "not_empty",
        "limit": 5
    }
})

# =============================================================================
# Method 5: DrugBank ID Pattern Filter
# =============================================================================
# Description: Filter drugs starting with specific pattern
# Syntax: tu.run({"name": "drugbank_vocab_filter", "arguments": {"field": "DrugBank ID", "condition": "starts_with", "value": "DB000", "limit": 10}})
result5 = tu.run({
    "name": "drugbank_vocab_filter",
    "arguments": {
        "field": "DrugBank ID",
        "condition": "starts_with",
        "value": "DB000",
        "limit": 10
    }
})

# =============================================================================
# Method 6: Common Name Contains Filter
# =============================================================================
# Description: Filter drugs containing specific text in common name
# Syntax: tu.run({"name": "drugbank_vocab_filter", "arguments": {"field": "Common name", "condition": "contains", "value": "interferon", "limit": 5}})
result6 = tu.run({
    "name": "drugbank_vocab_filter",
    "arguments": {
        "field": "Common name",
        "condition": "contains",
        "value": "interferon",
        "limit": 5
    }
})

# =============================================================================
# Method 7: Multi-Field Search
# =============================================================================
# Description: Search across multiple fields with complex parameters
# Syntax: tu.run({"name": "drugbank_vocab_search", "arguments": {"query": "insulin", "search_fields": ["Common name", "Synonyms"], "case_sensitive": False, "exact_match": False, "limit": 3}})
result7 = tu.run({
    "name": "drugbank_vocab_search",
    "arguments": {
        "query": "insulin",
        "search_fields": ["Common name", "Synonyms"],
        "case_sensitive": False,
        "exact_match": False,
        "limit": 3
    }
})

# =============================================================================
# Method 8: DrugBank Full Search
# =============================================================================
# Description: Comprehensive DrugBank search with partial matching
# Syntax: tu.run({"name": "drugbank_full_search", "arguments": {"query": "acetylsalicylic", "search_fields": ["name"], "limit": 5}})
result8 = tu.run({
    "name": "drugbank_full_search",
    "arguments": {
        "query": "acetylsalicylic",
        "search_fields": ["name"],
        "limit": 5
    }
})

# =============================================================================
# Method 9: DrugBank Links Search
# =============================================================================
# Description: Search DrugBank external links and identifiers
# Syntax: tu.run({"name": "drugbank_links_search", "arguments": {"query": "205923-56-4", "search_fields": ["CAS Number"], "exact_match": True}})
result9 = tu.run({
    "name": "drugbank_links_search",
    "arguments": {
        "query": "205923-56-4",
        "search_fields": ["CAS Number"],
        "exact_match": True
    }
})

# =============================================================================
# Method 10: DICT Search
# =============================================================================
# Description: Search using DICTrank database
# Syntax: tu.run({"name": "dict_search", "arguments": {"query": "ZYPREXA", "search_fields": ["Trade Name"], "limit": 2}})
result10 = tu.run({
    "name": "dict_search",
    "arguments": {
        "query": "ZYPREXA",
        "search_fields": ["Trade Name"],
        "limit": 2
    }
})

# =============================================================================
# Method 11: DILI Search
# =============================================================================
# Description: Search using DILIrank database for drug-induced liver injury
# Syntax: tu.run({"name": "dili_search", "arguments": {"query": "acetaminophen", "search_fields": ["Compound Name"], "exact_match": True}})
result11 = tu.run({
    "name": "dili_search",
    "arguments": {
        "query": "acetaminophen",
        "search_fields": ["Compound Name"],
        "exact_match": True
    }
})

# =============================================================================
# Method 12: DIQTA Search
# =============================================================================
# Description: Search using DIQTA database
# Syntax: tu.run({"name": "diqt_search", "arguments": {"query": "DB00637", "search_fields": ["DrugBank ID"], "exact_match": True}})
result12 = tu.run({
    "name": "diqt_search",
    "arguments": {
        "query": "DB00637",
        "search_fields": ["DrugBank ID"],
        "exact_match": True
    }
})

# =============================================================================
# Method 13: Result Processing
# =============================================================================
# Description: Process and analyze dataset search results
# Syntax: Check result structure and extract relevant information

def process_dataset_result(result, tool_name):
    """Process dataset search results"""
    if isinstance(result, dict):
        if "error" in result:
            # Handle error response
            return False, f"Error: {result['error']}"
        elif "results" in result:
            # Process search results
            results = result["results"]
            total_results = result.get('total_results', result.get('total_matches', 0))
            return True, f"Found {total_results} results"
        else:
            # Process other result types
            return True, "Search completed successfully"
    else:
        # Handle non-dictionary results
        return False, "Unexpected result format"

# Process results
success1, message1 = process_dataset_result(result1, "drugbank_vocab_search")
success2, message2 = process_dataset_result(result2, "drugbank_vocab_search")
success3, message3 = process_dataset_result(result3, "drugbank_vocab_search")

# =============================================================================
# Method 14: Error Handling
# =============================================================================
# Description: Handle errors in dataset tool execution
# Syntax: Check for errors and handle appropriately

def handle_dataset_error(result, tool_name):
    """Handle errors from dataset tools"""
    if isinstance(result, dict):
        if "error" in result:
            error_message = result["error"]
            # Handle specific error types
            if "not found" in error_message.lower():
                # Handle query not found errors
                pass
            elif "invalid" in error_message.lower():
                # Handle invalid parameter errors
                pass
            else:
                # Handle other errors
                pass
            return False, error_message
        else:
            return True, "Success"
    return False, "Invalid result format"

# Handle errors for each result
success1, message1 = handle_dataset_error(result1, "drugbank_vocab_search")
success2, message2 = handle_dataset_error(result2, "drugbank_vocab_search")
success3, message3 = handle_dataset_error(result3, "drugbank_vocab_search")

# =============================================================================
# Method 15: Batch Processing
# =============================================================================
# Description: Process multiple dataset queries in sequence
# Syntax: Loop through multiple tool calls

dataset_queries = [
    {
        "name": "drugbank_vocab_search",
        "arguments": {
            "query": "metformin",
            "limit": 3
        }
    },
    {
        "name": "drugbank_vocab_filter",
        "arguments": {
            "field": "Common name",
            "condition": "contains",
            "value": "insulin",
            "limit": 2
        }
    }
]

batch_results = []
for query in dataset_queries:
    try:
        result = tu.run(query)
        batch_results.append(result)
    except Exception as e:
        # Handle individual query failures
        batch_results.append({"error": str(e)})

# =============================================================================
# Summary of Dataset Tools
# =============================================================================
# Available dataset tools provide access to various drug and chemical databases:
# - drugbank_vocab_search: Search DrugBank vocabulary
# - drugbank_vocab_filter: Filter DrugBank entries by field conditions
# - drugbank_full_search: Comprehensive DrugBank search
# - drugbank_links_search: Search DrugBank external links
# - dict_search: Search DICTrank database
# - dili_search: Search DILIrank database
# - diqt_search: Search DIQTA database
# 
# Common search parameters:
# - query: Search term or identifier
# - search_fields: Fields to search in
# - exact_match: Whether to require exact matches
# - case_sensitive: Whether search is case sensitive
# - limit: Maximum number of results
# 
# Filter parameters:
# - field: Field to filter on
# - condition: Filter condition (not_empty, starts_with, contains, etc.)
# - value: Value to filter by
# - limit: Maximum number of results
# 
# Result structures:
# - Most tools return "results" array with matching entries
# - Results include total count and individual entries
# - Each entry contains relevant fields and metadata
# 
# Error handling:
# - Check for "error" key in dictionary responses
# - Handle query not found errors
# - Validate input parameters before calling tools
# - Use appropriate search fields for each tool
# 
# Performance considerations:
# - Use limits to control result size
# - Choose appropriate search fields for efficiency
# - Consider exact_match for precise lookups
# - Use batch processing for multiple queries
# 
# Use cases:
# - Drug information retrieval
# - Chemical database searches
# - Drug safety analysis
# - Pharmacological research
# - Drug interaction studies