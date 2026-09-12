"""PostgreSQL persistence for users and server-side sessions."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import secrets
from threading import Lock
from typing import Any

from pydantic import TypeAdapter, ValidationError

from app.core.auth import (
    AccountLockedError,
    AuthBootstrapUser,
    AuthManagedUserData,
    AuthRole,
    AuthUserData,
    CurrentPasswordMismatchError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    ManagedUserConflictError,
    ManagedUserNotFoundError,
    PasswordReuseError,
)
from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError


_AUTH_SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS proc;

CREATE TABLE IF NOT EXISTS proc.app_users (
    user_id bigserial PRIMARY KEY,
    username text NOT NULL,
    display_name text NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('member', 'approver', 'admin')),
    is_active boolean NOT NULL DEFAULT true,
    must_change_password boolean NOT NULL DEFAULT false,
    failed_login_count integer NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until timestamptz,
    last_login_at timestamptz,
    deleted_at timestamptz,
    deleted_by text,
    delete_reason text,
    password_changed_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE proc.app_users
    ADD COLUMN IF NOT EXISTS must_change_password boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS deleted_at timestamptz,
    ADD COLUMN IF NOT EXISTS deleted_by text,
    ADD COLUMN IF NOT EXISTS delete_reason text;

CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_username_lower
    ON proc.app_users (lower(username));

CREATE INDEX IF NOT EXISTS idx_app_users_deleted_at
    ON proc.app_users (deleted_at);

CREATE TABLE IF NOT EXISTS proc.auth_sessions (
    auth_session_id bigserial PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES proc.app_users (user_id) ON DELETE CASCADE,
    token_hash varchar(64) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id
    ON proc.auth_sessions (user_id);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at
    ON proc.auth_sessions (expires_at);
"""

# This valid Argon2id hash is used only to equalize verification work for unknown users.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$wagCPXjifgvUFBzq4hqe3w$"
    "CYaIb8sB+wtD+Vu/P4uod1+Qof8h+1g7bbDlBID48Rc"
)
_initialized_database_urls: set[str] = set()
_initialization_lock = Lock()


def _managed_user_from_row(row: tuple[Any, ...]) -> AuthManagedUserData:
    """Convert an administrator user query row to an API model."""

    return AuthManagedUserData(
        user_id=row[0],
        username=row[1],
        display_name=row[2],
        role=row[3],
        is_active=bool(row[4]),
        password_change_required=bool(row[5]),
        last_login_at=row[6],
        deleted_at=row[7],
        deleted_by=row[8],
        delete_reason=row[9],
        created_at=row[10],
        updated_at=row[11],
    )


_MANAGED_USER_COLUMNS = """
    user_id,
    username,
    display_name,
    role,
    is_active,
    must_change_password,
    last_login_at,
    deleted_at,
    deleted_by,
    delete_reason,
    created_at,
    updated_at
"""


def _password_hasher() -> Any:
    """Create the password hasher without importing optional code at module load."""

    try:
        from pwdlib import PasswordHash
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("Password hashing dependency is not installed.") from exception
    return PasswordHash.recommended()


def _parse_bootstrap_users(raw_json: str) -> list[AuthBootstrapUser]:
    """Parse optional Lab bootstrap users from configuration."""

    if not raw_json.strip():
        return []
    try:
        payload = json.loads(raw_json)
        return TypeAdapter(list[AuthBootstrapUser]).validate_python(payload)
    except (json.JSONDecodeError, ValidationError) as exception:
        raise DatabaseConnectionError("AUTH_BOOTSTRAP_USERS_JSON is invalid.") from exception


def ensure_auth_storage(settings: AppSettings) -> None:
    """Create auth tables for both new and already-existing database volumes."""

    if settings.database_url in _initialized_database_urls:
        return

    with _initialization_lock:
        if settings.database_url in _initialized_database_urls:
            return
        try:
            import psycopg
        except ModuleNotFoundError as exception:
            raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

        try:
            with psycopg.connect(
                settings.database_url,
                connect_timeout=settings.db_connect_timeout_seconds,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_AUTH_SCHEMA_SQL)
                    bootstrap_users = _parse_bootstrap_users(settings.auth_bootstrap_users_json)
                    if bootstrap_users:
                        cursor.execute("SELECT EXISTS (SELECT 1 FROM proc.app_users)")
                        has_users = bool(cursor.fetchone()[0])
                        if not has_users:
                            password_hasher = _password_hasher()
                            for user in bootstrap_users:
                                cursor.execute(
                                    """
                                    INSERT INTO proc.app_users (
                                        username,
                                        display_name,
                                        password_hash,
                                        role
                                    ) VALUES (
                                        %(username)s,
                                        %(display_name)s,
                                        %(password_hash)s,
                                        %(role)s
                                    )
                                    ON CONFLICT DO NOTHING
                                    """,
                                    {
                                        "username": user.username.strip(),
                                        "display_name": user.display_name.strip(),
                                        "password_hash": password_hasher.hash(user.password),
                                        "role": user.role,
                                    },
                                )
            _initialized_database_urls.add(settings.database_url)
        except DatabaseConnectionError:
            raise
        except Exception as exception:
            raise DatabaseConnectionError("Authentication storage initialization failed.") from exception


