"""Pytest configuration for unit tests."""

import pytest


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment between tests."""
    yield
    # Cleanup if needed
