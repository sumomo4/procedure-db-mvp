"""Tests for module routes."""

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import (
    ApprovalStatusDetailData,
    ApprovalTransitionData,
    ModuleDetailData,
    ModuleDiffData,
    ModuleDiffRowData,
    ModuleDiffSummaryData,
    ModuleDeviceHeaderData,
    ModuleListData,
    ModuleListItemData,
    ModuleRowData,
    ModuleRowDeviceEntryData,
    ModuleRowImageData,
    ModuleSimilarityCandidateData,
    ModuleSimilarityCheckData,
    ModuleSimilarityScoreBreakdownData,
    ModuleVersionListData,
    ModuleVersionListItemData,
)
from app.routers import modules


PNG_BYTES = b"\x89PNG\r\n\x1a\nfake-image-bytes"


def build_similarity_check_result(
    *,
    with_candidate: bool,
) -> ModuleSimilarityCheckData:
    """Build a deterministic similarity result for create-route tests."""

    candidate = ModuleSimilarityCandidateData(
        module_id=1,
        module_key="MOD-001",
        module_name="Existing module",
        module_version_id=10,
        version_no=1,
        version_label="ver.1.0",
        status="published",
        similarity=0.92,
        exact_match=False,
        image_metadata_match=True,
        score_breakdown=ModuleSimilarityScoreBreakdownData(
            work_text=0.95,
            expected_result=0.90,
            command=0.91,
            name=0.88,
            structure=1.0,
            device_header=1.0,
        ),
        matched_fields=["作業内容", "確認事項", "コマンド"],
    )
    return ModuleSimilarityCheckData(
        threshold=0.70,
        checked_count=1,
        candidate_count=1 if with_candidate else 0,
        exact_match=False,
        input_sha256="a" * 64,
        candidate_set_sha256="b" * 64,
        confirmation_token="signed-token" if with_candidate else None,
        candidates=[candidate] if with_candidate else [],
    )


def build_created_module_detail() -> ModuleDetailData:
    """Build a compact successful module-create response."""

    return ModuleDetailData(
        module_id=4,
        module_key="MOD-004",
        module_name="Created module",
        description=None,
        module_version_id=40,
        version_no=1,
        status="draft",
        status_label="作成中",
        row_count=0,
        source_xlsx_path=None,
        created_by="codex",
        header_time_text=None,
        target_text=None,
        common_p_text=None,
        target_device_text=None,
        created_at="2026-07-26",
        updated_at="2026-07-26",
        rows=[],
    )


