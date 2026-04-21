"""Tests for Sprint 2 router foundations."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("path", "resource", "message"),
    [
        ("/api/v1/modules/foundation", "modules", "Module router foundation is available."),
        (
            "/api/v1/source-docs/foundation",
            "source-docs",
            "Source document router foundation is available.",
        ),
        ("/api/v1/statuses/foundation", "statuses", "Status router foundation is available."),
    ],
)
def test_router_foundation_returns_planned_endpoints(
    client: TestClient,
    path: str,
    resource: str,
    message: str,
) -> None:
    """Router foundation endpoints should expose planned Sprint 2 API entries.

    Args:
        client: FastAPI test client.
        path: Endpoint path to call.
        resource: Expected resource name.
        message: Expected response message.
    """

    response = client.get(path)
    response_body = response.json()

    assert response.status_code == status.HTTP_200_OK
    assert response_body["result"] == "success"
    assert response_body["data"]["resource"] == resource
    assert response_body["data"]["sprint"] == "Sprint 2"
    assert response_body["data"]["status"] == "foundation-ready"
    assert len(response_body["data"]["planned_endpoints"]) >= 3
    assert response_body["message"] == message
