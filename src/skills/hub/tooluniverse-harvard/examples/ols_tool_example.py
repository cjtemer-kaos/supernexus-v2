#!/usr/bin/env python3
"""
Example usage of OLSTool for EMBL-EBI Ontology Lookup Service (OLS).

This example demonstrates all major operations of the OLSTool:
- Searching for terms
- Getting ontology information
- Searching ontologies
- Getting term details
- Retrieving term hierarchies
- Finding similar terms
"""

from tooluniverse import ToolUniverse


def example_search_terms():
    """Example: Search for terms in OLS."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Search for Terms")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Search for disease-related terms
    result = tu.run(
        {
            "name": "ols_search_terms",
            "arguments": {
                "operation": "search_terms",
                "query": "diabetes",
                "rows": 5,
            },
        }
    )

    print(f"\nSearch Query: diabetes")
    print(f"Total Results: {result.get('total_items', 0)}")
    if "terms" in result:
        print(f"Showing: {result['showing']} results")
        for i, term in enumerate(result["terms"][:3], 1):
            print(f"\n  {i}. {term.get('label', 'N/A')}")
            print(f"     IRI: {term.get('iri', 'N/A')}")
            print(f"     Ontology: {term.get('ontology_name', 'N/A')}")


def example_search_ontologies():
    """Example: Search for ontologies."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Search for Ontologies")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Search all available ontologies
    result = tu.run(
        {
            "name": "ols_search_ontologies",
            "arguments": {
                "operation": "search_ontologies",
                "size": 10,
            },
        }
    )

    print(f"\nAvailable Ontologies (first 10):")
    if "results" in result:
        for i, ontology in enumerate(result["results"][:5], 1):
            print(f"\n  {i}. {ontology.get('title', 'N/A')}")
            print(f"     ID: {ontology.get('id', 'N/A')}")
            if ontology.get("description"):
                desc = ontology["description"][:100] + "..."
                print(f"     Description: {desc}")


def example_get_ontology_info():
    """Example: Get detailed information about an ontology."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Get Ontology Information")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Get info about the EFO (Experimental Factor Ontology)
    result = tu.run(
        {
            "name": "ols_get_ontology_info",
            "arguments": {
                "operation": "get_ontology_info",
                "ontology_id": "efo",
            },
        }
    )

    print(f"\nOntology Information:")
    print(f"  ID: {result.get('id', 'N/A')}")
    print(f"  Title: {result.get('title', 'N/A')}")
    print(f"  Version: {result.get('version', 'N/A')}")
    if result.get("description"):
        print(f"  Description: {result.get('description')[:150]}...")
    if result.get("numberOfClasses"):
        print(f"  Number of Classes: {result.get('numberOfClasses')}")


def example_get_term_info():
    """Example: Get detailed information about a term."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Get Term Information")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Get information about a specific term
    result = tu.run(
        {
            "name": "ols_get_term_info",
            "arguments": {
                "operation": "get_term_info",
                "id": "EFO:0000408",
            },
        }
    )

    if "error" not in result:
        print(f"\nTerm Information:")
        print(f"  Label: {result.get('label', 'N/A')}")
        print(f"  IRI: {result.get('iri', 'N/A')}")
        print(f"  Short Form: {result.get('short_form', 'N/A')}")
        if result.get("description"):
            print(f"  Description: {result.get('description')}")
        if result.get("synonyms"):
            print(f"  Synonyms: {', '.join(result.get('synonyms', []))}")
    else:
        print(f"\nNote: {result.get('error')}")


def example_exact_search():
    """Example: Search for exact term matches."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Exact Term Search")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Perform exact match search
    result = tu.run(
        {
            "name": "ols_search_terms",
            "arguments": {
                "operation": "search_terms",
                "query": "cancer",
                "ontology": "efo",
                "exact_match": True,
                "rows": 5,
            },
        }
    )

    print(f"\nExact Search Results for 'cancer' in EFO:")
    print(f"  Total Results: {result.get('total_items', 0)}")
    if "terms" in result:
        print(f"  Showing: {result['showing']} results")
        for term in result["terms"]:
            print(f"\n  - {term.get('label', 'N/A')}")
            print(f"    OBO ID: {term.get('obo_id', 'N/A')}")


def example_search_with_filters():
    """Example: Search with various filters."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Advanced Search with Filters")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Search with multiple filters
    result = tu.run(
        {
            "name": "ols_search_terms",
            "arguments": {
                "operation": "search_terms",
                "query": "protein",
                "rows": 10,
                "include_obsolete": False,
            },
        }
    )

    print(f"\nFiltered Search Results for 'protein':")
    print(f"  Total Results: {result.get('total_items', 0)}")
    print(f"  Filters Applied:")
    if "filters" in result:
        filters = result["filters"]
        print(f"    - Ontology: {filters.get('ontology', 'All')}")
        print(f"    - Exact Match: {filters.get('exact_match', False)}")
        print(f"    - Include Obsolete: {filters.get('include_obsolete', False)}")


def example_term_hierarchy():
    """Example: Explore term hierarchies (if IRIs available)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Term Hierarchy (Children/Ancestors)")
    print("=" * 70)

    print("\nNote: This example demonstrates the API structure.")
    print("To use get_term_children or get_term_ancestors, you need a valid term IRI.")
    print("\nExample IRI structure:")
    print("  - http://purl.obolibrary.org/obo/GO_0008150")
    print("  - http://www.ebi.ac.uk/efo/EFO_0000408")
    print("\nYou can obtain IRIs from search results and use them as follows:\n")

    print("  result = tu.run({")
    print('      "name": "ols_get_term_children",')
    print("      \"arguments\": {")
    print('          "operation": "get_term_children",')
    print(
        '          "term_iri": "http://www.ebi.ac.uk/efo/EFO_0000408",'
    )
    print('          "ontology": "efo",')
    print('          "size": 20')
    print("      }")
    print("  })")


def example_error_handling():
    """Example: Error handling."""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Error Handling")
    print("=" * 70)

    tu = ToolUniverse()
    tu.load_tools()

    # Try with invalid parameters
    print("\n1. Missing required parameter:")
    result = tu.run(
        {
            "name": "ols_search_terms",
            "arguments": {"operation": "search_terms"},
        }
    )
    if "error" in result:
        print(f"   ✓ Error caught: {result['error']}")

    print("\n2. Invalid operation:")
    result = tu.run(
        {
            "name": "ols_search_terms",
            "arguments": {
                "operation": "invalid_operation",
                "query": "test",
            },
        }
    )
    if "error" in result:
        print(f"   ✓ Error caught: {result['error'][:80]}...")

    print("\n3. Invalid ontology ID:")
    result = tu.run(
        {
            "name": "ols_get_ontology_info",
            "arguments": {
                "operation": "get_ontology_info",
                "ontology_id": "invalid_id_12345",
            },
        }
    )
    if "error" in result:
        print(f"   ✓ Error caught: {result['error'][:80]}...")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("OLSTool - EMBL-EBI Ontology Lookup Service Examples")
    print("=" * 70)
    print("\nThis script demonstrates the capabilities of OLSTool")
    print("for accessing the EMBL-EBI Ontology Lookup Service (OLS) API.\n")

    try:
        # Run examples
        example_search_terms()
        example_search_ontologies()
        example_get_ontology_info()
        example_get_term_info()
        example_exact_search()
        example_search_with_filters()
        example_term_hierarchy()
        example_error_handling()

        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
