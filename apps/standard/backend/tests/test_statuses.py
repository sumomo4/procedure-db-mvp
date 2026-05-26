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


def _build_detail(status_value: str = "draft") -> ApprovalStatusDetailData:
    allowed_transitions = (
        [
            ApprovalTransitionData(
                to_status="review_requested",
                to_status_label="承認依頼中",
                action_label="承認依頼",
            )
        ]
        if status_value == "draft"
        else [
            ApprovalTransitionData(
                to_status="published",
                to_status_label="承認済み",
                action_label="承認する",
            ),
            ApprovalTransitionData(
                to_status="returned",
                to_status_label="差戻し",
                action_label="差戻す",
            ),
        ]
        if status_value == "review_requested"
        else [
            ApprovalTransitionData(
                to_status="archived",
                to_status_label="保管済み",
                action_label="保管する",
            )
        ]
        if status_value == "published"
        else []
    )

    next_action = (
        "承認依頼"
        if status_value == "draft"
        else "承認または差戻し"
        if status_value == "review_requested"
        else "保管する"
        if status_value == "published"
        else "確認のみ"
    )

    return ApprovalStatusDetailData(
        target_id=1,
        target_key="BP-STD-001",
        target_name="M1原本CS 原本A",
        target_type="source-doc",
        version_no=1,
        status=status_value,  # type: ignore[arg-type]
        status_label="作成中" if status_value == "draft" else "承認依頼中" if status_value == "review_requested" else "差戻し" if status_value == "returned" else "承認済み" if status_value == "published" else "保管済み",
        next_action=next_action,
        module_count=2,
        enabled_module_count=2,
        module_names=["初期点検手順", "部品交換手順"],
        description="原本Aの説明です。",
        change_note="Sprint 3 seed",
        created_by="seed",
        updated_at="2026-04-23",
        allowed_transitions=allowed_transitions,
    )


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
                    target_name="M1原本CS 原本A",
                    target_type="source-doc",
                    version_no=1,
                    status="draft",
                    status_label="作成中",
                    next_action="承認依頼",
                    module_count=2,
                    enabled_module_count=2,
                    created_by="seed",
                    updated_at="2026-04-23",
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
                    "target_name": "M1原本CS 原本A",
                        "target_type": "source-doc",
                        "version_no": 1,
                        "version_major": 0,
                        "version_minor": 0,
                        "version_label": "ver.0.0",
                        "status": "draft",
                    "status_label": "作成中",
                    "next_action": "承認依頼",
                    "module_count": 2,
                    "enabled_module_count": 2,
                    "created_by": "seed",
                    "updated_at": "2026-04-23",
                }
            ]
        },
        "message": "承認状態一覧を取得しました。",
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
        return _build_detail("draft")

    monkeypatch.setattr(statuses, "get_status_detail", fake_get_status_detail)

    response = client.get("/api/v1/statuses/1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "target_id": 1,
            "target_key": "BP-STD-001",
            "target_name": "M1原本CS 原本A",
            "target_type": "source-doc",
            "version_no": 1,
            "version_major": 0,
            "version_minor": 0,
            "version_label": "ver.0.0",
            "status": "draft",
            "status_label": "作成中",
            "next_action": "承認依頼",
            "module_count": 2,
            "enabled_module_count": 2,
            "module_names": ["初期点検手順", "部品交換手順"],
            "description": "原本Aの説明です。",
            "change_note": "Sprint 3 seed",
            "created_by": "seed",
            "updated_at": "2026-04-23",
            "allowed_transitions": [
                {
                    "to_status": "review_requested",
                    "to_status_label": "承認依頼中",
                    "action_label": "承認依頼",
                }
            ],
            "history": [],
        },
        "message": "承認状態詳細を取得しました。",
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
        "message": "承認対象が見つかりませんでした。",
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


def test_patch_status_detail_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status patch API should update one target."""

    def fake_update_status(
        settings: AppSettings,
        target_id: int,
        to_status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> ApprovalStatusDetailData | None:
        assert settings.app_env == "test"
        assert target_id == 1
        assert to_status == "published"
        assert changed_by == "webui"
        assert note == "画面操作"
        return _build_detail("published")

    monkeypatch.setattr(statuses, "update_status", fake_update_status)

    response = client.patch(
        "/api/v1/statuses/1",
        json={"status": "published", "changed_by": "webui", "note": "画面操作"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"] == "success"
    assert response.json()["message"] == "承認状態を更新しました。"
    assert response.json()["data"]["status"] == "published"
    assert response.json()["data"]["next_action"] == "保管する"


def test_patch_status_detail_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status patch API should return 404 when data does not exist."""

    def fake_update_status(
        settings: AppSettings,
        target_id: int,
        to_status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> ApprovalStatusDetailData | None:
        del settings, target_id, to_status, changed_by, note
        return None

    monkeypatch.setattr(statuses, "update_status", fake_update_status)

    response = client.patch("/api/v1/statuses/999", json={"status": "published"})

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "承認対象が見つかりませんでした。",
    }


def test_patch_status_detail_returns_bad_request_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status patch API should return 400 on invalid transition."""

    def fake_update_status(
        settings: AppSettings,
        target_id: int,
        to_status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> ApprovalStatusDetailData | None:
        del settings, target_id, to_status, changed_by, note
        raise ValueError("status transition from archived to published is not allowed.")

    monkeypatch.setattr(statuses, "update_status", fake_update_status)

    response = client.patch("/api/v1/statuses/1", json={"status": "published"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "status transition from archived to published is not allowed.",
    }


def test_patch_status_detail_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Approval status patch API should return 500 on DB failure."""

    def fake_update_status(
        settings: AppSettings,
        target_id: int,
        to_status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> ApprovalStatusDetailData | None:
        del settings, target_id, to_status, changed_by, note
        raise DatabaseConnectionError("Approval status update failed.")

    monkeypatch.setattr(statuses, "update_status", fake_update_status)

    response = client.patch("/api/v1/statuses/1", json={"status": "published"})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Approval status update failed.",
    }
