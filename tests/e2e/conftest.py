"""Pytest configuration for E2E tests."""

import pytest


def pytest_configure(config):
    """Configure pytest for E2E tests."""
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
