#!/usr/bin/env python3
"""
Chemistry Tools Example

Demonstrates chemistry-related tools available in ToolUniverse
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
# Method 1: ChEMBL Similar Molecule Search
# =============================================================================
# Description: Search for molecules similar to a reference compound
# Syntax: tu.run({"name": "ChEMBL_search_similar_molecules", "arguments": {"query": "compound_name", "similarity_threshold": 70, "max_results": 20}})
result1 = tu.run({
    "name": "ChEMBL_search_similar_molecules",
    "arguments": {
        "query": "Gadavist",
        "similarity_threshold": 70,
        "max_results": 20
    }
})

# =============================================================================
# Method 2: Basic Similarity Search
# =============================================================================
# Description: Search with default parameters
# Syntax: tu.run({"name": "ChEMBL_search_similar_molecules", "arguments": {"query": "aspirin"}})
result2 = tu.run({
    "name": "ChEMBL_search_similar_molecules",
    "arguments": {"query": "aspirin"}
})

# =============================================================================
# Method 3: High Similarity Threshold Search
# =============================================================================
# Description: Search with high similarity threshold for very similar compounds
# Syntax: tu.run({"name": "ChEMBL_search_similar_molecules", "arguments": {"query": "aspirin", "similarity_threshold": 90}})
result3 = tu.run({
    "name": "ChEMBL_search_similar_molecules",
    "arguments": {
        "query": "aspirin",
        "similarity_threshold": 90
    }
})

# =============================================================================
# Method 4: Limited Results Search
# =============================================================================
# Description: Search with limited number of results
# Syntax: tu.run({"name": "ChEMBL_search_similar_molecules", "arguments": {"query": "aspirin", "max_results": 5}})
result4 = tu.run({
    "name": "ChEMBL_search_similar_molecules",
    "arguments": {
        "query": "aspirin",
        "max_results": 5
    }
})

# =============================================================================
# Method 5: Combined Parameters Search
# =============================================================================
# Description: Search with both similarity threshold and result limit
# Syntax: tu.run({"name": "ChEMBL_search_similar_molecules", "arguments": {"query": "aspirin", "similarity_threshold": 85, "max_results": 3}})
result5 = tu.run({
    "name": "ChEMBL_search_similar_molecules",
    "arguments": {
        "query": "aspirin",
        "similarity_threshold": 85,
        "max_results": 3
    }
})

# =============================================================================
# Method 6: SMILES Structure Search
# =============================================================================
# Description: Search using SMILES molecular structure notation
# Syntax: tu.run({"name": "ChEMBL_search_similar_molecules", "arguments": {"query": "CC(=O)OC1=CC=CC=C1C(=O)O", "similarity_threshold": 80, "max_results": 10}})
result6 = tu.run({
    "name": "ChEMBL_search_similar_molecules",
    "arguments": {
        "query": "CC(=O)OC1=CC=CC=C1C(=O)O",  # SMILES for aspirin
        "similarity_threshold": 80,
        "max_results": 10
    }
})

# =============================================================================
# Method 7: Drug Name Search
# =============================================================================
# Description: Search using drug trade names
# Syntax: tu.run({"name": "ChEMBL_search_similar_molecules", "arguments": {"query": "FENOFIBRATE", "similarity_threshold": 70, "max_results": 20}})
result7 = tu.run({
    "name": "ChEMBL_search_similar_molecules",
    "arguments": {
        "query": "FENOFIBRATE",
        "similarity_threshold": 70,
        "max_results": 20
    }
})

# =============================================================================
# Method 8: Result Processing
# =============================================================================
# Description: Process and analyze ChEMBL search results
# Syntax: Check result structure and extract relevant information

def process_chembl_result(result):
    """Process ChEMBL search results"""
    if isinstance(result, dict):
        if "error" in result:
            # Handle error response
            return False, f"Error: {result['error']}"
        else:
            # Process successful result
            # Access molecular data, similarity scores, etc.
            return True, "Search completed successfully"
    else:
        # Handle non-dictionary results
        return False, "Unexpected result format"

# Process results
success1, message1 = process_chembl_result(result1)
success2, message2 = process_chembl_result(result2)
success3, message3 = process_chembl_result(result3)

# =============================================================================
# Method 9: Error Handling
# =============================================================================
# Description: Handle errors in chemistry tool execution
# Syntax: Check for errors and handle appropriately

def handle_chemistry_error(result, tool_name):
    """Handle errors from chemistry tools"""
    if isinstance(result, dict):
        if "error" in result:
            error_message = result["error"]
            # Handle specific error types
            if "not found" in error_message.lower():
                # Handle compound not found errors
                pass
            elif "invalid" in error_message.lower():
                # Handle invalid input errors
                pass
            else:
                # Handle other errors
                pass
            return False, error_message
        else:
            return True, "Success"
    return False, "Invalid result format"

# Handle errors for each result
success1, message1 = handle_chemistry_error(result1, "ChEMBL_search_similar_molecules")
success2, message2 = handle_chemistry_error(result2, "ChEMBL_search_similar_molecules")
success3, message3 = handle_chemistry_error(result3, "ChEMBL_search_similar_molecules")

# =============================================================================
# Method 10: Batch Processing
# =============================================================================
# Description: Process multiple chemistry queries in sequence
# Syntax: Loop through multiple tool calls

chemistry_queries = [
    {
        "name": "ChEMBL_search_similar_molecules",
        "arguments": {
            "query": "metformin",
            "similarity_threshold": 75,
            "max_results": 5
        }
    },
    {
        "name": "ChEMBL_search_similar_molecules",
        "arguments": {
            "query": "warfarin",
            "similarity_threshold": 80,
            "max_results": 3
        }
    }
]

batch_results = []
for query in chemistry_queries:
    try:
        result = tu.run(query)
        batch_results.append(result)
    except Exception as e:
        # Handle individual query failures
        batch_results.append({"error": str(e)})

# =============================================================================
# Summary of Chemistry Tools
# =============================================================================
# Available chemistry tools provide molecular similarity search capabilities:
# - ChEMBL_search_similar_molecules: Find molecules similar to a reference compound
# 
# Common parameters:
# - query: Compound name, SMILES, or other identifier
# - similarity_threshold: Minimum similarity score (0-100)
# - max_results: Maximum number of results to return
# 
# Query types supported:
# - Drug names (e.g., "aspirin", "Gadavist")
# - SMILES notation (e.g., "CC(=O)OC1=CC=CC=C1C(=O)O")
# - Trade names (e.g., "FENOFIBRATE")
# 
# Result processing:
# - Results typically contain molecular data and similarity scores
# - Check for "error" key in dictionary responses
# - Handle different result structures appropriately
# 
# Error handling:
# - Check for "error" key in dictionary responses
# - Handle compound not found errors
# - Validate input parameters before calling tools
# - Use appropriate similarity thresholds for desired results
# 
# Performance considerations:
# - Higher similarity thresholds return fewer, more similar results
# - Lower thresholds return more results but may be less relevant
# - Use max_results to limit response size
# - Consider batch processing for multiple queries
# 
# Use cases:
# - Drug discovery and development
# - Chemical similarity analysis
# - Lead compound identification
# - Structure-activity relationship studies