"""Authentication and authorization API tests."""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi import status
from fastapi.testclient import TestClient

from app.core.auth import (
    AuthManagedUserData,
    AuthUserData,
    DuplicateUsernameError,
    ManagedUserConflictError,
    role_allows,
)
from app.core.security import require_approval_transition
from app.main import create_app
from app.routers.health import get_app_settings


def _client_without_auth_override(test_settings):
    application = create_app()
    application.dependency_overrides[get_app_settings] = lambda: test_settings
    return application, TestClient(application)


def _managed_user(
    *,
    user_id: int = 8,
    username: str = "managed-user@example.co.jp",
    display_name: str = "管理対象ユーザー",
    role: str = "member",
    is_active: bool = True,
    password_change_required: bool = False,
) -> AuthManagedUserData:
    now = datetime(2026, 9, 11, 3, 0, tzinfo=timezone.utc)
    return AuthManagedUserData(
        user_id=user_id,
        username=username,
        display_name=display_name,
        role=role,
        is_active=is_active,
        password_change_required=password_change_required,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


def test_health_remains_public(test_settings) -> None:
    application, client = _client_without_auth_override(test_settings)
    try:
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
    finally:
        client.close()
        application.dependency_overrides.clear()


def test_business_api_requires_login(test_settings, monkeypatch) -> None:
    monkeypatch.setattr("app.core.security.get_auth_session_user", lambda settings, token: None)
    application, client = _client_without_auth_override(test_settings)
    try:
        response = client.get("/api/v1/modules")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["message"] == "ログインが必要です。"
    finally:
        client.close()
        application.dependency_overrides.clear()


def test_login_sets_httponly_cookie(test_settings, monkeypatch) -> None:
    authenticated_user = AuthUserData(
        user_id=8,
        username="member",
        display_name="メンバーユーザー",
        role="member",
    )
    monkeypatch.setattr(
        "app.routers.auth.authenticate_user",
        lambda settings, username, password: authenticated_user,
    )
    monkeypatch.setattr(
        "app.routers.auth.create_auth_session",
        lambda settings, user_id: "raw-session-token",
    )
    application, client = _client_without_auth_override(test_settings)
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "member", "password": "password"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["username"] == "member"
        cookie = response.headers["set-cookie"]
        assert f"{test_settings.auth_cookie_name}=raw-session-token" in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert response.headers["cache-control"] == "no-store"
    finally:
        client.close()
        application.dependency_overrides.clear()


def test_member_cannot_open_admin_placeholder_settings(test_settings, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.core.security.get_auth_session_user",
        lambda settings, token: AuthUserData(
            user_id=9,
            username="member",
            display_name="メンバーユーザー",
            role="member",
        ),
    )
    application, client = _client_without_auth_override(test_settings)
    try:
        client.cookies.set(test_settings.auth_cookie_name, "active-token")
        response = client.get("/api/v1/case-docs/placeholders")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        client.close()
        application.dependency_overrides.clear()


def test_untrusted_origin_is_rejected_before_login(test_settings) -> None:
    application, client = _client_without_auth_override(test_settings)
    try:
        response = client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://attacker.example"},
            json={"username": "member", "password": "password"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        client.close()
        application.dependency_overrides.clear()


def test_role_hierarchy_is_inclusive() -> None:
    assert role_allows("admin", "approver") is True
    assert role_allows("admin", "member") is True
    assert role_allows("approver", "member") is True
    assert role_allows("member", "approver") is False


def test_member_cannot_approve_but_approver_can() -> None:
    member = AuthUserData(user_id=1, username="member", display_name="Member", role="member")
    approver = AuthUserData(user_id=2, username="approver", display_name="Approver", role="approver")

    with pytest.raises(HTTPException) as exception_info:
        require_approval_transition(member, "published")
    assert exception_info.value.status_code == status.HTTP_403_FORBIDDEN

    require_approval_transition(approver, "published")


def test_admin_can_list_managed_users(client, monkeypatch) -> None:
    monkeypatch.setattr("app.routers.auth.list_managed_users", lambda settings: [_managed_user()])

    response = client.get("/api/v1/auth/users")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["items"][0]["username"] == "managed-user@example.co.jp"
    assert "password_hash" not in response.json()["data"]["items"][0]


def test_member_cannot_manage_users(test_settings, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.core.security.get_auth_session_user",
        lambda settings, token: AuthUserData(
            user_id=9,
            username="member",
            display_name="メンバーユーザー",
            role="member",
        ),
    )
    application, client = _client_without_auth_override(test_settings)
    try:
        client.cookies.set(test_settings.auth_cookie_name, "active-token")
        response = client.get("/api/v1/auth/users")
        assert response.status_code == status.HTTP_403_FORBIDDEN
    finally:
        client.close()
        application.dependency_overrides.clear()


def test_admin_can_create_managed_user(client, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_create(settings, **values):
        captured.update(values)
        return _managed_user(
            username=str(values["username"]),
            role=str(values["role"]),
            password_change_required=True,
        )

    monkeypatch.setattr("app.routers.auth.create_managed_user", fake_create)

    response = client.post(
        "/api/v1/auth/users",
        json={
            "username": "new-member@example.co.jp",
            "display_name": "新規メンバー",
            "password": "initial-password",
            "role": "member",
        },
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["data"]["username"] == "new-member@example.co.jp"
    assert response.json()["data"]["password_change_required"] is True
    assert captured["password"] == "initial-password"
    assert "password" not in response.json()["data"]


def test_duplicate_managed_username_returns_conflict(client, monkeypatch) -> None:
    def fake_create(settings, **values):
        del settings, values
        raise DuplicateUsernameError()

    monkeypatch.setattr("app.routers.auth.create_managed_user", fake_create)

    response = client.post(
        "/api/v1/auth/users",
        json={
            "username": "member@example.co.jp",
            "display_name": "重複ユーザー",
            "password": "initial-password",
            "role": "member",
        },
    )

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "すでに登録" in response.json()["message"]


def test_managed_user_creation_requires_email_address(client, monkeypatch) -> None:
    create_user_called = False

    def fake_create(settings, **values):
        nonlocal create_user_called
        create_user_called = True
        return _managed_user()

    monkeypatch.setattr("app.routers.auth.create_managed_user", fake_create)

    response = client.post(
        "/api/v1/auth/users",
        json={
            "username": "not-an-email",
            "display_name": "形式不正ユーザー",
            "password": "initial-password",
            "role": "member",
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert create_user_called is False


def test_admin_can_change_managed_user_role(client, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_update(settings, **values):
        captured.update(values)
        return _managed_user(user_id=int(values["user_id"]), role=str(values["role"]))

    monkeypatch.setattr("app.routers.auth.update_managed_user_role", fake_update)

    response = client.patch("/api/v1/auth/users/8/role", json={"role": "approver"})

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["role"] == "approver"
    assert captured["acting_user_id"] == 1


def test_admin_cannot_disable_self(client, monkeypatch) -> None:
    def fake_update(settings, **values):
        del settings, values
        raise ManagedUserConflictError("自分自身のアカウントは無効化できません。")

    monkeypatch.setattr("app.routers.auth.update_managed_user_active_state", fake_update)

    response = client.patch("/api/v1/auth/users/1/active", json={"is_active": False})

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json()["message"] == "自分自身のアカウントは無効化できません。"


def test_password_change_required_user_can_only_use_auth_api(test_settings, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.core.security.get_auth_session_user",
        lambda settings, token: AuthUserData(
            user_id=10,
            username="first-login",
            display_name="初回ログインユーザー",
            role="member",
            password_change_required=True,
        ),
    )
    application, client = _client_without_auth_override(test_settings)
    try:
        client.cookies.set(test_settings.auth_cookie_name, "temporary-session")

        me_response = client.get("/api/v1/auth/me")
        modules_response = client.get("/api/v1/modules")

        assert me_response.status_code == status.HTTP_200_OK
        assert me_response.json()["data"]["password_change_required"] is True
        assert modules_response.status_code == status.HTTP_403_FORBIDDEN
        assert "パスワード変更" in modules_response.json()["message"]
    finally:
        client.close()
        application.dependency_overrides.clear()


def test_user_can_replace_temporary_password(client, monkeypatch) -> None:
    updated_user = AuthUserData(
        user_id=1,
        username="pytest-admin",
        display_name="pytest authenticated user",
        role="admin",
        password_change_required=False,
    )
    captured: dict[str, object] = {}

    def fake_change(settings, **values):
        captured.update(values)
        return updated_user

    monkeypatch.setattr("app.routers.auth.change_user_password", fake_change)
    monkeypatch.setattr("app.routers.auth.create_auth_session", lambda settings, user_id: "fresh-token")

    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "temporary-password", "new_password": "new-secure-password"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["password_change_required"] is False
    assert captured["current_password"] == "temporary-password"
    assert captured["new_password"] == "new-secure-password"
    assert "fresh-token" in response.headers["set-cookie"]


def test_admin_can_reset_another_users_password(client, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_reset(settings, **values):
        captured.update(values)
        return _managed_user(
            user_id=int(values["user_id"]),
            password_change_required=True,
        )

    monkeypatch.setattr("app.routers.auth.reset_managed_user_password", fake_reset)

    response = client.patch(
        "/api/v1/auth/users/8/password",
        json={"temporary_password": "replacement-password"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["data"]["password_change_required"] is True
    assert captured["temporary_password"] == "replacement-password"
    assert captured["acting_user_id"] == 1
