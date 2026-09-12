"""Authentication models and authorization rules."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AuthRole = Literal["member", "approver", "admin"]
ROLE_RANK: dict[AuthRole, int] = {
    "member": 10,
    "approver": 20,
    "admin": 30,
}


class AuthLoginRequest(BaseModel):
    """Credentials accepted by the login endpoint."""

    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=512)


class AuthUserData(BaseModel):
    """Authenticated user information safe to return to the browser."""

    user_id: int
    username: str
    display_name: str
    role: AuthRole
    password_change_required: bool = False


class AuthBootstrapUser(BaseModel):
    """Lab-only user definition used to initialize an empty user table."""

    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=512)
    display_name: str = Field(min_length=1, max_length=200)
    role: AuthRole


class AuthManagedUserData(BaseModel):
    """User account information exposed to administrators."""

    user_id: int
    username: str
    display_name: str
    role: AuthRole
    is_active: bool
    password_change_required: bool
    last_login_at: datetime | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    delete_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class AuthManagedUserListData(BaseModel):
    """Administrator-facing user account list."""

    items: list[AuthManagedUserData]


class AuthSelfRegistrationRequest(BaseModel):
    """Credentials and profile for a new application user."""

    username: str = Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )
    display_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=512)


class AuthUserCreateRequest(AuthSelfRegistrationRequest):
    """Administrator request for creating a user with a selected role."""

    role: AuthRole


class AuthUserRoleUpdateRequest(BaseModel):
    """Request for changing one user's application role."""

    role: AuthRole


class AuthUserActiveUpdateRequest(BaseModel):
    """Request for enabling or disabling one user account."""

    is_active: bool


class AuthUserDeleteRequest(BaseModel):
    """Administrator request for logically deleting one user."""

    reason: str = Field(min_length=1, max_length=500)


class AuthPasswordChangeRequest(BaseModel):
    """Request for replacing the current user's password."""

    current_password: str = Field(min_length=1, max_length=512)
    new_password: str = Field(min_length=8, max_length=512)


class AuthUserPasswordResetRequest(BaseModel):
    """Administrator request for setting a temporary password."""

    temporary_password: str = Field(min_length=8, max_length=512)


class InvalidCredentialsError(Exception):
    """Raised when a username and password pair is invalid."""


class AccountLockedError(Exception):
    """Raised while a user account is temporarily locked."""


class DuplicateUsernameError(Exception):
    """Raised when a case-insensitive username already exists."""


class ManagedUserNotFoundError(Exception):
    """Raised when an administrator targets an unknown user."""


class ManagedUserConflictError(Exception):
    """Raised when an account change would make administration unsafe."""


class CurrentPasswordMismatchError(Exception):
    """Raised when a password change request has the wrong current password."""


class PasswordReuseError(Exception):
    """Raised when the new password matches the current password."""


def role_allows(user_role: AuthRole, minimum_role: AuthRole) -> bool:
    """Return whether ``user_role`` includes ``minimum_role`` permissions."""

    return ROLE_RANK[user_role] >= ROLE_RANK[minimum_role]


def approval_transition_minimum_role(to_status: str) -> AuthRole:
    """Return the minimum role required for an approval transition."""

    if to_status in {"published", "returned", "archived"}:
        return "approver"
    return "member"
