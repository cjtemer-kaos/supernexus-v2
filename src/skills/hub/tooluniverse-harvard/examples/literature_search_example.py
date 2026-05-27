#!/usr/bin/env python3
"""
Literature Search Tools Example

Demonstrates literature search tools available in ToolUniverse for finding
academic papers and preprints.
"""

from tooluniverse import ToolUniverse
import time

# =============================================================================
# Tool Initialization
# =============================================================================
# Description: Initialize ToolUniverse and load all available tools
# Syntax: tu = ToolUniverse(); tu.load_tools()
tu = ToolUniverse()
tu.load_tools()

# =============================================================================
# Method 1: ArXiv Preprint Search
# =============================================================================
# Description: Search for preprints on ArXiv repository
# Syntax: tu.run({
#   "name": "ArXiv_search_papers",
#   "arguments": {"query": "machine learning", "limit": 2,
#                  "sort_by": "relevance"}
# })
result1 = tu.run({
    "name": "ArXiv_search_papers",
    "arguments": {
        "query": "machine learning",
        "limit": 2,
        "sort_by": "relevance",
    },
})

# =============================================================================
# Method 2: PubMed Article Search
# =============================================================================
# Description: Search for articles in PubMed database
# Syntax: tu.run({
#   "name": "PubMed_search_articles",
#   "arguments": {"query": "cancer immunotherapy", "limit": 2,
#                  "sort_by": "relevance"}
# })
result2 = tu.run({
    "name": "PubMed_search_articles",
    "arguments": {
        "query": "cancer immunotherapy",
        "limit": 2,
        "sort_by": "relevance",
    },
})

# =============================================================================
# Method 3: EuropePMC Article Search
# =============================================================================
# Description: Search for articles in EuropePMC database
# Syntax: tu.run({
#   "name": "EuropePMC_search_articles",
#   "arguments": {"query": "COVID-19 vaccine", "limit": 2}
# })
result3 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {"query": "COVID-19 vaccine", "limit": 2},
})

# =============================================================================
# Method 4: Performance Timing
# =============================================================================
# Description: Measure execution time for search operations
# Syntax:
# start_time = time.time(); result = tu.run(...); end_time = time.time()
start_time = time.time()
result4 = tu.run({
    "name": "ArXiv_search_papers",
    "arguments": {"query": "artificial intelligence", "limit": 1},
})
end_time = time.time()
execution_time = end_time - start_time
ok_flag = isinstance(result4, (list, dict))
print(f"Timing: {execution_time:.2f}s, ok={ok_flag}")

# =============================================================================
# Method 5: Error Handling and Timeout Management
# =============================================================================
# Description: Handle potential errors and timeouts in search operations
# Syntax: try/except blocks around search calls
try:
    _ = tu.run({
        "name": "ArXiv_search_papers",
        "arguments": {
            "query": "complex query that might timeout",
            "limit": 100,
        },
    })
except Exception as e:
    if "timeout" in str(e).lower():
        print("Timeout handled")
    else:
        print("Other error handled")

# =============================================================================
# Method 6: Result Processing
# =============================================================================
# Description: Process and analyze search results
# Syntax: Check result structure and extract relevant information

# Process ArXiv results
if isinstance(result1, dict) and "papers" in result1:
    papers = result1["papers"]
    print(f"ArXiv papers: {len(papers)}")

# Process PubMed results
if isinstance(result2, dict) and "articles" in result2:
    pm_articles = result2["articles"]
    print(f"PubMed articles: {len(pm_articles)}")

# Process EuropePMC results
if isinstance(result3, dict) and "articles" in result3:
    epmc_articles = result3["articles"]
    print(f"EuropePMC articles: {len(epmc_articles)}")