def build_module_status_detail(status_value: str = "draft") -> ApprovalStatusDetailData:
    """Build deterministic module version approval status detail."""

    allowed_transitions = (
        [
            ApprovalTransitionData(
                to_status="review_requested",
                to_status_label="承認依頼中",
                action_label="承認依頼",
            ),
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

    return ApprovalStatusDetailData(
        target_id=1,
        target_key="MOD-001",
        target_name="Initial check procedure",
        target_type="module",
        version_no=2,
        status=status_value,
        status_label="作成中" if status_value == "draft" else "承認依頼中" if status_value == "review_requested" else "差戻し" if status_value == "returned" else status_value,
        next_action="承認依頼" if status_value == "draft" else "承認または差戻し" if status_value == "review_requested" else "再承認依頼" if status_value == "returned" else "保管する",
        module_count=1,
        enabled_module_count=1,
        module_names=["Initial check procedure"],
        description="Description",
        change_note="Updated from Excel",
        created_by="codex",
        updated_at="2026-05-21",
        allowed_transitions=allowed_transitions,
        history=[],
    )


def test_read_modules_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module list API should return module data in the common envelope."""

    def fake_list_modules(
        settings: AppSettings,
        keyword: str | None = None,
        status_filter: str | None = None,
        folder_paths: list[str] | None = None,
        created_by: str | None = None,
        updated_from: str | None = None,
        updated_to: str | None = None,
        has_images: str | None = None,
        sort: str | None = None,
    ) -> ModuleListData:
        """Return deterministic module list data."""

        assert settings.app_env == "test"
        assert keyword == "点検"
        assert status_filter == "draft"
        assert folder_paths == ["ネットワーク", "SBC"]
        return ModuleListData(
            items=[
                ModuleListItemData(
                    module_id=1,
                    module_key="MOD-001",
                    module_name="初期点検手順",
                    description="説明",
                    folder_path="未分類",
                    folder_paths=["未分類"],
                    module_version_id=10,
                    version_no=1,
                    status="draft",
                    status_label="作成中",
                    row_count=3,
                    first_work_text="作業開始前の状態を確認する",
                    source_xlsx_path=None,
                    created_by="seed",
                    updated_at="2026-04-22",
                )
            ],
            folders=["未分類"],
        )

    monkeypatch.setattr(modules, "list_modules", fake_list_modules)

    response = client.get(
        "/api/v1/modules?keyword=点検&status=draft"
        "&folder_path=ネットワーク&folder_path=SBC"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "items": [
                {
                    "module_id": 1,
                    "module_key": "MOD-001",
                    "module_name": "初期点検手順",
                    "description": "説明",
                    "folder_path": "未分類",
                    "folder_paths": ["未分類"],
                        "module_version_id": 10,
                        "version_no": 1,
                        "version_major": 0,
                        "version_minor": 0,
                        "version_label": "ver.0.0",
                        "status": "draft",
                    "status_label": "作成中",
                    "row_count": 3,
                    "first_work_text": "作業開始前の状態を確認する",
                    "source_xlsx_path": None,
                    "created_by": "seed",
                    "updated_at": "2026-04-22",
                }
            ],
            "folders": ["未分類"],
        },
        "message": "モジュール一覧を取得しました。",
    }


def test_read_modules_rejects_invalid_status(client: TestClient) -> None:
    """Module list API should reject unsupported status values."""

    response = client.get("/api/v1/modules?status=invalid")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "status must be one of all, draft, review_requested, returned, published, archived.",
    }


def test_read_modules_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module list API should return the common error envelope on DB failure."""

    def fake_list_modules(
        settings: AppSettings,
        keyword: str | None = None,
        status_filter: str | None = None,
        folder_paths: list[str] | None = None,
        created_by: str | None = None,
        updated_from: str | None = None,
        updated_to: str | None = None,
        has_images: str | None = None,
        sort: str | None = None,
    ) -> ModuleListData:
        """Raise a deterministic database error."""

        del settings, keyword, status_filter
        raise DatabaseConnectionError("Module list query failed.")

    monkeypatch.setattr(modules, "list_modules", fake_list_modules)

    response = client.get("/api/v1/modules")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Module list query failed.",
    }


def test_delete_module_folder_returns_modules_to_uncategorized(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Folder deletion should call the database helper and return a success response."""

    def fake_delete_module_folder(settings: AppSettings, folder_path: str) -> ModuleListData:
        assert settings.app_env == "test"
        assert folder_path == "TEST"
        return ModuleListData(items=[], folders=["未分類", "test"])

    monkeypatch.setattr(modules, "delete_module_folder", fake_delete_module_folder)

    response = client.request("DELETE", "/api/v1/modules/folders", json={"folder_path": "TEST"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {"items": [], "folders": ["未分類", "test"]},
        "message": "タグを削除しました。タグがなくなったモジュールは未分類へ移動しました。",
    }


def test_delete_module_folder_rejects_uncategorized(client: TestClient) -> None:
    """The uncategorized folder is the fallback and must not be deleted."""

    response = client.request("DELETE", "/api/v1/modules/folders", json={"folder_path": "未分類"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "The uncategorized folder cannot be deleted.",
    }


def test_add_modules_to_folder_keeps_existing_memberships(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Folder assignment should call the additive database helper."""

    def fake_move_modules_to_folder(
        settings: AppSettings,
        module_ids: list[int],
        folder_path: str,
    ) -> ModuleListData:
        assert settings.app_env == "test"
        assert module_ids == [1, 2]
        assert folder_path == "ネットワーク/SBC"
        return ModuleListData(items=[], folders=["既存", "ネットワーク/SBC"])

    monkeypatch.setattr(modules, "move_modules_to_folder", fake_move_modules_to_folder)

    response = client.patch(
        "/api/v1/modules/folders/modules",
        json={"module_ids": [1, 2], "folder_path": "ネットワーク/SBC"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {"items": [], "folders": ["既存", "ネットワーク/SBC"]},
        "message": "選択したモジュールへタグを追加しました。",
    }


def test_read_module_detail_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module detail API should return module data and rows."""

    def fake_get_module_detail(
        settings: AppSettings,
        module_id: int,
        version_no: int | None = None,
    ) -> ModuleDetailData | None:
        """Return deterministic module detail data."""

        assert settings.app_env == "test"
        assert module_id == 1
        return ModuleDetailData(
            module_id=1,
            module_key="MOD-001",
            module_name="Initial check procedure",
            description="Description",
            module_version_id=10,
            version_no=1,
            status="draft",
            status_label="Draft",
            row_count=1,
            source_xlsx_path=None,
            created_by="seed",
            header_time_text="09:00",
            target_text="CS",
            common_p_text=">",
            target_device_text="device-01",
            device_headers=[
                ModuleDeviceHeaderData(
                    slot_no=1,
                    header_time_text="09:00",
                    target_text="CS",
                    p_text=">",
                    target_device_text="device-01",
                )
            ],
            created_at="2026-04-22",
            updated_at="2026-04-22",
            rows=[
                ModuleRowData(
                    module_row_id=100,
                    row_order=1,
                    row_type="step",
                    major_no="1",
                    middle_no="1",
                    minor_no="1",
                    tech_doc_text="Tech doc",
                    work_text="Check before work.",
                    indent_level=1,
                    expected_result="Ready.",
                    time_text="□",
                    window_text=None,
                    p_text="TT",
                    command_text="show status",
                    note=None,
                    device_entries=[
                        ModuleRowDeviceEntryData(
                            slot_no=1,
                            time_text="□",
                            window_text=None,
                            p_text="TT",
                            command_text="show status",
                        )
                    ],
                )
            ],
        )

    monkeypatch.setattr(modules, "get_module_detail", fake_get_module_detail)

    response = client.get("/api/v1/modules/1")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "result": "success",
        "data": {
            "module_id": 1,
            "module_key": "MOD-001",
            "module_name": "Initial check procedure",
            "description": "Description",
                "module_version_id": 10,
                "version_no": 1,
                "version_major": 0,
                "version_minor": 0,
                "version_label": "ver.0.0",
                "status": "draft",
            "status_label": "Draft",
            "row_count": 1,
            "source_xlsx_path": None,
            "created_by": "seed",
            "header_time_text": "09:00",
            "target_text": "CS",
            "common_p_text": ">",
            "target_device_text": "device-01",
            "device_headers": [
                {
                    "slot_no": 1,
                    "header_time_text": "09:00",
                    "target_text": "CS",
                    "p_text": ">",
                    "target_device_text": "device-01",
                }
            ],
            "created_at": "2026-04-22",
            "updated_at": "2026-04-22",
            "rows": [
                {
                    "module_row_id": 100,
                    "row_order": 1,
                    "row_type": "step",
                    "major_no": "1",
                    "middle_no": "1",
                    "minor_no": "1",
                    "tech_doc_text": "Tech doc",
                    "work_text": "Check before work.",
                    "indent_level": 1,
                    "expected_result": "Ready.",
                    "time_text": "□",
                    "window_text": None,
                    "p_text": "TT",
                    "command_text": "show status",
                    "note": None,
                    "device_entries": [
                        {
                            "slot_no": 1,
                            "time_text": "□",
                            "window_text": None,
                            "p_text": "TT",
                            "command_text": "show status",
                        }
                    ],
                    "images": [],
                }
            ],
        },
        "message": "モジュール詳細を取得しました。",
    }


def test_read_module_detail_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module detail API should return 404 when data does not exist."""

    def fake_get_module_detail(
        settings: AppSettings,
        module_id: int,
        version_no: int | None = None,
    ) -> ModuleDetailData | None:
        """Return no module detail data."""

        del settings, module_id
        return None

    monkeypatch.setattr(modules, "get_module_detail", fake_get_module_detail)

    response = client.get("/api/v1/modules/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "モジュールが見つかりませんでした。",
    }


def test_read_module_detail_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module detail API should return the common error envelope on DB failure."""

    def fake_get_module_detail(
        settings: AppSettings,
        module_id: int,
        version_no: int | None = None,
    ) -> ModuleDetailData | None:
        """Raise a deterministic database error."""

        del settings, module_id, version_no
        raise DatabaseConnectionError("モジュール詳細の取得に失敗しました。")

    monkeypatch.setattr(modules, "get_module_detail", fake_get_module_detail)

    response = client.get("/api/v1/modules/1")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "モジュール詳細の取得に失敗しました。",
    }


def test_read_module_diff_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module diff API should return structured row diff data."""

    before_row = ModuleRowData(
        module_row_id=100,
        row_order=1,
        row_type="step",
        major_no=None,
        middle_no=None,
        minor_no=None,
        tech_doc_text=None,
        work_text="Before",
        indent_level=0,
        expected_result=None,
        time_text=None,
        window_text=None,
        p_text=None,
        command_text=None,
        note=None,
        device_entries=[],
        images=[],
    )
    after_row = before_row.model_copy(update={"module_row_id": 200, "work_text": "After"})

    def fake_get_module_diff(
        settings: AppSettings,
        module_id: int,
        from_version: int,
        to_version: int,
    ) -> ModuleDiffData | None:
        """Return deterministic module diff data."""

        assert settings.app_env == "test"
        assert module_id == 1
        assert from_version == 1
        assert to_version == 2
        return ModuleDiffData(
            module_id=1,
            module_key="MOD-001",
            module_name="Initial check procedure",
            from_version=1,
            to_version=2,
            summary=ModuleDiffSummaryData(added_count=0, removed_count=0, changed_count=1, unchanged_count=0),
            rows=[
                ModuleDiffRowData(
                    status="changed",
                    row_key="row_order:1->1",
                    before=before_row,
                    after=after_row,
                    changed_fields=["work_text"],
                    similarity=0.8,
                )
            ],
        )

    monkeypatch.setattr(modules, "get_module_diff", fake_get_module_diff)

    response = client.get("/api/v1/modules/1/diff?from_version=1&to_version=2")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["result"] == "success"
    assert payload["message"] == "モジュール差分を取得しました。"
    assert payload["data"]["summary"] == {
        "added_count": 0,
        "removed_count": 0,
        "changed_count": 1,
        "unchanged_count": 0,
    }
    assert payload["data"]["rows"][0]["status"] == "changed"
    assert payload["data"]["rows"][0]["changed_fields"] == ["work_text"]


def test_read_module_diff_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module diff API should return 404 when one version is missing."""

    def fake_get_module_diff(
        settings: AppSettings,
        module_id: int,
        from_version: int,
        to_version: int,
    ) -> ModuleDiffData | None:
        """Return no module diff data."""

        del settings, module_id, from_version, to_version
        return None

    monkeypatch.setattr(modules, "get_module_diff", fake_get_module_diff)

    response = client.get("/api/v1/modules/1/diff?from_version=1&to_version=99")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "比較対象のモジュール版が見つかりませんでした。",
    }


def test_read_module_diff_preview_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsaved import diff API should return structured diff data."""

    diff_data = ModuleDiffData(
        module_id=1,
        module_key="MOD-001",
        module_name="Initial check procedure",
        from_version=1,
        to_version=2,
        summary=ModuleDiffSummaryData(added_count=1, removed_count=0, changed_count=0, unchanged_count=1),
        rows=[],
    )

    def fake_get_module_diff_preview(
        settings: AppSettings,
        module_id: int,
        version_no: int,
        payload: object,
    ) -> ModuleDiffData | None:
        assert settings.app_env == "test"
        assert module_id == 1
        assert version_no == 1
        assert getattr(payload, "module_name") == "Imported module"
        return diff_data

    monkeypatch.setattr(modules, "get_module_diff_preview", fake_get_module_diff_preview)

    response = client.post(
        "/api/v1/modules/1/diff-preview?version_no=1",
        json={
            "module_name": "Imported module",
            "rows": [
                {
                    "row_order": 1,
                    "row_type": "step",
                    "work_text": "Check system status",
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["result"] == "success"
    assert payload["message"] == "取込内容との差分を取得しました。"
    assert payload["data"]["summary"]["added_count"] == 1


def test_read_module_diff_preview_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsaved import diff API should return 404 when candidate version is missing."""

    monkeypatch.setattr(modules, "get_module_diff_preview", lambda *args, **kwargs: None)

    response = client.post(
        "/api/v1/modules/999/diff-preview?version_no=1",
        json={
            "module_name": "Imported module",
            "rows": [
                {
                    "row_order": 1,
                    "row_type": "step",
                    "work_text": "Check system status",
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["message"] == "比較対象のモジュール版が見つかりませんでした。"


def test_read_module_versions_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module versions API should return version list."""

    def fake_list_module_versions(settings: AppSettings, module_id: int) -> ModuleVersionListData | None:
        """Return deterministic module versions."""

        assert settings.app_env == "test"
        assert module_id == 1
        return ModuleVersionListData(
            module_id=1,
            module_key="MOD-001",
            module_name="Initial check procedure",
            items=[
                ModuleVersionListItemData(
                    module_version_id=20,
                    version_no=2,
                    status="draft",
                    status_label="作成中",
                    row_count=2,
                    source_xlsx_path="module-v2.xlsm",
                    created_by="webui",
                    created_at="2026-05-21",
                    updated_at="2026-05-21",
                ),
                ModuleVersionListItemData(
                    module_version_id=10,
                    version_no=1,
                    status="published",
                    status_label="承認済み",
                    row_count=1,
                    source_xlsx_path="module-v1.xlsm",
                    created_by="webui",
                    created_at="2026-05-20",
                    updated_at="2026-05-20",
                ),
            ],
        )

    monkeypatch.setattr(modules, "list_module_versions", fake_list_module_versions)

    response = client.get("/api/v1/modules/1/versions")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["result"] == "success"
    assert payload["message"] == "モジュール版一覧を取得しました。"
    assert payload["data"]["items"][0]["version_no"] == 2
    assert payload["data"]["items"][1]["status"] == "published"


def test_read_module_versions_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module versions API should return 404 when module is missing."""

    def fake_list_module_versions(settings: AppSettings, module_id: int) -> ModuleVersionListData | None:
        """Return no module versions."""

        del settings, module_id
        return None

    monkeypatch.setattr(modules, "list_module_versions", fake_list_module_versions)

    response = client.get("/api/v1/modules/99/versions")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "モジュールが見つかりませんでした。",
    }


def test_read_module_version_status_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module version status API should return approval detail."""

    def fake_get_module_version_status(
        settings: AppSettings,
        module_id: int,
        version_no: int,
    ) -> ApprovalStatusDetailData | None:
        """Return deterministic module status detail."""

        assert settings.app_env == "test"
        assert module_id == 1
        assert version_no == 2
        return build_module_status_detail()

    monkeypatch.setattr(modules, "get_module_version_status", fake_get_module_version_status)

    response = client.get("/api/v1/modules/1/versions/2/status")

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["result"] == "success"
    assert payload["message"] == "モジュール版の承認状態を取得しました。"
    assert payload["data"]["target_type"] == "module"
    assert payload["data"]["version_no"] == 2


def test_patch_module_version_status_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module version status API should update approval status."""

    def fake_update_module_version_status(
        settings: AppSettings,
        module_id: int,
        version_no: int,
        to_status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> ApprovalStatusDetailData | None:
        """Return deterministic updated module status detail."""

        assert settings.app_env == "test"
        assert module_id == 1
        assert version_no == 2
        assert to_status == "published"
        assert changed_by == "承認者ユーザー"
        assert note == "OK"
        return build_module_status_detail("published")

    monkeypatch.setattr(modules, "update_module_version_status", fake_update_module_version_status)

    response = client.patch(
        "/api/v1/modules/1/versions/2/status",
        json={"status": "published", "changed_by": "承認者ユーザー", "note": "OK"},
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["result"] == "success"
    assert payload["message"] == "モジュール版の承認状態を更新しました。"
    assert payload["data"]["target_type"] == "module"
    assert payload["data"]["status"] == "published"


def test_patch_module_version_status_returns_validation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module version status API should return validation errors."""

    def fake_update_module_version_status(
        settings: AppSettings,
        module_id: int,
        version_no: int,
        to_status: str,
        changed_by: str | None = None,
        note: str | None = None,
    ) -> ApprovalStatusDetailData | None:
        """Raise deterministic validation error."""

        del settings, module_id, version_no, to_status, changed_by, note
        raise ValueError("status transition from archived to draft is not allowed.")

    monkeypatch.setattr(modules, "update_module_version_status", fake_update_module_version_status)

    response = client.patch("/api/v1/modules/1/versions/2/status", json={"status": "draft"})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "status transition from archived to draft is not allowed.",
    }


def test_read_module_row_image_returns_file(
    client: TestClient,
    test_settings: AppSettings,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module row image API should return the stored image file."""

    image_root = tmp_path / "module_images"
    image_file = image_root / "MOD-001" / "row-image.png"
    image_file.parent.mkdir(parents=True)
    image_file.write_bytes(PNG_BYTES)
    test_settings.module_image_storage_dir = str(image_root)

    def fake_get_module_row_image(settings: AppSettings, module_row_image_id: int) -> ModuleRowImageData | None:
        """Return deterministic image metadata."""

        assert settings.app_env == "test"
        assert module_row_image_id == 1
        return ModuleRowImageData(
            module_row_image_id=1,
            image_key="MOD-001_r1_img1",
            image_path=str(image_file),
            anchor_cell="E8",
            offset_x_px=0,
            offset_y_px=0,
            width_px=120,
            height_px=80,
            image_order=1,
        )

    monkeypatch.setattr(modules, "get_module_row_image", fake_get_module_row_image)

    response = client.get("/api/v1/modules/images/1")

    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "image/png"
    assert response.content == PNG_BYTES


def test_read_module_row_image_rejects_outside_storage(
    client: TestClient,
    test_settings: AppSettings,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module row image API should not serve files outside image storage."""

    image_root = tmp_path / "module_images"
    outside_file = tmp_path / "outside.png"
    image_root.mkdir()
    outside_file.write_bytes(PNG_BYTES)
    test_settings.module_image_storage_dir = str(image_root)

    def fake_get_module_row_image(settings: AppSettings, module_row_image_id: int) -> ModuleRowImageData | None:
        """Return image metadata pointing outside storage."""

        del settings, module_row_image_id
        return ModuleRowImageData(
            module_row_image_id=1,
            image_key="outside",
            image_path=str(outside_file),
            anchor_cell="E8",
            offset_x_px=0,
            offset_y_px=0,
            width_px=None,
            height_px=None,
            image_order=1,
        )

    monkeypatch.setattr(modules, "get_module_row_image", fake_get_module_row_image)

    response = client.get("/api/v1/modules/images/1")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "画像が見つかりませんでした。",
    }


def test_read_module_row_image_returns_not_found_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module row image API should return 404 when metadata does not exist."""

    def fake_get_module_row_image(settings: AppSettings, module_row_image_id: int) -> ModuleRowImageData | None:
        """Return no image metadata."""

        del settings, module_row_image_id
        return None

    monkeypatch.setattr(modules, "get_module_row_image", fake_get_module_row_image)

    response = client.get("/api/v1/modules/images/999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "画像が見つかりませんでした。",
    }


def test_create_module_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module create API should create a module and return detail data."""

    def fake_create_module(settings: AppSettings, payload: object) -> ModuleDetailData:
        assert settings.app_env == "test"
        assert payload.module_name == "Created module"
        assert payload.target_text == "CS"
        assert payload.target_device_text == "device-01"
        assert len(payload.rows) == 2
        return ModuleDetailData(
            module_id=4,
            module_key="MOD-004",
            module_name="Created module",
            description="Created from API",
            module_version_id=40,
            version_no=1,
            status="draft",
            status_label="作成中",
            row_count=2,
            source_xlsx_path="imports/MOD-004.xlsx",
            created_by="codex",
            header_time_text="09:00",
            target_text="CS",
            common_p_text=">",
            target_device_text="device-01",
            device_headers=[
                ModuleDeviceHeaderData(
                    slot_no=1,
                    header_time_text="09:00",
                    target_text="CS",
                    p_text=">",
                    target_device_text="device-01",
                )
            ],
            created_at="2026-04-22",
            updated_at="2026-04-22",
            rows=[
                ModuleRowData(
                    module_row_id=400,
                    row_order=1,
                    row_type="header",
                    major_no=None,
                    middle_no=None,
                    minor_no=None,
                    tech_doc_text="Header note",
                    work_text="Preparation",
                    indent_level=0,
                    expected_result=None,
                    time_text=None,
                    window_text=None,
                    p_text=None,
                    command_text=None,
                    note=None,
                    device_entries=[],
                ),
                ModuleRowData(
                    module_row_id=401,
                    row_order=2,
                    row_type="step",
                    major_no="1",
                    middle_no="1",
                    minor_no="1",
                    tech_doc_text="Tech doc",
                    work_text="Run command",
                    indent_level=1,
                    expected_result="Succeeded",
                    time_text="5分",
                    window_text="console",
                    p_text=">",
                    command_text="show version",
                    note=None,
                    device_entries=[
                        ModuleRowDeviceEntryData(
                            slot_no=1,
                            time_text="5分",
                            window_text="console",
                            p_text=">",
                            command_text="show version",
                        )
                    ],
                ),
            ],
        )

    monkeypatch.setattr(modules, "create_module", fake_create_module)
    monkeypatch.setattr(
        modules,
        "check_similar_modules",
        lambda _settings, _payload: build_similarity_check_result(
            with_candidate=False
        ),
    )

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "description": "Created from API",
            "source_xlsx_path": "imports/MOD-004.xlsx",
            "created_by": "codex",
            "header_time_text": "09:00",
            "target_text": "CS",
            "common_p_text": ">",
            "target_device_text": "device-01",
            "rows": [
                {
                    "row_order": 1,
                    "row_type": "header",
                    "tech_doc_text": "Header note",
                    "work_text": "Preparation",
                    "indent_level": 0,
                },
                {
                    "row_order": 2,
                    "row_type": "step",
                    "major_no": "1",
                    "middle_no": "1",
                    "minor_no": "1",
                    "tech_doc_text": "Tech doc",
                    "work_text": "Run command",
                    "indent_level": 1,
                    "expected_result": "Succeeded",
                    "time_text": "5分",
                    "window_text": "console",
                    "p_text": ">",
                    "command_text": "show version",
                },
            ],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["result"] == "success"
    assert response.json()["message"] == "モジュールを登録しました。"
    assert response.json()["data"]["module_key"] == "MOD-004"
    assert response.json()["data"]["row_count"] == 2


def test_create_module_rejects_invalid_payload(client: TestClient) -> None:
    """Module create API should reject invalid request bodies."""

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "rows": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Request validation failed: 1 error(s).",
    }


def test_create_module_rejects_business_validation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module create API should return 400 for business validation errors."""

    def fake_create_module(settings: AppSettings, payload: object) -> ModuleDetailData:
        del settings, payload
        raise ValueError("row_order must be unique within rows.")

    monkeypatch.setattr(modules, "create_module", fake_create_module)
    monkeypatch.setattr(
        modules,
        "check_similar_modules",
        lambda _settings, _payload: build_similarity_check_result(
            with_candidate=False
        ),
    )

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "rows": [
                {"row_order": 1, "row_type": "step"},
                {"row_order": 1, "row_type": "step"},
            ],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "row_order must be unique within rows.",
    }


def test_create_module_returns_error_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Module create API should return the common error envelope on DB failure."""

    def fake_create_module(settings: AppSettings, payload: object) -> ModuleDetailData:
        del settings, payload
        raise DatabaseConnectionError("Module create failed.")

    monkeypatch.setattr(modules, "create_module", fake_create_module)
    monkeypatch.setattr(
        modules,
        "check_similar_modules",
        lambda _settings, _payload: build_similarity_check_result(
            with_candidate=False
        ),
    )

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "rows": [{"row_order": 1, "row_type": "step"}],
        },
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Module create failed.",
    }


def test_create_module_requires_confirmation_for_similarity_candidates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate-bearing request should return 409 before database writes."""

    monkeypatch.setattr(
        modules,
        "check_similar_modules",
        lambda _settings, _payload: build_similarity_check_result(
            with_candidate=True
        ),
    )
    monkeypatch.setattr(
        modules,
        "validate_similarity_confirmation_token",
        lambda _settings, _result, _token: False,
    )

    def fail_if_created(_settings: AppSettings, _payload: object) -> ModuleDetailData:
        raise AssertionError("create_module must not run before confirmation")

    monkeypatch.setattr(modules, "create_module", fail_if_created)

    response = client.post(
        "/api/v1/modules",
        json={
            "module_name": "Created module",
            "rows": [{"row_order": 1, "row_type": "step"}],
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["result"] == "error"
    assert response.json()["data"]["candidate_count"] == 1
    assert response.json()["data"]["confirmation_token"] == "signed-token"


def test_create_module_accepts_latest_similarity_confirmation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid confirmation token should allow the create operation."""

    similarity_result = build_similarity_check_result(with_candidate=True)
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        modules,
        "check_similar_modules",
        lambda _settings, _payload: similarity_result,
    )

    def fake_validate(
        _settings: AppSettings,
        result: ModuleSimilarityCheckData,
        token: str | None,
    ) -> bool:
        captured["result"] = result
        captured["token"] = token
        return token == "signed-token"

    monkeypatch.setattr(
        modules,
        "validate_similarity_confirmation_token",
        fake_validate,
    )
    monkeypatch.setattr(
        modules,
        "create_module",
        lambda _settings, _payload: build_created_module_detail(),
    )

    response = client.post(
        "/api/v1/modules?similarity_confirmation_token=signed-token",
        json={
            "module_name": "Created module",
            "rows": [{"row_order": 1, "row_type": "step"}],
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["result"] == "success"
    assert response.json()["data"]["module_key"] == "MOD-004"
    assert captured == {
        "result": similarity_result,
        "token": "signed-token",
    }


def test_normalize_module_sheet_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sheet-normalize API should return a create payload preview."""

    def fake_build_module_create_request_from_sheet_data(**kwargs: object) -> object:
        assert kwargs["module_name"] == "Excel import module"
        assert len(kwargs["device_header_cells"]) == 2
        assert len(kwargs["row_cells"]) == 1
        return {
            "module_key": "MOD-900",
            "module_name": "Excel import module",
            "description": "Imported from one sheet",
            "change_note": "Initial import",
            "source_xlsx_path": "imports/sample.xlsx",
            "source_sha256": "abc123",
            "created_by": "codex",
            "header_time_text": None,
            "target_text": None,
            "common_p_text": None,
            "target_device_text": None,
            "device_headers": [
                {
                    "slot_no": 1,
                    "header_time_text": "09:00",
                    "target_text": "target-1",
                    "p_text": ">",
                    "target_device_text": "device-01",
                },
                {
                    "slot_no": 2,
                    "header_time_text": "09:05",
                    "target_text": "target-2",
                    "p_text": "#",
                    "target_device_text": "device-02",
                },
            ],
            "rows": [
                {
                    "row_order": 1,
                    "row_type": "step",
                    "major_no": "1",
                    "middle_no": "1",
                    "minor_no": "1",
                    "tech_doc_text": "Tech doc",
                    "work_text": "Check command",
                    "indent_level": 1,
                    "expected_result": "Ready.",
                    "time_text": None,
                    "window_text": None,
                    "p_text": None,
                    "command_text": None,
                    "note": None,
                    "device_entries": [
                        {
                            "slot_no": 1,
                            "time_text": "10:00",
                            "window_text": "STOP",
                            "p_text": ">",
                            "command_text": "show version",
                        },
                        {
                            "slot_no": 2,
                            "time_text": "10:05",
                            "window_text": "STOP",
                            "p_text": "#",
                            "command_text": "show status",
                        },
                    ],
                }
            ],
        }

    monkeypatch.setattr(
        modules,
        "build_module_create_request_from_sheet_data",
        fake_build_module_create_request_from_sheet_data,
    )

    response = client.post(
        "/api/v1/modules/import-sheet",
        json={
            "module_name": "Excel import module",
            "description": "Imported from one sheet",
            "change_note": "Initial import",
            "source_xlsx_path": "imports/sample.xlsx",
            "source_sha256": "abc123",
            "created_by": "codex",
            "device_header_cells": [
                {
                    "slot_no": 1,
                    "header_time_text": "09:00",
                    "target_text": "target-1",
                    "p_text": ">",
                    "target_device_text": "device-01",
                },
                {
                    "slot_no": 2,
                    "header_time_text": "09:05",
                    "target_text": "target-2",
                    "p_text": "#",
                    "target_device_text": "device-02",
                },
            ],
            "row_cells": [
                {
                    "A": "1",
                    "B": "1",
                    "C": "1",
                    "D": "Tech doc",
                    "F": "Check command",
                    "I": "Ready.",
                    "device_entries": [
                        {
                            "slot_no": 1,
                            "time_text": "10:00",
                            "window_text": "STOP",
                            "p_text": ">",
                            "command_text": "show version",
                        },
                        {
                            "slot_no": 2,
                            "time_text": "10:05",
                            "window_text": "STOP",
                            "p_text": "#",
                            "command_text": "show status",
                        },
                    ],
                }
            ],
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"] == "success"
    assert response.json()["message"] == "Excel取込プレビューを正規化しました。"
    assert response.json()["data"]["module_name"] == "Excel import module"
    assert len(response.json()["data"]["device_headers"]) == 2
    assert response.json()["data"]["rows"][0]["device_entries"][1]["slot_no"] == 2


def test_normalize_module_sheet_rejects_business_validation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sheet-normalize API should return 400 for helper validation errors."""

    def fake_build_module_create_request_from_sheet_data(**kwargs: object) -> object:
        del kwargs
        raise ValueError("Excel device headers must not exceed 20 slots.")

    monkeypatch.setattr(
        modules,
        "build_module_create_request_from_sheet_data",
        fake_build_module_create_request_from_sheet_data,
    )

    response = client.post(
        "/api/v1/modules/import-sheet",
        json={
            "module_name": "Excel import module",
            "row_cells": [{"A": "1"}],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Excel device headers must not exceed 20 slots.",
    }


def test_normalize_module_sheet_rejects_invalid_payload(client: TestClient) -> None:
    """Sheet-normalize API should reject invalid request bodies."""

    response = client.post(
        "/api/v1/modules/import-sheet",
        json={
            "module_name": "Excel import module",
            "row_cells": [],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "Request validation failed: 1 error(s).",
    }


def test_import_module_workbook_returns_success_response(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workbook import API should normalize uploaded bytes into create payload."""

    def fake_build_module_create_request_from_workbook_bytes(**kwargs: object) -> object:
        assert kwargs["filename"] == "sample.xlsx"
        assert kwargs["created_by"] == "codex"
        assert kwargs["workbook_bytes"] == b"sample-bytes"
        return {
            "module_key": None,
            "module_name": "Workbook module",
            "description": None,
            "change_note": "imported from workbook upload",
            "source_xlsx_path": "sample.xlsx",
            "source_sha256": "abc123",
            "created_by": "codex",
            "header_time_text": None,
            "target_text": None,
            "common_p_text": None,
            "target_device_text": None,
            "device_headers": [{"slot_no": 1, "target_device_text": "device-01"}],
            "rows": [{"row_order": 1, "row_type": "step", "device_entries": []}],
        }

    monkeypatch.setattr(
        modules,
        "build_module_create_request_from_workbook_bytes",
        fake_build_module_create_request_from_workbook_bytes,
    )

    response = client.post(
        "/api/v1/modules/import?filename=sample.xlsx&created_by=codex",
        content=b"sample-bytes",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["result"] == "success"
    assert response.json()["message"] == "ワークブック取込結果を正規化しました。"
    assert response.json()["data"]["module_name"] == "Workbook module"


def test_import_module_workbook_rejects_business_validation_error(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workbook import API should return 400 for parser validation errors."""

    def fake_build_module_create_request_from_workbook_bytes(**kwargs: object) -> object:
        del kwargs
        raise ValueError("filename must end with .xlsx or .xlsm.")

    monkeypatch.setattr(
        modules,
        "build_module_create_request_from_workbook_bytes",
        fake_build_module_create_request_from_workbook_bytes,
    )

    response = client.post(
        "/api/v1/modules/import?filename=sample.txt",
        content=b"sample-bytes",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "result": "error",
        "data": None,
        "message": "filename must end with .xlsx or .xlsm.",
    }
