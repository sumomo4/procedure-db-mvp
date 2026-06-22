"""Tests for browser access settings."""

from fastapi import status
from fastapi.testclient import TestClient


def test_cors_preflight_allows_frontend_origin(client: TestClient) -> None:
    """Frontend origins should be allowed to call the API in local development."""

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
