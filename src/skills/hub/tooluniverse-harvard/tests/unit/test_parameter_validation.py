#!/usr/bin/env python3
"""
Test parameter validation functionality

Verify that validate_parameters correctly detects various types of validation errors
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import Mock
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tooluniverse.base_tool import BaseTool
from tooluniverse.exceptions import ToolValidationError


@pytest.mark.unit
class TestParameterValidation(unittest.TestCase):
    """Test parameter validation with various error scenarios"""
    
    def setUp(self):
        """Set up test tool with comprehensive parameter schema"""
        self.tool_config = {
            "name": "test_tool",
            "type": "TestTool",
            "description": "Test tool for validation",
            "parameter": {
                "type": "object",
                "properties": {
                    "required_string": {
                        "type": "string",
                        "description": "Required string parameter"
                    },
                    "optional_integer": {
                        "type": "integer",
                        "description": "Optional integer parameter",
                        "minimum": 1,
                        "maximum": 100
                    },
                    "optional_boolean": {
                        "type": "boolean",
                        "description": "Optional boolean parameter"
                    },
                    "enum_value": {
                        "type": "string",
                        "enum": ["option1", "option2", "option3"],
                        "description": "Enum parameter"
                    },
                    "date_string": {
                        "type": "string",
                        "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
                        "description": "Date string in YYYY-MM-DD format"
                    },
                    "nested_object": {
                        "type": "object",
                        "properties": {
                            "nested_string": {"type": "string"},
                            "nested_number": {"type": "number"}
                        },
                        "required": ["nested_string"]
                    },
                    "string_array": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 5
                    }
                },
                "required": ["required_string"]
            }
        }
        
        self.tool = BaseTool(self.tool_config)
    
    def test_valid_parameters(self):
        """Test that valid parameters pass validation"""
        valid_args = {
            "required_string": "test_value",
            "optional_integer": 50,
            "optional_boolean": True,
            "enum_value": "option1",
            "date_string": "2023-12-25",
            "nested_object": {
                "nested_string": "nested_value",
                "nested_number": 42.5
            },
            "string_array": ["item1", "item2", "item3"]
        }
        
        result = self.tool.validate_parameters(valid_args)
        self.assertIsNone(result, "Valid parameters should not return validation error")
    
    def test_missing_required_parameter(self):
        """Test detection of missing required parameters"""
        invalid_args = {
            "optional_integer": 50
            # Missing required_string
        }
        
        result = self.tool.validate_parameters(invalid_args)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("required_string", str(result))
        self.assertIn("required", str(result).lower())
    
    def test_wrong_parameter_type(self):
        """Test detection of wrong parameter types"""
        invalid_args = {
            "required_string": "test_value",
            "optional_integer": "not_a_number"  # Should be integer
        }
        
        result = self.tool.validate_parameters(invalid_args)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("not of type 'integer'", str(result))
    
    def test_integer_range_violation(self):
        """Test detection of integer range violations"""
        # Test minimum violation
        invalid_args_min = {
            "required_string": "test_value",
            "optional_integer": 0  # Below minimum of 1
        }
        
        result = self.tool.validate_parameters(invalid_args_min)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("minimum", str(result))
        
        # Test maximum violation
        invalid_args_max = {
            "required_string": "test_value",
            "optional_integer": 150  # Above maximum of 100
        }
        
        result = self.tool.validate_parameters(invalid_args_max)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("maximum", str(result))
    
    def test_enum_violation(self):
        """Test detection of enum value violations"""
        invalid_args = {
            "required_string": "test_value",
            "enum_value": "invalid_option"  # Not in enum
        }
        
        result = self.tool.validate_parameters(invalid_args)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("not one of", str(result))
        self.assertIn("option1", str(result))
    
    def test_pattern_violation(self):
        """Test detection of string pattern violations"""
        invalid_args = {
            "required_string": "test_value",
            "date_string": "25/12/2023"  # Wrong format, should be YYYY-MM-DD
        }
        
        result = self.tool.validate_parameters(invalid_args)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("does not match", str(result))
    
    def test_nested_object_violation(self):
        """Test detection of nested object structure violations"""
        # Test wrong type for nested object
        invalid_args_type = {
            "required_string": "test_value",
            "nested_object": "not_an_object"
        }
        
        result = self.tool.validate_parameters(invalid_args_type)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("not of type 'object'", str(result))
        
        # Test missing required field in nested object
        invalid_args_missing = {
            "required_string": "test_value",
            "nested_object": {
                "nested_number": 42.5
                # Missing required nested_string
            }
        }
        
        result = self.tool.validate_parameters(invalid_args_missing)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("nested_string", str(result))
        self.assertIn("required", str(result).lower())
    
    def test_array_violations(self):
        """Test detection of array-related violations"""
        # Test wrong type for array
        invalid_args_type = {
            "required_string": "test_value",
            "string_array": "not_an_array"
        }
        
        result = self.tool.validate_parameters(invalid_args_type)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("not of type 'array'", str(result))
        
        # Test array length violations
        invalid_args_length = {
            "required_string": "test_value",
            "string_array": []  # Below minItems of 1
        }
        
        result = self.tool.validate_parameters(invalid_args_length)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("non-empty", str(result))  # jsonschema reports "should be non-empty" for minItems
        
        # Test too many items
        invalid_args_too_many = {
            "required_string": "test_value",
            "string_array": ["item1", "item2", "item3", "item4", "item5", "item6"]  # Above maxItems of 5
        }
        
        result = self.tool.validate_parameters(invalid_args_too_many)
        self.assertIsInstance(result, ToolValidationError)
        self.assertIn("too long", str(result))  # jsonschema reports "is too long" for maxItems
    
    def test_multiple_errors(self):
        """Test that validation stops at first error (jsonschema behavior)"""
        invalid_args = {
            # Missing required parameter
            # Wrong type for integer
            "optional_integer": "not_a_number",
            "enum_value": "invalid_option"
        }
        
        result = self.tool.validate_parameters(invalid_args)
        self.assertIsInstance(result, ToolValidationError)
        # Should report the first error (missing required parameter)
        self.assertIn("required_string", str(result))
    
    def test_no_schema_validation(self):
        """Test that tools without parameter schema skip validation"""
        tool_config_no_schema = {
            "name": "no_schema_tool",
            "type": "NoSchemaTool",
            "description": "Tool without parameter schema"
            # No parameter field
        }
        
        tool_no_schema = BaseTool(tool_config_no_schema)
        result = tool_no_schema.validate_parameters({"any": "value"})
        self.assertIsNone(result, "Tools without schema should skip validation")
    
    def test_error_details_structure(self):
        """Test that validation error includes proper details structure"""
        invalid_args = {
            "required_string": "test_value",
            "optional_integer": "not_a_number"
        }
        
        result = self.tool.validate_parameters(invalid_args)
        self.assertIsInstance(result, ToolValidationError)
        
        # Check error details structure
        self.assertIn("validation_error", result.details)
        self.assertIn("path", result.details)
        self.assertIn("schema", result.details)
        
        # Check that path points to the problematic field
        self.assertIn("optional_integer", str(result.details["path"]))


if __name__ == "__main__":
    unittest.main()
