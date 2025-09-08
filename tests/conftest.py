"""
Pytest configuration and fixtures for the Legal Case File Manager tests.
"""

import pytest
from app import create_app
from app.config.settings import TestingConfig


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app(TestingConfig)
    app.config.update({
        "TESTING": True,
    })
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()
