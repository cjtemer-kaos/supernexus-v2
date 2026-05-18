#!/usr/bin/env python3
"""
PubChem Tools Example

Demonstrates various PubChem database tools available in ToolUniverse
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
# Test Data Setup
# =============================================================================
# Description: Define test compounds and parameters for PubChem queries
# Note: These are example compounds for testing various PubChem tools

# Valid compound identifiers
VALID_CID = 1983  # Example compound CID
VALID_NAME = "Aspirin"  # Compound name for name-based queries
VALID_SMILES = "C1=NC2=C(N1)C(=O)N=C(N2)N"  # SMILES notation for structure queries
VALID_SUBSTRUCTURE = "c1ccccc1"  # Benzene ring substructure for substructure search
VALID_THRESHOLD = 0.95  # Similarity threshold for similarity search
INVALID_CID = -1  # Intentionally invalid CID for error testing

# External reference types for cross-reference queries
VALID_XREF_TYPES = ["RegistryID", "RN"]

# =============================================================================
# Method 1: Compound Properties by CID
# =============================================================================
# Description: Retrieve molecular properties using compound ID
# Syntax: tu.run({"name": "PubChem_get_compound_properties_by_CID", "arguments": {"cid": 1983}})
result1 = tu.run({"name": "PubChem_get_compound_properties_by_CID", "arguments": {"cid": VALID_CID}})

# =============================================================================
# Method 2: Associated Patents
# =============================================================================
# Description: Get patents associated with a compound
# Syntax: tu.run({"name": "PubChem_get_associated_patents_by_CID", "arguments": {"cid": 1983}})
result2 = tu.run({"name": "PubChem_get_associated_patents_by_CID", "arguments": {"cid": VALID_CID}})

# =============================================================================
# Method 3: Webpage Title Extraction
# =============================================================================
# Description: Extract title from PubChem patent webpage
# Syntax: tu.run({"name": "get_webpage_title", "arguments": {"url": "https://pubchem.ncbi.nlm.nih.gov/patent/US6015577"}})
result3 = tu.run({
    "name": "get_webpage_title",
    "arguments": {"url": "https://pubchem.ncbi.nlm.nih.gov/patent/US6015577"}
})

# =============================================================================
# Method 4: CID Lookup by Name
# =============================================================================
# Description: Find compound ID using compound name
# Syntax: tu.run({"name": "PubChem_get_CID_by_compound_name", "arguments": {"name": "Aspirin"}})
result4 = tu.run({"name": "PubChem_get_CID_by_compound_name", "arguments": {"name": VALID_NAME}})

# =============================================================================
# Method 5: CID Lookup by SMILES
# =============================================================================
# Description: Find compound ID using SMILES notation
# Syntax: tu.run({"name": "PubChem_get_CID_by_SMILES", "arguments": {"smiles": "C1=NC2=C(N1)C(=O)N=C(N2)N"}})
result5 = tu.run({"name": "PubChem_get_CID_by_SMILES", "arguments": {"smiles": VALID_SMILES}})

# =============================================================================
# Method 6: Substructure Search
# =============================================================================
# Description: Search for compounds containing specific substructures
# Syntax: tu.run({"name": "PubChem_search_compounds_by_substructure", "arguments": {"smiles": "c1ccccc1"}})
result6 = tu.run({
    "name": "PubChem_search_compounds_by_substructure",
    "arguments": {"smiles": VALID_SUBSTRUCTURE}
})

# =============================================================================
# Method 7: Similarity Search
# =============================================================================
# Description: Find compounds similar to a reference structure
# Syntax: tu.run({"name": "PubChem_search_compounds_by_similarity", "arguments": {"smiles": "C1=NC2=C(N1)C(=O)N=C(N2)N", "threshold": 0.95}})
result7 = tu.run({
    "name": "PubChem_search_compounds_by_similarity",
    "arguments": {"smiles": VALID_SMILES, "threshold": VALID_THRESHOLD}
})

# =============================================================================
# Method 8: 2D Structure Image
# =============================================================================
# Description: Retrieve 2D molecular structure image
# Syntax: tu.run({"name": "PubChem_get_compound_2D_image_by_CID", "arguments": {"cid": 1983, "image_size": "150x150"}})
result8 = tu.run({
    "name": "PubChem_get_compound_2D_image_by_CID",
    "arguments": {"cid": VALID_CID, "image_size": "150x150"}
})

# =============================================================================
# Method 9: Compound Synonyms
# =============================================================================
# Description: Get alternative names and synonyms for a compound
# Syntax: tu.run({"name": "PubChem_get_compound_synonyms_by_CID", "arguments": {"cid": 1983}})
result9 = tu.run({"name": "PubChem_get_compound_synonyms_by_CID", "arguments": {"cid": VALID_CID}})

# =============================================================================
# Method 10: External References
# =============================================================================
# Description: Get cross-references to external databases
# Syntax: tu.run({"name": "PubChem_get_compound_xrefs_by_CID", "arguments": {"cid": 1983, "xref_types": ["RegistryID", "RN"]}})
result10 = tu.run({
    "name": "PubChem_get_compound_xrefs_by_CID",
    "arguments": {"cid": VALID_CID, "xref_types": VALID_XREF_TYPES}
})

# =============================================================================
# Method 11: Error Handling Example
# =============================================================================
# Description: Demonstrate error handling with invalid compound ID
# Syntax: tu.run({"name": "PubChem_get_compound_properties_by_CID", "arguments": {"cid": -1}})
result11 = tu.run({
    "name": "PubChem_get_compound_properties_by_CID",
    "arguments": {"cid": INVALID_CID}
})

# =============================================================================
# Result Processing Examples
# =============================================================================
# Description: Different ways to process and handle various result types

# Dictionary results (JSON data)
if isinstance(result1, dict):
    if "error" in result1:
        # Handle error response
        pass
    else:
        # Process successful dictionary result
        # Access specific properties: result1.get("property_name")
        pass

# List results (search results)
if isinstance(result6, list):
    # Process list of compounds
    # Access individual items: result6[0], result6[1], etc.
    pass

# String results (text data)
if isinstance(result9, str):
    # Process text data (CSV, TXT format)
    # Split by lines: result9.split("\n")
    pass

# Binary results (image data)
if isinstance(result8, (bytes, bytearray)):
    # Process binary image data
    # Check PNG header: result8.startswith(b"\x89PNG")
    # Save to file: with open("structure.png", "wb") as f: f.write(result8)
    pass

# =============================================================================
# Summary of PubChem Tools
# =============================================================================
# Available PubChem tools provide comprehensive chemical information:
# - Molecular properties and descriptors
# - Patent and literature associations
# - Structure-based searches (SMILES, substructure, similarity)
# - Name-based compound identification
# - 2D structure visualization
# - Synonym and nomenclature data
# - Cross-references to external databases
# 
# Common patterns:
# - Use CID for most compound-specific queries
# - Use SMILES for structure-based searches
# - Use compound names for text-based lookups
# - Check for "error" key in dictionary responses
# - Handle different result types (dict, list, str, bytes)
# 
# Error handling:
# - Invalid CIDs return error responses
# - Network timeouts may occur for large searches
# - Some tools may require specific parameter formats