# =============================================================================
# Method 7: Batch Search Operations
# =============================================================================
# Description: Perform multiple searches in sequence
# Syntax: Loop through multiple search queries
search_queries = [
    {
        "name": "ArXiv_search_papers",
        "arguments": {"query": "deep learning", "limit": 1},
    },
    {
        "name": "PubMed_search_articles",
        "arguments": {"query": "neural networks", "limit": 1},
    },
    {
        "name": "EuropePMC_search_articles",
        "arguments": {"query": "machine learning", "limit": 1},
    },
]

batch_results = []
for q in search_queries:
    try:
        res = tu.run(q)
        batch_results.append(res)
    except Exception as e:
        batch_results.append({"error": str(e)})

# =============================================================================
# Method 8: Search Parameter Optimization
# =============================================================================
# Description: Optimize search parameters for better results
# Syntax: Adjust limit, sort_by, and other parameters

# Small limit for quick testing
quick_result = tu.run({
    "name": "ArXiv_search_papers",
    "arguments": {
        "query": "quantum computing",
        "limit": 1,
        "sort_by": "relevance",
    },
})

# Larger limit for comprehensive results
comprehensive_result = tu.run({
    "name": "ArXiv_search_papers",
    "arguments": {
        "query": "quantum computing",
        "limit": 10,
        "sort_by": "relevance",
    },
})

# =============================================================================
# Method 9: Result Validation
# =============================================================================
# Description: Validate search results and check for errors
# Syntax: Check result structure and error conditions


def validate_search_result(result, tool_name):
    """Validate search result structure and content"""
    if isinstance(result, dict):
        if "error" in result:
            return False, f"Error in {tool_name}: {result['error']}"
        if "papers" in result or "articles" in result:
            return True, "Search completed successfully"
        return False, f"Unexpected result structure from {tool_name}"
    return False, f"Unexpected result type from {tool_name}"


# Validate results
is_valid, message = validate_search_result(result1, "ArXiv_search_papers")
print(f"Validation: {message}")
is_valid, message = validate_search_result(result2, "PubMed_search_articles")
print(f"Validation: {message}")
is_valid, message = validate_search_result(
    result3, "EuropePMC_search_articles"
)
print(f"Validation: {message}")

# =============================================================================
# Summary of Literature Search Tools
# =============================================================================
# Available literature search tools provide access to multiple academic
# databases:
# - ArXiv: Preprints and early research papers
# - PubMed: Biomedical and life sciences literature
# - EuropePMC: European biomedical literature database
#
# Common search parameters:
# - query: Search terms or keywords
# - limit: Maximum number of results to return
# - sort_by: Sorting criteria (relevance, date, etc.)
#
# Result structures:
# - ArXiv: Returns "papers" array with title, authors, abstract, etc.
# - PubMed: Returns "articles" array with title, abstract, authors, etc.
# - EuropePMC: Returns "articles" array with similar structure
#
# Error handling:
# - Check for "error" key in dictionary responses
# - Handle timeout exceptions for large searches
# - Validate result structure before processing
# - Use appropriate limits to avoid timeouts
#
# Performance considerations:
# - Start with small limits for testing
# - Use timing to measure search performance
# - Consider batch operations for multiple queries
# - Handle individual query failures gracefully

# =============================================================================
# Quick Run-All (Minimal Arguments)
# =============================================================================
# Description: Smoke test of multiple literature tools with minimal arguments
quick_tools = [
    ("ArXiv_search_papers", {"query": "machine learning"}),
    ("EuropePMC_search_articles", {"query": "machine learning"}),
    ("openalex_literature_search", {"search_keywords": "machine learning"}),
    ("PubMed_search_articles", {"query": "machine learning"}),
    ("SemanticScholar_search_papers", {"query": "machine learning"}),
    ("PMC_search_papers", {"query": "machine learning"}),
]

for name, args in quick_tools:
    print(f"\n=== Running {name} ===")
    try:
        res = tu.run_one_function({
            "name": name,
            "arguments": args,
        })
        status = "OK" if isinstance(res, (list, dict)) else "UNKNOWN"
        print(status)
    except Exception as err:
        print(f"ERR: {err}")
