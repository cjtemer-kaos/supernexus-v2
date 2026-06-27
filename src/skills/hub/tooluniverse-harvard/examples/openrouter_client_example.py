"""
Tests for OpenRouter client integration.

These tests verify that the OpenRouter client is properly integrated
with the ToolUniverse system.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from tooluniverse.llm_clients import OpenRouterClient
from tooluniverse.agentic_tool import AgenticTool


class TestOpenRouterClient:
    """Test suite for OpenRouterClient."""

    def test_client_initialization_without_api_key(self):
        """Test that client raises error when API key is not set."""
        # Remove API key if present
        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        
        try:
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY not set"):
                logger = Mock()
                OpenRouterClient("openai/gpt-4o", logger)
        finally:
            # Restore old key if it existed
            if old_key:
                os.environ["OPENROUTER_API_KEY"] = old_key

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    @patch("tooluniverse.llm_clients.OpenRouterClient._OpenAI")
    def test_client_initialization_with_api_key(self, mock_openai_class):
        """Test that client initializes correctly with API key."""
        logger = Mock()
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        client = OpenRouterClient("openai/gpt-4o", logger)
        
        assert client.model_name == "openai/gpt-4o"
        assert client.logger == logger
        mock_openai_class.assert_called_once()
        
        # Verify base_url and api_key
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"
        assert call_kwargs["api_key"] == "test_key"

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test_key",
            "OPENROUTER_SITE_URL": "https://example.com",
            "OPENROUTER_SITE_NAME": "Test App"
        }
    )
    @patch("tooluniverse.llm_clients.OpenRouterClient._OpenAI")
    def test_client_with_optional_headers(self, mock_openai_class):
        """Test that optional headers are set correctly."""
        logger = Mock()
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        client = OpenRouterClient("openai/gpt-4o", logger)
        
        call_kwargs = mock_openai_class.call_args[1]
        assert "default_headers" in call_kwargs
        headers = call_kwargs["default_headers"]
        assert headers["HTTP-Referer"] == "https://example.com"
        assert headers["X-Title"] == "Test App"

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    @patch("tooluniverse.llm_clients.OpenRouterClient._OpenAI")
    def test_resolve_default_max_tokens(self, mock_openai_class):
        """Test max tokens resolution for known models."""
        logger = Mock()
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        client = OpenRouterClient("openai/gpt-4o", logger)
        
        # Test known model
        max_tokens = client._resolve_default_max_tokens("openai/gpt-4o")
        assert max_tokens == 64000
        
        # Test another known model
        max_tokens = client._resolve_default_max_tokens("anthropic/claude-3.5-sonnet")
        assert max_tokens == 8192
        
        # Test unknown model
        max_tokens = client._resolve_default_max_tokens("unknown/model")
        assert max_tokens is None

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    @patch("tooluniverse.llm_clients.OpenRouterClient._OpenAI")
    def test_infer_basic(self, mock_openai_class):
        """Test basic inference functionality."""
        logger = Mock()
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        # Mock the completion response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_client.chat.completions.create.return_value = mock_response
        
        client = OpenRouterClient("openai/gpt-4o", logger)
        
        messages = [{"role": "user", "content": "Test prompt"}]
        result = client.infer(
            messages=messages,
            temperature=0.7,
            max_tokens=100,
            return_json=False
        )
        
        assert result == "Test response"
        mock_client.chat.completions.create.assert_called_once()
        
        # Verify call arguments
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "openai/gpt-4o"
        assert call_kwargs["messages"] == messages
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 100


class TestAgenticToolWithOpenRouter:
    """Test AgenticTool integration with OpenRouter."""

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    @patch("tooluniverse.agentic_tool.OpenRouterClient")
    def test_agentic_tool_with_openrouter(self, mock_client_class):
        """Test that AgenticTool can use OpenRouter."""
        # Mock the client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.test_api = Mock()
        mock_client.infer = Mock(return_value="Test result")
        
        # Create tool config
        tool_config = {
            "name": "Test_Tool",
            "prompt": "Test prompt: {input}",
            "input_arguments": ["input"],
            "parameter": {
                "type": "object",
                "properties": {
                    "input": {"type": "string", "required": True}
                },
                "required": ["input"]
            },
            "configs": {
                "api_type": "OPENROUTER",
                "model_id": "openai/gpt-4o",
                "temperature": 0.5,
                "validate_api_key": True,
                "return_metadata": False
            }
        }
        
        # Create tool
        tool = AgenticTool(tool_config)
        
        # Verify initialization
        assert tool._is_available
        assert tool._current_api_type == "OPENROUTER"
        assert tool._current_model_id == "openai/gpt-4o"
        mock_client.test_api.assert_called_once()
        
        # Test execution
        result = tool.run({"input": "test data"})
        assert result == "Test result"
        mock_client.infer.assert_called_once()

    def test_openrouter_in_supported_types(self):
        """Test that OPENROUTER is in supported API types."""
        tool_config = {
            "name": "Test_Tool",
            "prompt": "Test: {x}",
            "input_arguments": ["x"],
            "parameter": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"]
            },
            "configs": {
                "api_type": "OPENROUTER",
                "model_id": "openai/gpt-4o",
                "validate_api_key": False
            }
        }
        
        # This should not raise an error
        try:
            tool = AgenticTool(tool_config)
            # Validation should pass
            validation = tool.validate_configuration()
            assert validation["valid"]
        except ValueError as e:
            if "Unsupported API type" in str(e):
                pytest.fail("OPENROUTER should be a supported API type")


class TestOpenRouterModels:
    """Test model configuration and limits."""

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test_key"})
    @patch("tooluniverse.llm_clients.OpenRouterClient._OpenAI")
    def test_model_limits_configuration(self, mock_openai_class):
        """Test that model limits are correctly configured."""
        logger = Mock()
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        client = OpenRouterClient("openai/gpt-4o", logger)
        
        # Check some key models
        expected_models = {
            "openai/gpt-4o": {"max_output": 64000, "context_window": 1_048_576},
            "anthropic/claude-3.7-sonnet": {"max_output": 8192, "context_window": 200_000},
            "google/gemini-2.0-flash-exp": {"max_output": 8192, "context_window": 1_048_576},
            "qwen/qwq-32b-preview": {"max_output": 8192, "context_window": 32_768},
        }
        
        for model_id, expected_limits in expected_models.items():
            assert model_id in client.DEFAULT_MODEL_LIMITS
            assert client.DEFAULT_MODEL_LIMITS[model_id] == expected_limits

    @patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test_key",
            "OPENROUTER_MAX_TOKENS_BY_MODEL": '{"openai/gpt-4o": 32000}'
        }
    )
    @patch("tooluniverse.llm_clients.OpenRouterClient._OpenAI")
    def test_env_override_max_tokens(self, mock_openai_class):
        """Test that environment variables can override max tokens."""
        logger = Mock()
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        client = OpenRouterClient("openai/gpt-4o", logger)
        
        # Should return the overridden value
        max_tokens = client._resolve_default_max_tokens("openai/gpt-4o")
        assert max_tokens == 32000


class TestOpenRouterFallback:
    """Test fallback configuration with OpenRouter."""

    def test_openrouter_in_default_fallback_chain(self):
        """Test that OpenRouter is in the default fallback chain."""
        from tooluniverse.agentic_tool import DEFAULT_FALLBACK_CHAIN
        
        # Check that OPENROUTER is in the default chain
        openrouter_configs = [
            config for config in DEFAULT_FALLBACK_CHAIN
            if config["api_type"] == "OPENROUTER"
        ]
        
        assert len(openrouter_configs) > 0, "OPENROUTER should be in default fallback chain"
        
        # Verify it has a model_id
        for config in openrouter_configs:
            assert "model_id" in config
            assert config["model_id"].startswith("openai/") or \
                   config["model_id"].startswith("anthropic/") or \
                   config["model_id"].startswith("google/") or \
                   config["model_id"].startswith("qwen/")

    def test_openrouter_in_api_key_env_vars(self):
        """Test that OPENROUTER is in API key environment variables mapping."""
        from tooluniverse.agentic_tool import API_KEY_ENV_VARS
        
        assert "OPENROUTER" in API_KEY_ENV_VARS
        assert "OPENROUTER_API_KEY" in API_KEY_ENV_VARS["OPENROUTER"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


