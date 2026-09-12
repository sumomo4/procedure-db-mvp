"""Shared pytest fixtures for the standard API tests."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.core.auth import AuthUserData
from app.core.security import get_current_user
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
    application.dependency_overrides[get_current_user] = lambda: AuthUserData(
        user_id=1,
        username="pytest-admin",
        display_name="pytest authenticated user",
        role="admin",
    )

    with TestClient(application) as test_client:
        yield test_client

    application.dependency_overrides.clear()
