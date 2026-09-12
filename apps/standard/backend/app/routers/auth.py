"""Login, current-user, and logout routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth import (
    AccountLockedError,
    AuthLoginRequest,
    AuthManagedUserData,
    AuthManagedUserListData,
    AuthPasswordChangeRequest,
    AuthSelfRegistrationRequest,
    AuthUserActiveUpdateRequest,
    AuthUserCreateRequest,
    AuthUserData,
    AuthUserDeleteRequest,
    AuthUserPasswordResetRequest,
    AuthUserRoleUpdateRequest,
    CurrentPasswordMismatchError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    ManagedUserConflictError,
    ManagedUserNotFoundError,
    PasswordReuseError,
)
from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import ApiResponse, success_response
from app.core.security import AdminUser, CurrentUser, validate_request_origin
from app.db.auth import (
    authenticate_user,
    change_user_password,
    create_auth_session,
    create_managed_user,
    delete_managed_user,
    list_managed_users,
    revoke_auth_session,
    reset_managed_user_password,
    restore_managed_user,
    update_managed_user_active_state,
    update_managed_user_role,
)
from app.routers.health import get_app_settings


router = APIRouter(prefix="/auth", tags=["auth"])


def _uses_secure_cookie(request: Request, settings: AppSettings) -> bool:
    """Use Secure cookies for HTTPS, including traffic forwarded by Nginx."""

    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    return settings.auth_cookie_secure or forwarded_proto.lower() == "https"


def _set_auth_cookie(
    response: Response,
    request: Request,
    settings: AppSettings,
    token: str,
) -> None:
    """Set the shared authentication cookie attributes."""

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        secure=_uses_secure_cookie(request, settings),
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=ApiResponse[AuthUserData])
def login(
    payload: AuthLoginRequest,
    request: Request,
    response: Response,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthUserData]:
    """Authenticate credentials and issue an HttpOnly session cookie."""

    validate_request_origin(request, settings)
    try:
        user = authenticate_user(settings, payload.username, payload.password)
        token = create_auth_session(settings, user.user_id)
    except InvalidCredentialsError as exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません。",
        ) from exception
    except AccountLockedError as exception:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="ログインに複数回失敗したため一時的にロックされています。",
        ) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception

    _set_auth_cookie(response, request, settings, token)
    response.headers["Cache-Control"] = "no-store"
    return success_response(user, "ログインしました。")


@router.post("/register", response_model=ApiResponse[AuthUserData], status_code=status.HTTP_201_CREATED)
def register(
    payload: AuthSelfRegistrationRequest,
    request: Request,
    response: Response,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthUserData]:
    """Allow a new user to create and sign in to a member account."""

    validate_request_origin(request, settings)
    try:
        registered = create_managed_user(
            settings,
            username=payload.username,
            display_name=payload.display_name,
            password=payload.password,
            role="member",
            require_password_change=False,
        )
        token = create_auth_session(settings, registered.user_id)
    except DuplicateUsernameError as exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同じメールアドレスがすでに登録されています。",
        ) from exception
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exception)) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception

    _set_auth_cookie(response, request, settings, token)
    response.headers["Cache-Control"] = "no-store"
    return success_response(
        AuthUserData(
            user_id=registered.user_id,
            username=registered.username,
            display_name=registered.display_name,
            role=registered.role,
            password_change_required=registered.password_change_required,
        ),
        "ユーザー登録が完了しました。",
    )


@router.get("/me", response_model=ApiResponse[AuthUserData])
def read_current_user(current_user: CurrentUser) -> ApiResponse[AuthUserData]:
    """Return the user represented by the active session."""

    return success_response(current_user, "ログインユーザーを取得しました。")


@router.post("/change-password", response_model=ApiResponse[AuthUserData])
def change_password(
    payload: AuthPasswordChangeRequest,
    request: Request,
    response: Response,
    current_user: CurrentUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthUserData]:
    """Replace the current password and issue a fresh session."""

    try:
        user = change_user_password(
            settings,
            user_id=current_user.user_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
        token = create_auth_session(settings, user.user_id)
    except CurrentPasswordMismatchError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません。",
        ) from exception
    except PasswordReuseError as exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在とは異なる新しいパスワードを設定してください。",
        ) from exception
    except ManagedUserNotFoundError as exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが無効または削除されています。",
        ) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception

    _set_auth_cookie(response, request, settings, token)
    response.headers["Cache-Control"] = "no-store"
    return success_response(user, "パスワードを変更しました。")


@router.post("/logout", response_model=ApiResponse[None])
def logout(
    request: Request,
    response: Response,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[None]:
    """Revoke the current session and always clear the browser cookie."""

    validate_request_origin(request, settings)
    token = request.cookies.get(settings.auth_cookie_name)
    if token:
        try:
            revoke_auth_session(settings, token)
        except DatabaseConnectionError as exception:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exception),
            ) from exception
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=_uses_secure_cookie(request, settings),
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return success_response(None, "ログアウトしました。")


@router.get("/users", response_model=ApiResponse[AuthManagedUserListData])
def read_managed_users(
    admin_user: AdminUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthManagedUserListData]:
    """Return all users to an administrator."""

    del admin_user
    try:
        items = list_managed_users(settings)
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    return success_response(AuthManagedUserListData(items=items), "ユーザー一覧を取得しました。")


@router.post("/users", response_model=ApiResponse[AuthManagedUserData], status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AuthUserCreateRequest,
    admin_user: AdminUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthManagedUserData]:
    """Create one user account as an administrator."""

    del admin_user
    try:
        user = create_managed_user(
            settings,
            username=payload.username,
            display_name=payload.display_name,
            password=payload.password,
            role=payload.role,
        )
    except DuplicateUsernameError as exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同じメールアドレスがすでに登録されています。",
        ) from exception
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exception)) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    return success_response(user, "ユーザーを追加しました。初回ログイン時にパスワード変更が必要です。")


@router.patch("/users/{user_id}/role", response_model=ApiResponse[AuthManagedUserData])
def update_user_role(
    user_id: int,
    payload: AuthUserRoleUpdateRequest,
    admin_user: AdminUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthManagedUserData]:
    """Change one user's role as an administrator."""

    try:
        user = update_managed_user_role(
            settings,
            user_id=user_id,
            role=payload.role,
            acting_user_id=admin_user.user_id,
        )
    except ManagedUserNotFoundError as exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません。") from exception
    except ManagedUserConflictError as exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception)) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    return success_response(user, "ロールを変更しました。対象ユーザーの既存セッションは失効しました。")


