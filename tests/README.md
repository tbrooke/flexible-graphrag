# Flexible-GraphRAG Tests

This directory contains comprehensive tests for the Flexible-GraphRAG system, with a focus on BM25 functionality and persistence.

## Test Structure

### Test Files

- `test_bm25_config.py` - Basic BM25 configuration tests
- `test_bm25_integration.py` - Comprehensive integration tests for BM25 functionality
- `conftest.py` - Pytest configuration and test setup
- `run_tests.py` - Test runner script for easy execution

### Test Categories

#### BM25 Tests (`@pytest.mark.bm25`)
- Configuration validation
- Factory method testing
- Integration with hybrid system
- Persistence functionality

#### Integration Tests (`@pytest.mark.integration`)
- End-to-end functionality testing
- System component interaction
- Database integration

#### Unit Tests (`@pytest.mark.unit`)
- Individual component testing
- Isolated functionality validation

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-mock

# Ensure flexible-graphrag is in your Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/flexible-graphrag"
```

### Running All Tests

```bash
# From project root
python -m pytest tests/ -v

# Or use the test runner
python tests/run_tests.py
```

### Running Specific Test Categories

```bash
# BM25 tests only
python tests/run_tests.py --bm25-only

# Integration tests only
python tests/run_tests.py --integration-only

# Using pytest directly
python -m pytest tests/ -m bm25 -v
python -m pytest tests/ -m integration -v
```

### Running Individual Test Files

```bash
# Run specific test file
python -m pytest tests/test_bm25_config.py -v

# Run specific test class
python -m pytest tests/test_bm25_integration.py::TestBM25Configuration -v

# Run specific test method
python -m pytest tests/test_bm25_integration.py::TestBM25Configuration::test_bm25_default_configuration -v
```

## Test Coverage

### BM25 Configuration Tests
- Default configuration validation
- Custom configuration options
- Enum type validation
- Persistence directory configuration

### BM25 Factory Tests
- Search store creation (returns None for BM25)
- BM25 retriever creation
- Configuration parameter handling
- Directory creation for persistence

### BM25 Integration Tests
- Hybrid system setup with BM25
- Retriever integration in hybrid system
- Configuration parameter passing
- Mock database interaction

### Persistence Tests
- Directory creation and validation
- Configuration parameter validation
- Temporary directory handling

### Search Type Tests
- Different search database type configurations
- BM25 vs external search engine handling
- Enum value validation

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Verbose output settings
- Marker definitions
- Warning suppression

### Conftest.py
- Path configuration for imports
- Automatic test marking
- Shared fixtures and utilities

## Adding New Tests

### Test File Naming
- Use `test_*.py` naming convention
- Include descriptive names indicating functionality

### Test Class Structure
```python
class TestFeatureName:
    """Test description"""
    
    def test_specific_functionality(self):
        """Test specific functionality description"""
        # Test implementation
        pass
```

### Test Markers
- `@pytest.mark.bm25` for BM25 related tests
- `@pytest.mark.integration` for integration tests
- `@pytest.mark.unit` for unit tests
- `@pytest.mark.slow` for slow running tests

### Mocking Guidelines
- Use `unittest.mock` for external dependencies
- Mock database connections and external services
- Use `pytest.fixture` for shared test data

## Continuous Integration

Tests are designed to run in CI/CD environments with:
- Isolated test execution
- Mock external dependencies
- Temporary file handling
- Clear pass/fail reporting

## Troubleshooting

### Import Errors
- Ensure `flexible-graphrag` is in Python path
- Check `conftest.py` path configuration
- Verify test file imports

### Database Connection Errors
- Tests use mocked database connections
- No actual database required for tests
- Check mock configuration in test files

### Permission Errors
- Tests create temporary directories
- Ensure write permissions in test directory
- Check temporary directory cleanup 