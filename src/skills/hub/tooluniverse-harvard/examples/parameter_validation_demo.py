#!/usr/bin/env python3
"""
Parameter Validation Demo

Demonstrates real parameter validation errors with actual tool schemas
"""

from tooluniverse import ToolUniverse
from tooluniverse.exceptions import ToolValidationError

# =============================================================================
# Method 1: Missing Required Parameter
# =============================================================================
# Description: Test validation when required parameters are missing
# Syntax: tu.tools.ToolName() - missing required parameter
tu = ToolUniverse()
tu.load_tools()

# Test missing required parameter
try:
    result1 = tu.tools.UniProt_get_entry_by_accession()
except Exception as e:
    # Handle missing required parameter error
    pass

# =============================================================================
# Method 2: Wrong Parameter Type
# =============================================================================
# Description: Test validation when parameter types are incorrect
# Syntax: tu.tools.ToolName(param="string") when param expects integer

# Wrong parameter type - string instead of integer
try:
    result2 = tu.tools.openalex_literature_search(
        search_keywords="AI", 
        max_results="ten"  # Should be integer
    )
except Exception as e:
    # Handle type validation error
    pass

# =============================================================================
# Method 3: Value Out of Range
# =============================================================================
# Description: Test validation when parameter values exceed allowed range
# Syntax: tu.tools.ToolName(param=value) when value exceeds maximum

# Value out of range - exceeds maximum allowed
try:
    result3 = tu.tools.openalex_literature_search(
        search_keywords="AI", 
        max_results=500  # Above maximum of 200
    )
except Exception as e:
    # Handle range validation error
    pass

# =============================================================================
# Method 4: Valid Parameters
# =============================================================================
# Description: Test with correct parameters that should work
# Syntax: tu.tools.ToolName(required_param=valid_value)

# Valid parameters - should work without errors
try:
    result4 = tu.tools.UniProt_get_entry_by_accession(accession="P05067")
    # Success: Got result of expected type
except Exception as e:
    # Handle unexpected error
    pass

# =============================================================================
# Method 5: Structured Error Handling
# =============================================================================
# Description: Handle validation errors with structured exception handling
# Syntax: try/except with ToolValidationError

try:
    result5 = tu.tools.UniProt_get_entry_by_accession(accession="")
except ToolValidationError as e:
    # Handle structured validation error
    # e.message contains error description
    # e.field contains the problematic field name
    # e.value contains the invalid value
    pass
except Exception as e:
    # Handle other types of errors
    pass

# =============================================================================
# Method 6: Custom Validation in Tools
# =============================================================================
# Description: Tools can perform additional validation beyond schema validation
# Syntax: Custom validation logic in tool.run() method

# Example of how tools might implement custom validation
def example_custom_validation():
    try:
        # This might trigger custom validation logic in the tool
        result6 = tu.tools.UniProt_get_entry_by_accession(accession="INVALID_FORMAT")
    except Exception as e:
        # Handle custom validation error
        pass

# =============================================================================
# Summary of Validation Types
# =============================================================================
# Parameter validation catches various error types:
# - Missing required parameters
# - Incorrect parameter types (string vs integer, etc.)
# - Values outside allowed ranges
# - Invalid parameter names
# - Malformed parameter values
# 
# Validation provides:
# - Clear error messages
# - Structured error information
# - Field-specific error details
# - Suggestion for corrections