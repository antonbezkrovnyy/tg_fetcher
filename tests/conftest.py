"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path
import pytest

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test requiring external services"
    )
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


@pytest.fixture
def sample_fixture():
    """Example fixture for tests."""
    return {"status": "ok"}
