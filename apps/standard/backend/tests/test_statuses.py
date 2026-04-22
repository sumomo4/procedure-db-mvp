"""Tests for approval status routes."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApprovalStatusDetailData,
    ApprovalStatusListData,
    ApprovalStatusListItemData,
    ApprovalTransitionData,
)
from app.routers import statuses


def test_read_statuses_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status list API should return target data in the common envelope."""

    def fake_list_statuses(settings: AppSettings) -> ApprovalStatusListData:
        assert settings.app_env == "test"
        return ApprovalStatusListData(
            items=[
                ApprovalStatusListItemData(
                    target_id=1,
                    target_key="BP-STD-001",
                    target_name="M1確認用 原本A",
                    target_type="source-doc",
                    version_no=1,
                    status="draft",
                    status_label="作成中",
                    next_action="承認申請",
                    module_count=2,
                    enabled_module_count=2,
                    created_by="seed",
                    updated_at="2026-04-22",
                )
            ]
        )

    monkeypatch.setattr(statuses, "list_statuses", fake_list_statuses)

    response = client.get("/api/v1/statuses")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "items": [
                {
                    "target_id": 1,
                    "target_key": "BP-STD-001",
                    "target_name": "M1確認用 原本A",
                    "target_type": "source-doc",
                    "version_no": 1,
                    "status": "draft",
                    "status_label": "作成中",
                    "next_action": "承認申請",
                    "module_count": 2,
                    "enabled_module_count": 2,
                    "created_by": "seed",
                    "updated_at": "2026-04-22",
                }
            ]
        },
        "message": "Approval statuses are available.",
    }


def test_read_statuses_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status list API should return the common error envelope on DB failure."""

    def fake_list_statuses(settings: AppSettings) -> ApprovalStatusListData:
        del settings
        raise DatabaseConnectionError("Approval status list query failed.")

    monkeypatch.setattr(statuses, "list_statuses", fake_list_statuses)

    response = client.get("/api/v1/statuses")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Approval status list query failed.",
    }


def test_read_status_detail_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status detail API should return one target detail."""

    def fake_get_status_detail(
        settings: AppSettings,
        target_id: int,
    ) -> ApprovalStatusDetailData | None:
        assert settings.app_env == "test"
        assert target_id == 1
        return ApprovalStatusDetailData(
            target_id=1,
            target_key="BP-STD-001",
            target_name="M1確認用 原本A",
            target_type="source-doc",
            version_no=1,
            status="draft",
            status_label="作成中",
            next_action="承認申請",
            module_count=2,
            enabled_module_count=2,
            module_names=["初期点検手順", "部品交換手順"],
            description="確認用の原本です。",
            change_note="Sprint 2 seed",
            created_by="seed",
            updated_at="2026-04-22",
            allowed_transitions=[
                ApprovalTransitionData(
                    to_status="published",
                    to_status_label="承認済み",
                    action_label="承認申請",
                )
            ],
        )

    monkeypatch.setattr(statuses, "get_status_detail", fake_get_status_detail)

    response = client.get("/api/v1/statuses/1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "target_id": 1,
            "target_key": "BP-STD-001",
            "target_name": "M1確認用 原本A",
            "target_type": "source-doc",
            "version_no": 1,
            "status": "draft",
            "status_label": "作成中",
            "next_action": "承認申請",
            "module_count": 2,
            "enabled_module_count": 2,
            "module_names": ["初期点検手順", "部品交換手順"],
            "description": "確認用の原本です。",
            "change_note": "Sprint 2 seed",
            "created_by": "seed",
            "updated_at": "2026-04-22",
            "allowed_transitions": [
                {
                    "to_status": "published",
                    "to_status_label": "承認済み",
                    "action_label": "承認申請",
                }
            ],
        },
        "message": "Approval status detail is available.",
    }


def test_read_status_detail_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status detail API should return 404 when data does not exist."""

    def fake_get_status_detail(
        settings: AppSettings,
        target_id: int,
    ) -> ApprovalStatusDetailData | None:
        del settings, target_id
        return None

    monkeypatch.setattr(statuses, "get_status_detail", fake_get_status_detail)

    response = client.get("/api/v1/statuses/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Approval target was not found.",
    }


def test_read_status_detail_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status detail API should return the common error envelope on DB failure."""

    def fake_get_status_detail(
        settings: AppSettings,
        target_id: int,
    ) -> ApprovalStatusDetailData | None:
        del settings, target_id
        raise DatabaseConnectionError("Approval status detail query failed.")

    monkeypatch.setattr(statuses, "get_status_detail", fake_get_status_detail)

    response = client.get("/api/v1/statuses/1")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Approval status detail query failed.",
    }
