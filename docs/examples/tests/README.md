# Testing Infrastructure for Fetcher Service

This directory contains comprehensive tests for the Fetcher Service, following Test-Driven Development (TDD) principles.

## Test Structure

- `conftest.py` - Pytest fixtures and test configuration
- `test_fetcher_utils.py` - Tests for utility functions
- `test_fetcher.py` - Tests for main fetcher functionality
- `test_retry_mechanisms.py` - Tests for retry and error handling (to be implemented)
- `test_config.py` - Tests for configuration management (to be implemented)

## Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_fetcher_utils.py

# Run tests by marker
pytest -m unit
pytest -m integration
```

## Test Categories

- **unit**: Fast isolated tests of individual functions
- **integration**: Tests of component interactions
- **slow**: Tests that take more than a few seconds
- **telegram**: Tests involving Telegram API (mocked)

## Notes

Many tests are currently designed to fail until corresponding features are implemented. This follows TDD methodology where tests are written first to define expected behavior, then implementation follows to make tests pass.