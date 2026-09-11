from pathlib import Path


def test_schema_does_not_insert_runtime_sample_data() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "db" / "init" / "001_standard_schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")

    assert "INSERT INTO proc.modules (module_key, name, description)" not in schema_sql
    assert "INSERT INTO proc.blueprints (blueprint_key, name, description)" not in schema_sql
    assert "CREATE TABLE IF NOT EXISTS proc.app_users" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS proc.auth_sessions" in schema_sql
    assert "member / password" not in schema_sql