@router.patch("/users/{user_id}/active", response_model=ApiResponse[AuthManagedUserData])
def update_user_active_state(
    user_id: int,
    payload: AuthUserActiveUpdateRequest,
    admin_user: AdminUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthManagedUserData]:
    """Enable or disable one user account as an administrator."""

    try:
        user = update_managed_user_active_state(
            settings,
            user_id=user_id,
            is_active=payload.is_active,
            acting_user_id=admin_user.user_id,
        )
    except ManagedUserNotFoundError as exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません。") from exception
    except ManagedUserConflictError as exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception)) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    message = "ユーザーを有効化しました。" if user.is_active else "ユーザーを無効化しました。"
    return success_response(user, message)


@router.delete("/users/{user_id}", response_model=ApiResponse[AuthManagedUserData])
def delete_user(
    user_id: int,
    payload: AuthUserDeleteRequest,
    admin_user: AdminUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthManagedUserData]:
    """Logically delete one user as an administrator."""

    try:
        user = delete_managed_user(
            settings,
            user_id=user_id,
            reason=payload.reason,
            acting_user_id=admin_user.user_id,
            deleted_by=admin_user.display_name,
        )
    except ManagedUserNotFoundError as exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません。") from exception
    except ManagedUserConflictError as exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception)) from exception
    except ValueError as exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exception)) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    return success_response(user, "ユーザーを削除しました。対象ユーザーの既存セッションは失効しました。")


@router.post("/users/{user_id}/restore", response_model=ApiResponse[AuthManagedUserData])
def restore_user(
    user_id: int,
    admin_user: AdminUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthManagedUserData]:
    """Restore one logically deleted user as an administrator."""

    del admin_user
    try:
        user = restore_managed_user(settings, user_id=user_id)
    except ManagedUserNotFoundError as exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません。") from exception
    except ManagedUserConflictError as exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception)) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    return success_response(user, "ユーザーを無効状態で復元しました。内容を確認して再有効化してください。")


@router.patch("/users/{user_id}/password", response_model=ApiResponse[AuthManagedUserData])
def reset_user_password(
    user_id: int,
    payload: AuthUserPasswordResetRequest,
    admin_user: AdminUser,
    settings: Annotated[AppSettings, Depends(get_app_settings)],
) -> ApiResponse[AuthManagedUserData]:
    """Set a temporary password for another user."""

    try:
        user = reset_managed_user_password(
            settings,
            user_id=user_id,
            temporary_password=payload.temporary_password,
            acting_user_id=admin_user.user_id,
        )
    except ManagedUserNotFoundError as exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません。") from exception
    except ManagedUserConflictError as exception:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exception)) from exception
    except DatabaseConnectionError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception
    return success_response(
        user,
        "仮パスワードを設定しました。対象ユーザーの既存セッションは失効しました。",
    )