def authenticate_user(settings: AppSettings, username: str, password: str) -> AuthUserData:
    """Verify credentials and update lockout metadata."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    normalized_username = username.strip().lower()
    password_hasher = _password_hasher()
    authentication_error: Exception | None = None
    authenticated_user: AuthUserData | None = None

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        user_id,
                        username,
                        display_name,
                        password_hash,
                        role,
                        is_active,
                        failed_login_count,
                        locked_until,
                        must_change_password
                    FROM proc.app_users
                    WHERE lower(username) = lower(%(username)s)
                      AND deleted_at IS NULL
                    FOR UPDATE
                    """,
                    {"username": normalized_username},
                )
                row = cursor.fetchone()
                stored_hash = row[3] if row is not None else _DUMMY_PASSWORD_HASH
                password_matches = password_hasher.verify(password, stored_hash)

                if row is None or not bool(row[5]) or not password_matches:
                    if row is not None:
                        failed_count = int(row[6]) + 1
                        lock_account = failed_count >= settings.auth_login_max_failures
                        cursor.execute(
                            """
                            UPDATE proc.app_users
                            SET
                                failed_login_count = %(failed_count)s,
                                locked_until = CASE
                                    WHEN %(lock_account)s
                                    THEN now() + make_interval(secs => %(lock_seconds)s)
                                    ELSE locked_until
                                END,
                                updated_at = now()
                            WHERE user_id = %(user_id)s
                            """,
                            {
                                "failed_count": failed_count,
                                "lock_account": lock_account,
                                "lock_seconds": settings.auth_login_lock_seconds,
                                "user_id": row[0],
                            },
                        )
                    authentication_error = InvalidCredentialsError()
                elif row[7] is not None and row[7] > datetime.now(timezone.utc):
                    authentication_error = AccountLockedError()
                else:
                    cursor.execute(
                        """
                        UPDATE proc.app_users
                        SET
                            failed_login_count = 0,
                            locked_until = NULL,
                            last_login_at = now(),
                            updated_at = now()
                        WHERE user_id = %(user_id)s
                        """,
                        {"user_id": row[0]},
                    )
                    authenticated_user = AuthUserData(
                        user_id=row[0],
                        username=row[1],
                        display_name=row[2],
                        role=row[4],
                        password_change_required=bool(row[8]),
                    )
    except Exception as exception:
        if isinstance(exception, (InvalidCredentialsError, AccountLockedError)):
            raise
        raise DatabaseConnectionError("User authentication query failed.") from exception

    if authentication_error is not None:
        raise authentication_error
    if authenticated_user is None:
        raise InvalidCredentialsError()
    return authenticated_user


