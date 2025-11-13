"""Pytest configuration for integration tests."""

import pytest


def pytest_configure(config):
    """Configure pytest for integration tests."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring external services",
    )


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Provide path to docker-compose file for integration tests."""
    return str(pytestconfig.rootdir / "docker-compose.yml")
