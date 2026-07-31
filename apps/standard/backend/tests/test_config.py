"""Tests for application configuration."""

import pytest

from app.core.config import (
    AppSettings,
    _get_csv_from_env,
    _get_float_from_env,
    _get_int_from_env,
    get_settings,
)


def test_database_url_uses_postgresql_settings() -> None:
    """Database URL should include all PostgreSQL connection values."""

    settings = AppSettings(
        db_host="db.example.local",
        db_port=15432,
        db_name="example_db",
        db_user="example_user",
        db_password="example_password",
    )

    assert settings.database_url == (
        "postgresql://example_user:example_password"
        "@db.example.local:15432/example_db"
    )


def test_get_int_from_env_returns_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset integer environment variables should return the supplied default."""

    monkeypatch.delenv("EXAMPLE_PORT", raising=False)

    assert _get_int_from_env("EXAMPLE_PORT", 5432) == 5432


def test_get_int_from_env_raises_for_invalid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid integer environment variables should raise ValueError."""

    monkeypatch.setenv("EXAMPLE_PORT", "invalid")

    with pytest.raises(ValueError):
        _get_int_from_env("EXAMPLE_PORT", 5432)


def test_get_float_from_env_loads_similarity_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    """Floating-point environment variables should be parsed."""

    monkeypatch.setenv("EXAMPLE_THRESHOLD", "0.82")

    assert _get_float_from_env("EXAMPLE_THRESHOLD", 0.70) == 0.82


def test_get_csv_from_env_returns_trimmed_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Comma-separated environment variables should be trimmed and filtered."""

    monkeypatch.setenv("EXAMPLE_ORIGINS", " http://localhost:3000, ,http://127.0.0.1:5173 ")

    assert _get_csv_from_env("EXAMPLE_ORIGINS", ("fallback",)) == (
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    )


def test_get_csv_from_env_returns_default_for_blank_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Blank comma-separated environment variables should return the supplied default."""

    monkeypatch.setenv("EXAMPLE_ORIGINS", " , ")

    assert _get_csv_from_env("EXAMPLE_ORIGINS", ("fallback",)) == ("fallback",)

def test_get_settings_loads_case_doc_master_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Case document master settings should be loaded from environment variables."""

    monkeypatch.setenv("CASE_DOC_MASTER_SOURCE", "seed")
    monkeypatch.setenv("CASE_DOC_ACCESS_EXPORT_DIR", "/tmp/access_exports")
    monkeypatch.setenv("CASE_DOC_IMPORT_STRICT", "false")
    monkeypatch.setenv("MODULE_IMAGE_STORAGE_DIR", "/tmp/module_images")
    monkeypatch.setenv("MODULE_SIMILARITY_THRESHOLD", "0.72")
    monkeypatch.setenv("MODULE_SIMILARITY_CANDIDATE_LIMIT", "40")
    monkeypatch.setenv("MODULE_SIMILARITY_RESULT_LIMIT", "8")
    monkeypatch.setenv(
        "MODULE_SIMILARITY_CONFIRMATION_SECRET",
        "test-confirmation-secret",
    )
    monkeypatch.setenv("MODULE_SIMILARITY_CONFIRMATION_TTL_SECONDS", "600")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.case_doc_master_source == "seed"
    assert settings.case_doc_access_export_dir == "/tmp/access_exports"
    assert settings.case_doc_import_strict is False
    assert settings.module_image_storage_dir == "/tmp/module_images"
    assert settings.module_similarity_threshold == 0.72
    assert settings.module_similarity_candidate_limit == 40
    assert settings.module_similarity_result_limit == 8
    assert settings.module_similarity_confirmation_secret == "test-confirmation-secret"
    assert settings.module_similarity_confirmation_ttl_seconds == 600

    get_settings.cache_clear()
