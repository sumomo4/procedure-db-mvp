"""FastAPI dependencies for session authentication and role authorization."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import AuthRole, AuthUserData, approval_transition_minimum_role, role_allows
from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.db.auth import get_auth_session_user
from app.routers.health import get_app_settings


def validate_request_origin(request: Request, settings: AppSettings) -> None:
    """Reject browser state changes from an untrusted origin."""

    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    origin = request.headers.get("origin")
    if not origin:
        return

    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host")
    allowed_origins = set(settings.cors_allow_origins)
    if host:
        allowed_origins.add(f"{forwarded_proto}://{host}")
    if origin.rstrip("/") not in {item.rstrip("/") for item in allowed_origins}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="許可されていない送信元からの操作です。",
        )


def get_current_user(
    request: Request,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> AuthUserData:
    """Resolve the current user from the server-side session."""

    validate_request_origin(request, settings)
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインが必要です。",
        )
    try:
        user = get_auth_session_user(settings, token)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ログインセッションが無効または期限切れです。",
        )
    request.state.auth_user = user
    return user


CurrentUser = Annotated[AuthUserData, Depends(get_current_user)]


def require_password_change_completed(current_user: CurrentUser) -> AuthUserData:
    """Block business APIs until a temporary password has been replaced."""

    if current_user.password_change_required:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="初回ログインのパスワード変更を完了してください。",
        )
    return current_user


def require_minimum_role(minimum_role: AuthRole) -> Callable[..., AuthUserData]:
    """Build a dependency that enforces the hierarchical application role."""

    def dependency(current_user: CurrentUser) -> AuthUserData:
        require_password_change_completed(current_user)
        if not role_allows(current_user.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="この操作を実行する権限がありません。",
            )
        return current_user

    return dependency


AdminUser = Annotated[AuthUserData, Depends(require_minimum_role("admin"))]


def require_approval_transition(current_user: AuthUserData, to_status: str) -> None:
    """Enforce member/approver responsibilities for a status transition."""

    minimum_role = approval_transition_minimum_role(to_status)
    if not role_allows(current_user.role, minimum_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="この承認操作を実行する権限がありません。",
        )
