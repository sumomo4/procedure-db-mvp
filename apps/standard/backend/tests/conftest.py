"""Shared pytest fixtures for the standard API tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app
from app.routers.health import get_app_settings


@pytest.fixture
def test_settings() -> AppSettings:
    """Create deterministic settings for API tests.

    Returns:
        Application settings for tests.
    """

    return AppSettings(
        app_env="test",
        service_name="standard-api-test",
        db_host="test-db",
        db_port=15432,
        db_name="mvp_standard_test",
        db_user="test_user",
        db_password="test_password",
    )


@pytest.fixture
def client(test_settings: AppSettings) -> Generator[TestClient]:
    """Create a FastAPI test client with settings overridden.

    Args:
        test_settings: Deterministic settings for tests.

    Yields:
        FastAPI test client.
    """

    application = create_app()
    application.dependency_overrides[get_app_settings] = lambda: test_settings

    with TestClient(application) as test_client:
        yield test_client

    application.dependency_overrides.clear()