def create_auth_session(settings: AppSettings, user_id: int) -> str:
    """Persist a new session and return its raw browser token."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    token = secrets.token_urlsafe(48)
    token_hash = sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.auth_session_ttl_seconds)
    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM proc.auth_sessions WHERE expires_at <= now() OR revoked_at IS NOT NULL"
                )
                cursor.execute(
                    """
                    INSERT INTO proc.auth_sessions (user_id, token_hash, expires_at)
                    VALUES (%(user_id)s, %(token_hash)s, %(expires_at)s)
                    """,
                    {
                        "user_id": user_id,
                        "token_hash": token_hash,
                        "expires_at": expires_at,
                    },
                )
    except Exception as exception:
        raise DatabaseConnectionError("Authentication session creation failed.") from exception
    return token


def get_auth_session_user(settings: AppSettings, token: str) -> AuthUserData | None:
    """Return the active user for a raw session token."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    token_hash = sha256(token.encode("utf-8")).hexdigest()
    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        u.user_id,
                        u.username,
                        u.display_name,
                        u.role,
                        u.must_change_password
                    FROM proc.auth_sessions s
                    JOIN proc.app_users u ON u.user_id = s.user_id
                    WHERE s.token_hash = %(token_hash)s
                      AND s.revoked_at IS NULL
                      AND s.expires_at > now()
                      AND u.is_active = true
                      AND u.deleted_at IS NULL
                    """,
                    {"token_hash": token_hash},
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute(
                    """
                    UPDATE proc.auth_sessions
                    SET last_seen_at = now()
                    WHERE token_hash = %(token_hash)s
                    """,
                    {"token_hash": token_hash},
                )
    except Exception as exception:
        raise DatabaseConnectionError("Authentication session query failed.") from exception

    return AuthUserData(
        user_id=row[0],
        username=row[1],
        display_name=row[2],
        role=row[3],
        password_change_required=bool(row[4]),
    )


def revoke_auth_session(settings: AppSettings, token: str) -> None:
    """Revoke a raw session token if it exists."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    token_hash = sha256(token.encode("utf-8")).hexdigest()
    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE proc.auth_sessions
                    SET revoked_at = now()
                    WHERE token_hash = %(token_hash)s
                      AND revoked_at IS NULL
                    """,
                    {"token_hash": token_hash},
                )
    except Exception as exception:
        raise DatabaseConnectionError("Authentication session revocation failed.") from exception


def list_managed_users(settings: AppSettings) -> list[AuthManagedUserData]:
    """Return all application users for the administrator screen."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {_MANAGED_USER_COLUMNS}
                    FROM proc.app_users
                    ORDER BY deleted_at NULLS FIRST, is_active DESC, lower(username), user_id
                    """
                )
                return [_managed_user_from_row(row) for row in cursor.fetchall()]
    except Exception as exception:
        raise DatabaseConnectionError("User management list query failed.") from exception


def create_managed_user(
    settings: AppSettings,
    *,
    username: str,
    display_name: str,
    password: str,
    role: AuthRole,
    require_password_change: bool = True,
) -> AuthManagedUserData:
    """Create one application user with an Argon2id password hash."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    normalized_username = username.strip().lower()
    normalized_display_name = display_name.strip()
    if not normalized_username or not normalized_display_name:
        raise ValueError("メールアドレスと表示名は空白だけにできません。")

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    INSERT INTO proc.app_users (
                        username,
                        display_name,
                        password_hash,
                        role,
                        must_change_password
                    ) VALUES (
                        %(username)s,
                        %(display_name)s,
                        %(password_hash)s,
                        %(role)s,
                        %(require_password_change)s
                    )
                    RETURNING {_MANAGED_USER_COLUMNS}
                    """,
                    {
                        "username": normalized_username,
                        "display_name": normalized_display_name,
                        "password_hash": _password_hasher().hash(password),
                        "role": role,
                        "require_password_change": require_password_change,
                    },
                )
                return _managed_user_from_row(cursor.fetchone())
    except Exception as exception:
        if getattr(exception, "sqlstate", None) == "23505":
            raise DuplicateUsernameError() from exception
        raise DatabaseConnectionError("User account creation failed.") from exception


def update_managed_user_role(
    settings: AppSettings,
    *,
    user_id: int,
    role: AuthRole,
    acting_user_id: int,
) -> AuthManagedUserData:
    """Change a user's role and revoke that user's active sessions."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT role
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                      AND deleted_at IS NULL
                    FOR UPDATE
                    """,
                    {"user_id": user_id},
                )
                row = cursor.fetchone()
                if row is None:
                    raise ManagedUserNotFoundError()

                current_role = row[0]
                if user_id == acting_user_id and role != current_role:
                    raise ManagedUserConflictError("自分自身のロールは変更できません。")

                if role != current_role:
                    cursor.execute(
                        """
                        UPDATE proc.app_users
                        SET role = %(role)s, updated_at = now()
                        WHERE user_id = %(user_id)s
                        """,
                        {"role": role, "user_id": user_id},
                    )
                    cursor.execute(
                        """
                        UPDATE proc.auth_sessions
                        SET revoked_at = now()
                        WHERE user_id = %(user_id)s AND revoked_at IS NULL
                        """,
                        {"user_id": user_id},
                    )

                cursor.execute(
                    f"""
                    SELECT {_MANAGED_USER_COLUMNS}
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                    """,
                    {"user_id": user_id},
                )
                return _managed_user_from_row(cursor.fetchone())
    except (ManagedUserNotFoundError, ManagedUserConflictError):
        raise
    except Exception as exception:
        raise DatabaseConnectionError("User role update failed.") from exception


def update_managed_user_active_state(
    settings: AppSettings,
    *,
    user_id: int,
    is_active: bool,
    acting_user_id: int,
) -> AuthManagedUserData:
    """Enable or disable a user and revoke sessions when its state changes."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT is_active
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                      AND deleted_at IS NULL
                    FOR UPDATE
                    """,
                    {"user_id": user_id},
                )
                row = cursor.fetchone()
                if row is None:
                    raise ManagedUserNotFoundError()

                current_is_active = bool(row[0])
                if user_id == acting_user_id and not is_active:
                    raise ManagedUserConflictError("自分自身のアカウントは無効化できません。")

                if is_active != current_is_active:
                    cursor.execute(
                        """
                        UPDATE proc.app_users
                        SET
                            is_active = %(is_active)s,
                            failed_login_count = 0,
                            locked_until = NULL,
                            updated_at = now()
                        WHERE user_id = %(user_id)s
                        """,
                        {"is_active": is_active, "user_id": user_id},
                    )
                    cursor.execute(
                        """
                        UPDATE proc.auth_sessions
                        SET revoked_at = now()
                        WHERE user_id = %(user_id)s AND revoked_at IS NULL
                        """,
                        {"user_id": user_id},
                    )

                cursor.execute(
                    f"""
                    SELECT {_MANAGED_USER_COLUMNS}
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                    """,
                    {"user_id": user_id},
                )
                return _managed_user_from_row(cursor.fetchone())
    except (ManagedUserNotFoundError, ManagedUserConflictError):
        raise
    except Exception as exception:
        raise DatabaseConnectionError("User active state update failed.") from exception


def delete_managed_user(
    settings: AppSettings,
    *,
    user_id: int,
    reason: str,
    acting_user_id: int,
    deleted_by: str,
) -> AuthManagedUserData:
    """Logically delete a user and revoke every active session."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ValueError("削除理由を入力してください。")
    if user_id == acting_user_id:
        raise ManagedUserConflictError("自分自身のアカウントは削除できません。")

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT role, is_active, deleted_at
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                    FOR UPDATE
                    """,
                    {"user_id": user_id},
                )
                row = cursor.fetchone()
                if row is None:
                    raise ManagedUserNotFoundError()
                if row[2] is not None:
                    raise ManagedUserConflictError("このユーザーはすでに削除されています。")

                if row[0] == "admin" and bool(row[1]):
                    cursor.execute(
                        """
                        SELECT count(*)
                        FROM proc.app_users
                        WHERE role = 'admin'
                          AND is_active = true
                          AND deleted_at IS NULL
                          AND user_id <> %(user_id)s
                        """,
                        {"user_id": user_id},
                    )
                    if int(cursor.fetchone()[0]) == 0:
                        raise ManagedUserConflictError("最後の有効な管理者は削除できません。")

                cursor.execute(
                    """
                    UPDATE proc.app_users
                    SET
                        is_active = false,
                        deleted_at = now(),
                        deleted_by = %(deleted_by)s,
                        delete_reason = %(reason)s,
                        failed_login_count = 0,
                        locked_until = NULL,
                        updated_at = now()
                    WHERE user_id = %(user_id)s
                    """,
                    {
                        "deleted_by": deleted_by.strip(),
                        "reason": normalized_reason,
                        "user_id": user_id,
                    },
                )
                cursor.execute(
                    """
                    UPDATE proc.auth_sessions
                    SET revoked_at = now()
                    WHERE user_id = %(user_id)s AND revoked_at IS NULL
                    """,
                    {"user_id": user_id},
                )
                cursor.execute(
                    f"""
                    SELECT {_MANAGED_USER_COLUMNS}
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                    """,
                    {"user_id": user_id},
                )
                return _managed_user_from_row(cursor.fetchone())
    except (ManagedUserConflictError, ManagedUserNotFoundError, ValueError):
        raise
    except Exception as exception:
        raise DatabaseConnectionError("User logical deletion failed.") from exception


def restore_managed_user(
    settings: AppSettings,
    *,
    user_id: int,
) -> AuthManagedUserData:
    """Restore a logically deleted user in the disabled state."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT deleted_at
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                    FOR UPDATE
                    """,
                    {"user_id": user_id},
                )
                row = cursor.fetchone()
                if row is None:
                    raise ManagedUserNotFoundError()
                if row[0] is None:
                    raise ManagedUserConflictError("このユーザーは削除されていません。")

                cursor.execute(
                    """
                    UPDATE proc.app_users
                    SET
                        is_active = false,
                        deleted_at = NULL,
                        deleted_by = NULL,
                        delete_reason = NULL,
                        failed_login_count = 0,
                        locked_until = NULL,
                        updated_at = now()
                    WHERE user_id = %(user_id)s
                    """,
                    {"user_id": user_id},
                )
                cursor.execute(
                    f"""
                    SELECT {_MANAGED_USER_COLUMNS}
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                    """,
                    {"user_id": user_id},
                )
                return _managed_user_from_row(cursor.fetchone())
    except (ManagedUserConflictError, ManagedUserNotFoundError):
        raise
    except Exception as exception:
        raise DatabaseConnectionError("User restoration failed.") from exception


def change_user_password(
    settings: AppSettings,
    *,
    user_id: int,
    current_password: str,
    new_password: str,
) -> AuthUserData:
    """Replace the current user's password and revoke all existing sessions."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    password_hasher = _password_hasher()
    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT username, display_name, role, password_hash, is_active
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                      AND deleted_at IS NULL
                    FOR UPDATE
                    """,
                    {"user_id": user_id},
                )
                row = cursor.fetchone()
                if row is None or not bool(row[4]):
                    raise ManagedUserNotFoundError()
                if not password_hasher.verify(current_password, row[3]):
                    raise CurrentPasswordMismatchError()
                if password_hasher.verify(new_password, row[3]):
                    raise PasswordReuseError()

                cursor.execute(
                    """
                    UPDATE proc.app_users
                    SET
                        password_hash = %(password_hash)s,
                        must_change_password = false,
                        failed_login_count = 0,
                        locked_until = NULL,
                        password_changed_at = now(),
                        updated_at = now()
                    WHERE user_id = %(user_id)s
                    """,
                    {
                        "password_hash": password_hasher.hash(new_password),
                        "user_id": user_id,
                    },
                )
                cursor.execute(
                    """
                    UPDATE proc.auth_sessions
                    SET revoked_at = now()
                    WHERE user_id = %(user_id)s AND revoked_at IS NULL
                    """,
                    {"user_id": user_id},
                )
                return AuthUserData(
                    user_id=user_id,
                    username=row[0],
                    display_name=row[1],
                    role=row[2],
                    password_change_required=False,
                )
    except (
        CurrentPasswordMismatchError,
        ManagedUserNotFoundError,
        PasswordReuseError,
    ):
        raise
    except Exception as exception:
        raise DatabaseConnectionError("Password change failed.") from exception


def reset_managed_user_password(
    settings: AppSettings,
    *,
    user_id: int,
    temporary_password: str,
    acting_user_id: int,
) -> AuthManagedUserData:
    """Set a temporary password and require the target to replace it."""

    ensure_auth_storage(settings)
    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    if user_id == acting_user_id:
        raise ManagedUserConflictError("自分自身のパスワードはパスワード変更画面から変更してください。")

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM proc.app_users
                        WHERE user_id = %(user_id)s
                          AND deleted_at IS NULL
                    )
                    """,
                    {"user_id": user_id},
                )
                if not bool(cursor.fetchone()[0]):
                    raise ManagedUserNotFoundError()

                cursor.execute(
                    """
                    UPDATE proc.app_users
                    SET
                        password_hash = %(password_hash)s,
                        must_change_password = true,
                        failed_login_count = 0,
                        locked_until = NULL,
                        password_changed_at = now(),
                        updated_at = now()
                    WHERE user_id = %(user_id)s
                    """,
                    {
                        "password_hash": _password_hasher().hash(temporary_password),
                        "user_id": user_id,
                    },
                )
                cursor.execute(
                    """
                    UPDATE proc.auth_sessions
                    SET revoked_at = now()
                    WHERE user_id = %(user_id)s AND revoked_at IS NULL
                    """,
                    {"user_id": user_id},
                )
                cursor.execute(
                    f"""
                    SELECT {_MANAGED_USER_COLUMNS}
                    FROM proc.app_users
                    WHERE user_id = %(user_id)s
                    """,
                    {"user_id": user_id},
                )
                return _managed_user_from_row(cursor.fetchone())
    except (ManagedUserConflictError, ManagedUserNotFoundError):
        raise
    except Exception as exception:
        raise DatabaseConnectionError("Temporary password reset failed.") from exception
