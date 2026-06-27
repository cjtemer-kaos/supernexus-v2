#!/usr/bin/env python3
"""
Tool Validation Example

This example shows how validation works with existing tools.
"""

from tooluniverse.tools import ArXiv_search_papers


def demo():
    """Show how validation works with existing tools"""
    
    # Test 1: Valid input - this will work fine
    result = ArXiv_search_papers(query="machine learning", limit=3)
    print("✓ Valid input:")
    print(result)
    print()
    
    # Test 2: Wrong parameter type - limit should be int, not string
    result = ArXiv_search_papers(query="AI", limit="three")  # Wrong type
    print("✗ Wrong type (string):")
    print(result)
    print()
    
    # Test 3: Missing required parameter - query is required
    try:
        result = ArXiv_search_papers()  # Missing query
        print("✗ Missing required parameter:")
        print(result)
    except TypeError as e:
        print("✗ Missing required parameter:")
        print(f"Python error: {e}")
    print()
    
    # Test 4: Invalid parameter name
    try:
        result = ArXiv_search_papers(query="AI", invalid_param="test")
        print("✗ Invalid parameter name:")
        print(result)
    except TypeError as e:
        print("✗ Invalid parameter name:")
        print(f"Python error: {e}")
    print()
    
    # Test 5: Validation disabled - errors won't be caught
    try:
        result = ArXiv_search_papers(query="AI", limit="three", validate=False)
        print("✓ Validation disabled:")
        print(result)
    except TypeError as e:
        print("✓ Validation disabled:")
        print(f"Python error: {e}")


if __name__ == "__main__":
    demo()