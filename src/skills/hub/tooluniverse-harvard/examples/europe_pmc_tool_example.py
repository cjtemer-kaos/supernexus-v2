#!/usr/bin/env python3
"""
EuropePMC Tool Example

Demonstrates EuropePMC literature search tools available in ToolUniverse
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
# Method 1: Basic Article Search
# =============================================================================
# Description: Search for articles using basic query
# Syntax: tu.run({"name": "EuropePMC_search_articles", "arguments": {"query": "cancer immunotherapy", "limit": 3}})
result1 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "cancer immunotherapy",
        "limit": 3
    }
})

# =============================================================================
# Method 2: Advanced Search with Filters
# =============================================================================
# Description: Search with additional filtering parameters
# Syntax: tu.run({"name": "EuropePMC_search_articles", "arguments": {"query": "machine learning", "limit": 5, "sort_by": "relevance"}})
result2 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "machine learning",
        "limit": 5,
        "sort_by": "relevance"
    }
})

# =============================================================================
# Method 3: Date Range Search
# =============================================================================
# Description: Search articles within specific date range
# Syntax: tu.run({"name": "EuropePMC_search_articles", "arguments": {"query": "COVID-19", "limit": 3, "from_date": "2020-01-01", "to_date": "2021-12-31"}})
result3 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "COVID-19",
        "limit": 3,
        "from_date": "2020-01-01",
        "to_date": "2021-12-31"
    }
})

# =============================================================================
# Method 4: Author-Specific Search
# =============================================================================
# Description: Search for articles by specific author
# Syntax: tu.run({"name": "EuropePMC_search_articles", "arguments": {"query": "Smith", "limit": 2, "search_fields": ["author"]}})
result4 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "Smith",
        "limit": 2,
        "search_fields": ["author"]
    }
})

# =============================================================================
# Method 5: Journal-Specific Search
# =============================================================================
# Description: Search within specific journal
# Syntax: tu.run({"name": "EuropePMC_search_articles", "arguments": {"query": "neuroscience", "limit": 3, "journal": "Nature"}})
result5 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "neuroscience",
        "limit": 3,
        "journal": "Nature"
    }
})

# =============================================================================
# Method 6: Abstract-Only Search
# =============================================================================
# Description: Search only in article abstracts
# Syntax: tu.run({"name": "EuropePMC_search_articles", "arguments": {"query": "artificial intelligence", "limit": 2, "search_fields": ["abstract"]}})
result6 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "artificial intelligence",
        "limit": 2,
        "search_fields": ["abstract"]
    }
})

# =============================================================================
# Method 7: Full Text Search
# =============================================================================
# Description: Search in full text of articles
# Syntax: tu.run({"name": "EuropePMC_search_articles", "arguments": {"query": "deep learning", "limit": 2, "search_fields": ["fulltext"]}})
result7 = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "deep learning",
        "limit": 2,
        "search_fields": ["fulltext"]
    }
})

# =============================================================================
# Method 8: Result Processing
# =============================================================================
# Description: Process and analyze EuropePMC search results
# Syntax: Check result structure and extract relevant information

def process_europepmc_result(result):
    """Process EuropePMC search results"""
    if isinstance(result, dict):
        if "error" in result:
            # Handle error response
            return False, f"Error: {result['error']}"
        elif "articles" in result:
            # Process article results
            articles = result["articles"]
            return True, f"Found {len(articles)} articles"
        else:
            # Process other result types
            return True, "Search completed successfully"
    else:
        # Handle non-dictionary results
        return False, "Unexpected result format"

# Process results
success1, message1 = process_europepmc_result(result1)
success2, message2 = process_europepmc_result(result2)
success3, message3 = process_europepmc_result(result3)

# =============================================================================
# Method 9: Article Information Extraction
# =============================================================================
# Description: Extract specific information from article results
# Syntax: Access specific fields from result data

def extract_article_info(result):
    """Extract key information from article results"""
    if not isinstance(result, dict) or "articles" not in result:
        return {}
    
    articles = result["articles"]
    if not articles:
        return {}
    
    first_article = articles[0]
    return {
        'title': first_article.get('title', 'N/A'),
        'authors': first_article.get('authors', 'N/A'),
        'journal': first_article.get('journal', 'N/A'),
        'year': first_article.get('year', 'N/A'),
        'abstract': first_article.get('abstract', 'N/A')[:200] + '...' if first_article.get('abstract') else 'N/A'
    }

# Extract information from results
article_info1 = extract_article_info(result1)
article_info2 = extract_article_info(result2)
article_info3 = extract_article_info(result3)

# =============================================================================
# Method 10: Error Handling
# =============================================================================
# Description: Handle errors in EuropePMC tool execution
# Syntax: Check for errors and handle appropriately

def handle_europepmc_error(result, tool_name):
    """Handle errors from EuropePMC tools"""
    if isinstance(result, dict):
        if "error" in result:
            error_message = result["error"]
            # Handle specific error types
            if "timeout" in error_message.lower():
                # Handle timeout errors
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
success1, message1 = handle_europepmc_error(result1, "EuropePMC_search_articles")
success2, message2 = handle_europepmc_error(result2, "EuropePMC_search_articles")
success3, message3 = handle_europepmc_error(result3, "EuropePMC_search_articles")

# =============================================================================
# Method 11: Batch Processing
# =============================================================================
# Description: Process multiple EuropePMC queries in sequence
# Syntax: Loop through multiple tool calls

europepmc_queries = [
    {
        "name": "EuropePMC_search_articles",
        "arguments": {
            "query": "bioinformatics",
            "limit": 2
        }
    },
    {
        "name": "EuropePMC_search_articles",
        "arguments": {
            "query": "genomics",
            "limit": 2
        }
    }
]

batch_results = []
for query in europepmc_queries:
    try:
        result = tu.run(query)
        batch_results.append(result)
    except Exception as e:
        # Handle individual query failures
        batch_results.append({"error": str(e)})

# =============================================================================
# Method 12: Search Parameter Optimization
# =============================================================================
# Description: Optimize search parameters for better results
# Syntax: Adjust limit, sort_by, and other parameters

# Small limit for quick testing
quick_result = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "pharmacology",
        "limit": 1
    }
})

# Larger limit for comprehensive results
comprehensive_result = tu.run({
    "name": "EuropePMC_search_articles",
    "arguments": {
        "query": "pharmacology",
        "limit": 10
    }
})

# =============================================================================
# Summary of EuropePMC Tools
# =============================================================================
# Available EuropePMC tools provide literature search capabilities:
# - EuropePMC_search_articles: Search for articles in EuropePMC database
# 
# Common search parameters:
# - query: Search terms or keywords
# - limit: Maximum number of results to return
# - sort_by: Sorting criteria (relevance, date, etc.)
# - from_date, to_date: Date range filters
# - search_fields: Fields to search in (title, abstract, fulltext, author)
# - journal: Filter by specific journal
# 
# Search field options:
# - title: Search in article titles
# - abstract: Search in article abstracts
# - fulltext: Search in full article text
# - author: Search by author names
# 
# Result structures:
# - Results contain "articles" array with matching articles
# - Each article includes: title, authors, journal, year, abstract, etc.
# - Results may include metadata like total count
# 
# Error handling:
# - Check for "error" key in dictionary responses
# - Handle timeout errors for complex queries
# - Validate input parameters before calling tools
# - Use appropriate limits to avoid timeouts
# 
# Performance considerations:
# - Start with small limits for testing
# - Use specific search fields for better performance
# - Consider date ranges to limit search scope
# - Use batch processing for multiple queries
# 
# Use cases:
# - Literature research and review
# - Academic paper discovery
# - Research trend analysis
# - Author and journal tracking
# - Scientific content analysis