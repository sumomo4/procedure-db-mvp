"""Application configuration for the standard API."""

from functools import lru_cache
import os

from pydantic import BaseModel, Field


DEFAULT_DB_CONNECT_TIMEOUT_SECONDS = 3
DEFAULT_CORS_ALLOW_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

DEFAULT_MODULE_SIMILARITY_THRESHOLD = 0.70
DEFAULT_MODULE_SIMILARITY_CANDIDATE_LIMIT = 50
DEFAULT_MODULE_SIMILARITY_RESULT_LIMIT = 10
DEFAULT_MODULE_SIMILARITY_CONFIRMATION_SECRET = "lab-similarity-confirmation-secret"
DEFAULT_MODULE_SIMILARITY_CONFIRMATION_TTL_SECONDS = 900


class AppSettings(BaseModel):
    """Runtime settings loaded from environment variables.

    Attributes:
        app_env: Application environment name.
        service_name: Human-readable service name.
        api_prefix: Prefix used by versioned API routes.
        db_host: PostgreSQL host name.
        db_port: PostgreSQL port number.
        db_name: PostgreSQL database name.
        db_user: PostgreSQL user name.
        db_password: PostgreSQL password.
        db_connect_timeout_seconds: PostgreSQL connection timeout in seconds.
        cors_allow_origins: Origins allowed to call the API from a browser.
        case_doc_master_source: Source used for case document master data.
        case_doc_access_export_dir: Directory where Access export files are placed.
        case_doc_import_strict: Whether Access export import should fail on validation warnings.
        case_doc_placeholder_mapping_path: YAML path for case document placeholder mappings.
        module_image_storage_dir: Directory where extracted module row images are stored.
    """

    app_env: str = Field(default="standard")
    service_name: str = Field(default="standard-api")
    api_prefix: str = Field(default="/api/v1")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="mvp_standard")
    db_user: str = Field(default="standard_user")
    db_password: str = Field(default="standard_password")
    db_connect_timeout_seconds: int = Field(default=DEFAULT_DB_CONNECT_TIMEOUT_SECONDS, ge=1)
    cors_allow_origins: tuple[str, ...] = Field(default=DEFAULT_CORS_ALLOW_ORIGINS)
    case_doc_master_source: str = Field(default="seed")
    case_doc_access_export_dir: str = Field(default="/app/storage/access_exports")
    case_doc_import_strict: bool = Field(default=True)
    case_doc_placeholder_mapping_path: str = Field(default="app/config/placeholder_mapping.yml")
    module_image_storage_dir: str = Field(default="/app/storage/module_images")
    module_similarity_threshold: float = Field(default=DEFAULT_MODULE_SIMILARITY_THRESHOLD, ge=0, le=1)
    module_similarity_candidate_limit: int = Field(default=DEFAULT_MODULE_SIMILARITY_CANDIDATE_LIMIT, ge=1)
    module_similarity_result_limit: int = Field(default=DEFAULT_MODULE_SIMILARITY_RESULT_LIMIT, ge=1)
    module_similarity_confirmation_secret: str = Field(
        default=DEFAULT_MODULE_SIMILARITY_CONFIRMATION_SECRET,
        min_length=16,
    )
    module_similarity_confirmation_ttl_seconds: int = Field(
        default=DEFAULT_MODULE_SIMILARITY_CONFIRMATION_TTL_SECONDS,
        ge=60,
    )

    @property
    def database_url(self) -> str:
        """Build a PostgreSQL connection URL.

        Returns:
            PostgreSQL URL suitable for psycopg.
        """

        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


def _get_int_from_env(name: str, default_value: int) -> int:
    """Read an integer environment variable.

    Args:
        name: Environment variable name.
        default_value: Value used when the variable is unset.

    Returns:
        Parsed integer value.

    Raises:
        ValueError: If the environment value cannot be parsed as an integer.
    """

    raw_value = os.environ.get(name)
    if raw_value is None:
        return default_value

    return int(raw_value)


