"""API tests for the pre-registration module similarity check."""

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import DatabaseConnectionError
from app.core.responses import ModuleSimilarityCheckData
from app.routers import modules


def similarity_payload() -> dict[str, object]:
    """Return the minimum valid imported-module payload."""

    return {
        "module_name": "ログイン確認",
        "rows": [
            {
                "row_order": 1,
                "row_type": "step",
                "work_text": "TeraTermを起動する",
            }
        ],
    }


def test_similarity_check_returns_success(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The endpoint should return the service result in the common envelope."""

    monkeypatch.setattr(
        modules,
        "check_similar_modules",
        lambda _settings, _payload: ModuleSimilarityCheckData(
            threshold=0.70,
            checked_count=3,
            candidate_count=0,
            exact_match=False,
            input_sha256="a" * 64,
            candidates=[],
        ),
    )

    response = client.post(
        "/api/v1/modules/similarity-check",
        json=similarity_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "success"
    assert body["message"] == "類似モジュールを確認しました。"
    assert body["data"]["threshold"] == 0.70
    assert body["data"]["checked_count"] == 3


def test_similarity_check_returns_server_error_for_database_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Database failures should be exposed as an explicit API error."""

    def raise_database_error(*_args: object) -> ModuleSimilarityCheckData:
        raise DatabaseConnectionError("similarity query failed")

    monkeypatch.setattr(modules, "check_similar_modules", raise_database_error)

    response = client.post(
        "/api/v1/modules/similarity-check",
        json=similarity_payload(),
    )

    assert response.status_code == 500
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "similarity query failed",
    }
