#!/usr/bin/env python3
"""
Test suite for BaseTool capabilities refactoring.

This module tests the new capabilities added to BaseTool:
- validate_parameters()
- handle_error()
- get_cache_key()
- supports_streaming()
- supports_caching()
- get_tool_info()
"""

import pytest
import json
from unittest.mock import Mock, patch
from tooluniverse.base_tool import BaseTool
from tooluniverse.exceptions import (
    ToolError, ToolValidationError, ToolAuthError, ToolRateLimitError,
    ToolUnavailableError, ToolConfigError, ToolDependencyError, ToolServerError
)


class TestTool(BaseTool):
    """Test tool implementation for testing BaseTool capabilities."""
    
    def run(self, arguments=None):
        return "test_result"


@pytest.mark.unit
class TestBaseToolCapabilities:
    """Test suite for BaseTool new capabilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tool_config = {
            "name": "test_tool",
            "description": "A test tool",
            "parameter": {
                "type": "object",
                "properties": {
                    "required_param": {"type": "string"},
                    "optional_param": {"type": "integer"},
                    "boolean_param": {"type": "boolean"}
                },
                "required": ["required_param"]
            },
            "supports_streaming": True,
            "cacheable": False
        }
        self.tool = TestTool(self.tool_config)

    def test_validate_parameters_success(self):
        """Test successful parameter validation."""
        arguments = {
            "required_param": "test_value",
            "optional_param": 42,
            "boolean_param": True
        }
        
        result = self.tool.validate_parameters(arguments)
        assert result is None

    def test_validate_parameters_missing_required(self):
        """Test validation failure for missing required parameter."""
        arguments = {
            "optional_param": 42
        }
        
        result = self.tool.validate_parameters(arguments)
        assert isinstance(result, ToolValidationError)
        assert "required_param" in str(result)

    def test_validate_parameters_wrong_type(self):
        """Test validation failure for wrong parameter type."""
        arguments = {
            "required_param": "test_value",
            "optional_param": "not_an_integer"  # Should be integer
        }
        
        result = self.tool.validate_parameters(arguments)
        assert isinstance(result, ToolValidationError)
        assert "integer" in str(result)  # Check for type error message

    def test_validate_parameters_no_schema(self):
        """Test validation with no schema."""
        tool_config = {"name": "no_schema_tool"}
        tool = TestTool(tool_config)
        
        result = tool.validate_parameters({"any": "value"})
        assert result is None

    def test_handle_error_auth_error(self):
        """Test error classification for authentication errors."""
        auth_exceptions = [
            Exception("Authentication failed"),
            Exception("401 Unauthorized"),
            Exception("Invalid API key"),
            Exception("Token expired")
        ]
        
        for exc in auth_exceptions:
            result = self.tool.handle_error(exc)
            assert isinstance(result, ToolAuthError)
            assert "Authentication failed" in str(result)

    def test_handle_error_rate_limit(self):
        """Test error classification for rate limit errors."""
        rate_limit_exceptions = [
            Exception("Rate limit exceeded"),
            Exception("429 Too Many Requests"),
            Exception("Quota exceeded")
        ]
        
        for exc in rate_limit_exceptions:
            result = self.tool.handle_error(exc)
            assert isinstance(result, ToolRateLimitError)
            assert "Rate limit exceeded" in str(result)

    def test_handle_error_unavailable(self):
        """Test error classification for unavailable errors."""
        unavailable_exceptions = [
            Exception("Service unavailable"),
            Exception("Connection timeout"),
            Exception("404 Not Found"),
            Exception("Network error")
        ]
        
        for exc in unavailable_exceptions:
            result = self.tool.handle_error(exc)
            assert isinstance(result, ToolUnavailableError)
            assert "Tool unavailable" in str(result)

    def test_handle_error_validation(self):
        """Test error classification for validation errors."""
        validation_exceptions = [
            Exception("Invalid parameter"),
            Exception("Schema validation failed"),
            Exception("Parameter validation error")
        ]
        
        for exc in validation_exceptions:
            result = self.tool.handle_error(exc)
            assert isinstance(result, ToolValidationError)
            assert "Validation error" in str(result)

    def test_handle_error_config(self):
        """Test error classification for configuration errors."""
        config_exceptions = [
            Exception("Configuration error"),
            Exception("Setup failed"),
            Exception("Config setup error")
        ]
        
        for exc in config_exceptions:
            result = self.tool.handle_error(exc)
            assert isinstance(result, ToolConfigError)
            assert "Configuration error" in str(result)

    def test_handle_error_dependency(self):
        """Test error classification for dependency errors."""
        dependency_exceptions = [
            Exception("Import error"),
            Exception("Dependency missing"),
            Exception("Package error"),
            Exception("Module import failed")
        ]
        
        for exc in dependency_exceptions:
            result = self.tool.handle_error(exc)
            assert isinstance(result, ToolDependencyError)
            assert "Dependency error" in str(result)

    def test_handle_error_server(self):
        """Test error classification for server errors."""
        server_exceptions = [
            Exception("Internal server error"),
            Exception("Something went wrong"),
            Exception("Unknown error")
        ]
        
        for exc in server_exceptions:
            result = self.tool.handle_error(exc)
            assert isinstance(result, ToolServerError)
            assert "Unexpected error" in str(result)

    def test_get_cache_key(self):
        """Test cache key generation."""
        arguments = {"param1": "value1", "param2": 42}
        
        cache_key = self.tool.get_cache_key(arguments)
        assert isinstance(cache_key, str)
        assert len(cache_key) == 32  # MD5 hash length
        
        # Same arguments should produce same cache key
        cache_key2 = self.tool.get_cache_key(arguments)
        assert cache_key == cache_key2
        
        # Different arguments should produce different cache key
        different_args = {"param1": "different_value", "param2": 42}
        cache_key3 = self.tool.get_cache_key(different_args)
        assert cache_key != cache_key3

    def test_get_cache_key_deterministic(self):
        """Test that cache key generation is deterministic."""
        arguments = {"param1": "value1", "param2": 42}
        
        # Generate multiple times
        keys = [self.tool.get_cache_key(arguments) for _ in range(5)]
        
        # All should be the same
        assert all(key == keys[0] for key in keys)

    def test_supports_streaming(self):
        """Test streaming support detection."""
        assert self.tool.supports_streaming() is True
        
        # Test tool without streaming support
        no_streaming_config = {"name": "no_streaming_tool"}
        no_streaming_tool = TestTool(no_streaming_config)
        assert no_streaming_tool.supports_streaming() is False

    def test_supports_caching(self):
        """Test caching support detection."""
        assert self.tool.supports_caching() is False  # Set to False in config
        
        # Test tool with caching support
        caching_config = {"name": "caching_tool", "cacheable": True}
        caching_tool = TestTool(caching_config)
        assert caching_tool.supports_caching() is True

    def test_get_tool_info(self):
        """Test tool info retrieval."""
        info = self.tool.get_tool_info()
        
        assert info["name"] == "test_tool"
        assert info["description"] == "A test tool"
        assert info["supports_streaming"] is True
        assert info["supports_caching"] is False
        assert info["required_parameters"] == ["required_param"]
        assert info["tool_type"] == "TestTool"
        assert "parameter_schema" in info

    def test_get_required_parameters(self):
        """Test required parameters retrieval."""
        required_params = self.tool.get_required_parameters()
        assert required_params == ["required_param"]
        
        # Test tool with no required parameters
        no_required_config = {
            "name": "no_required_tool",
            "parameter": {
                "type": "object",
                "properties": {
                    "optional_param": {"type": "string"}
                }
            }
        }
        no_required_tool = TestTool(no_required_config)
        assert no_required_tool.get_required_parameters() == []


class TestCustomToolValidation:
    """Test custom tool with overridden validation."""

    class CustomValidationTool(BaseTool):
        """Tool with custom validation logic."""
        
        def validate_parameters(self, arguments):
            """Custom validation that requires 'custom_field'."""
            if "custom_field" not in arguments:
                return ToolValidationError(
                    "Custom field is required",
                    details={"custom_rule": "custom_field_must_be_present"}
                )
            return None
        
        def run(self, arguments=None):
            return "custom_result"

    def test_custom_validation(self):
        """Test custom validation logic."""
        tool_config = {"name": "custom_tool"}
        tool = self.CustomValidationTool(tool_config)
        
        # Should fail without custom_field
        result = tool.validate_parameters({"other_field": "value"})
        assert isinstance(result, ToolValidationError)
        assert "Custom field is required" in str(result)
        assert result.details["custom_rule"] == "custom_field_must_be_present"
        
        # Should pass with custom_field
        result = tool.validate_parameters({"custom_field": "value"})
        assert result is None


class TestBackwardCompatibility:
    """Test backward compatibility with old exception classes."""

    def test_old_exception_removed(self):
        """Test that old exception classes are no longer available."""
        # These should no longer be available
        with pytest.raises(ImportError):
            from tooluniverse.base_tool import ToolExecutionError
        with pytest.raises(ImportError):
            from tooluniverse.base_tool import ValidationError
        with pytest.raises(ImportError):
            from tooluniverse.base_tool import AuthenticationError
        with pytest.raises(ImportError):
            from tooluniverse.base_tool import RateLimitError

    def test_new_exception_classes_work(self):
        """Test that new exception classes work without warnings."""
        # These should work without warnings
        ToolError("test message")
        ToolValidationError("test message")
        ToolAuthError("test message")
        ToolRateLimitError("test message")
        ToolUnavailableError("test message")
        ToolConfigError("test message")
        ToolDependencyError("test message")
        ToolServerError("test message")


if __name__ == "__main__":
    pytest.main([__file__])
