# ToolUniverse Test Suite

## Test Organization

- `unit/` - Fast, isolated unit tests (no network, no external dependencies)
- `integration/` - Integration tests (may use network or real tools)
- `tools/` - Tool-specific tests (test individual tool implementations)
- `api/` - API validation and external service tests
- `helpers/` - Test utilities and fixtures

## Running Tests

### Quick Tests (default)
```bash
pytest  # Runs unit tests only
```

### By Category
```bash
pytest tests/unit           # Unit tests only
pytest tests/integration    # Integration tests
pytest -m unit             # All unit tests
pytest -m integration      # All integration tests
```

### Slow Tests
```bash
pytest -m slow             # Run slow tests
pytest -m "not slow"       # Skip slow tests (default)
```

### With Coverage
```bash
pytest --cov=tooluniverse --cov-report=html
```

## Test Standards

1. **Markers**: All tests must have appropriate markers
2. **Naming**: Use descriptive names (`test_<what>_<expected_behavior>`)
3. **Isolation**: Unit tests must not depend on network or external services
4. **Speed**: Unit tests should complete in <1s each
5. **Documentation**: Each test should have a docstring explaining what it tests

## Writing New Tests

### Unit Test Template
```python
import pytest
from tooluniverse import ToolUniverse

@pytest.mark.unit
def test_feature_behavior():
    """Test that feature behaves correctly when condition."""
    # Arrange
    tu = ToolUniverse()
    
    # Act
    result = tu.some_method()
    
    # Assert
    assert result == expected
```

### Integration Test Template
```python
import pytest

@pytest.mark.integration
def test_tool_integration():
    """Test that tool integrates correctly with real service."""
    # May make real API calls
    pass
```

## Test Categories Explained

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 1s each)
- **Dependencies**: No network, no external services
- **Examples**: 
  - Parameter validation
  - Error handling
  - BaseTool capabilities
  - Backward compatibility

### Integration Tests (`tests/integration/`)
- **Purpose**: Test how components work together
- **Speed**: Medium (1-10s each)
- **Dependencies**: May use network or real tools
- **Examples**:
  - Coding API integration
  - Typed functions
  - Streaming support
  - Compose tool functionality

### Tool Tests (`tests/tools/`)
- **Purpose**: Test individual tool implementations
- **Speed**: Variable (depends on tool)
- **Dependencies**: May require API keys or external services
- **Examples**:
  - Literature search tools
  - Clinical guideline tools
  - Paper search tools
  - Cellosaurus tool

### API Tests (`tests/api/`)
- **Purpose**: Test API validation and external service integration
- **Speed**: Slow (> 10s each)
- **Dependencies**: Require API keys
- **Examples**:
  - API key validation
  - Azure OpenAI models
  - Agentic streaming integration

## Test Markers

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Network or external-resource tests
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.require_api_keys` - Tests requiring API keys
- `@pytest.mark.legacy` - Legacy tests kept for reference
- `@pytest.mark.asyncio` - Tests that use pytest-asyncio

## Common Commands

```bash
# Run all fast tests (default)
pytest

# Run only unit tests
pytest tests/unit

# Run integration tests
pytest tests/integration

# Run with specific markers
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run with coverage
pytest --cov=tooluniverse --cov-report=html

# Run specific test file
pytest tests/unit/test_parameter_validation.py

# Run specific test function
pytest tests/unit/test_parameter_validation.py::TestParameterValidation::test_valid_parameters

# Verbose output
pytest -v

# Stop on first failure
pytest --maxfail=1
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure `src/` is in Python path
2. **Missing API Keys**: Use `@pytest.mark.skipif` for optional tests
3. **Network Timeouts**: Use `@pytest.mark.slow` for network tests
4. **Test Dependencies**: Install required packages in test environment

### Debug Mode
```bash
# Run with debug output
pytest -s -v

# Run single test with debug
pytest -s -v tests/unit/test_parameter_validation.py::TestParameterValidation::test_valid_parameters
```

## Contributing Tests

When adding new tests:

1. **Choose the right category**: Unit, integration, tools, or API
2. **Add appropriate markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
3. **Write clear docstrings**: Explain what each test does
4. **Follow naming conventions**: `test_<what>_<expected_behavior>`
5. **Keep tests isolated**: Each test should be independent
6. **Use fixtures**: For common setup/teardown
7. **Mock external dependencies**: In unit tests
8. **Test edge cases**: Invalid inputs, error conditions
9. **Keep tests fast**: Unit tests < 1s, integration tests < 10s
10. **Document requirements**: API keys, network access, etc.