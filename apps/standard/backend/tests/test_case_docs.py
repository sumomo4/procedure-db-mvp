"""Tests for case document routes."""

from fastapi import status
from fastapi.testclient import TestClient


def _tokyo_prefecture(client: TestClient) -> str:
    response = client.get("/api/v1/case-docs/master/prefectures")
    return response.json()["data"]["items"][0]["value"]


def _tokyo_building(client: TestClient) -> str:
    response = client.get(
        "/api/v1/case-docs/master/buildings",
        params={"prefecture": _tokyo_prefecture(client)},
    )
    return response.json()["data"]["items"][0]["value"]


def test_read_case_doc_prefectures_returns_options(client: TestClient) -> None:
    """Prefecture master API should return selectable options."""

    response = client.get("/api/v1/case-docs/master/prefectures")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"] == "success"
    assert body["data"]["items"]
    assert body["data"]["items"][0]["value"]


def test_read_case_doc_unit_configs_returns_candidates(client: TestClient) -> None:
    """Unit configuration API should filter by selected location."""

    response = client.get(
        "/api/v1/case-docs/master/unit-config",
        params={"prefecture": _tokyo_prefecture(client), "building": _tokyo_building(client)},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"] == "success"
    assert body["data"]["items"] == [
        {
            "unit_config_id": "unit-tokyo-001",
            "fs_cluster_name": "FS-CL-TYO-01",
            "block": "B001",
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
        }
    ]


def test_resolve_case_doc_context_returns_no_manual_values(client: TestClient) -> None:
    """Resolve context API should return values derived from master data."""

    response = client.post(
        "/api/v1/case-docs/resolve-context",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "unit-tokyo-001",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["result"] == "success"
    data = body["data"]
    assert data["unit_config"]["unit_config_id"] == "unit-tokyo-001"
    assert data["host_assignments"]
    assert data["common_values"] == [
        {
            "key": "USER",
            "value": "cs-operator",
            "source": "case_common_values.operator_user",
        }
    ]
    assert any(item["placeholder"] == "SBC_COMMAND_FLOATING_IP" for item in data["resolved_placeholders"])


def test_resolve_case_doc_context_rejects_unknown_unit(client: TestClient) -> None:
    """Resolve context API should reject unknown selected master values."""

    response = client.post(
        "/api/v1/case-docs/resolve-context",
        json={
            "source_doc_id": 1,
            "prefecture": _tokyo_prefecture(client),
            "building": _tokyo_building(client),
            "unit_config_id": "missing",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["result"] == "error"