def _get_float_from_env(name: str, default_value: float) -> float:
    """Read a floating-point environment variable.

    Args:
        name: Environment variable name.
        default_value: Value used when the variable is unset.

    Returns:
        Parsed floating-point value.

    Raises:
        ValueError: If the environment value cannot be parsed as a float.
    """

    raw_value = os.environ.get(name)
    if raw_value is None:
        return default_value

    return float(raw_value)


def _get_csv_from_env(name: str, default_value: tuple[str, ...]) -> tuple[str, ...]:
    """Read a comma-separated environment variable.

    Args:
        name: Environment variable name.
        default_value: Value used when the variable is unset or blank.

    Returns:
        Tuple of trimmed non-empty values.
    """

    raw_value = os.environ.get(name)
    if raw_value is None:
        return default_value

    values = tuple(item.strip() for item in raw_value.split(",") if item.strip())
    if not values:
        return default_value

    return values


@lru_cache
def get_settings() -> AppSettings:
    """Load application settings from environment variables.

    Returns:
        Application settings.

    Raises:
        ValueError: If integer environment variables contain invalid values.
    """

    return AppSettings(
        app_env=os.environ.get("APP_ENV", "standard"),
        service_name=os.environ.get("SERVICE_NAME", "standard-api"),
        api_prefix=os.environ.get("API_PREFIX", "/api/v1"),
        db_host=os.environ.get("DB_HOST", "localhost"),
        db_port=_get_int_from_env("DB_PORT", 5432),
        db_name=os.environ.get("DB_NAME", "mvp_standard"),
        db_user=os.environ.get("DB_USER", "standard_user"),
        db_password=os.environ.get("DB_PASSWORD", "standard_password"),
        db_connect_timeout_seconds=_get_int_from_env(
            "DB_CONNECT_TIMEOUT_SECONDS",
            DEFAULT_DB_CONNECT_TIMEOUT_SECONDS,
        ),
        cors_allow_origins=_get_csv_from_env(
            "CORS_ALLOW_ORIGINS",
            DEFAULT_CORS_ALLOW_ORIGINS,
        ),
        case_doc_master_source=os.environ.get("CASE_DOC_MASTER_SOURCE", "seed"),
        case_doc_access_export_dir=os.environ.get("CASE_DOC_ACCESS_EXPORT_DIR", "/app/storage/access_exports"),
        case_doc_import_strict=os.environ.get("CASE_DOC_IMPORT_STRICT", "true").lower() == "true",
        case_doc_placeholder_mapping_path=os.environ.get(
            "CASE_DOC_PLACEHOLDER_MAPPING_PATH",
            "app/config/placeholder_mapping.yml",
        ),
        module_image_storage_dir=os.environ.get("MODULE_IMAGE_STORAGE_DIR", "/app/storage/module_images"),
        module_similarity_threshold=_get_float_from_env(
            "MODULE_SIMILARITY_THRESHOLD",
            DEFAULT_MODULE_SIMILARITY_THRESHOLD,
        ),
        module_similarity_candidate_limit=_get_int_from_env(
            "MODULE_SIMILARITY_CANDIDATE_LIMIT",
            DEFAULT_MODULE_SIMILARITY_CANDIDATE_LIMIT,
        ),
        module_similarity_result_limit=_get_int_from_env(
            "MODULE_SIMILARITY_RESULT_LIMIT",
            DEFAULT_MODULE_SIMILARITY_RESULT_LIMIT,
        ),
        module_similarity_confirmation_secret=os.environ.get(
            "MODULE_SIMILARITY_CONFIRMATION_SECRET",
            DEFAULT_MODULE_SIMILARITY_CONFIRMATION_SECRET,
        ),
        module_similarity_confirmation_ttl_seconds=_get_int_from_env(
            "MODULE_SIMILARITY_CONFIRMATION_TTL_SECONDS",
            DEFAULT_MODULE_SIMILARITY_CONFIRMATION_TTL_SECONDS,
        ),
    )
