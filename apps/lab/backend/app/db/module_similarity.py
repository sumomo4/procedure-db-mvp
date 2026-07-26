"""PostgreSQL persistence for module similarity signatures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.services.module_similarity import ModuleSimilaritySignature


@dataclass(frozen=True, slots=True)
class ModuleSimilarityCandidateRecord:
    """Persisted candidate and its precomputed similarity signature."""

    module_id: int
    module_key: str
    module_name: str
    module_version_id: int
    version_no: int
    version_major: int
    version_minor: int
    status: str
    signature: ModuleSimilaritySignature
    shortlist_similarity: float

    @property
    def version_label(self) -> str:
        """Return the user-facing version label."""

        return f"ver.{self.version_major}.{self.version_minor}"


def _ensure_module_similarity_schema(cursor: Any) -> None:
    """Create similarity persistence objects for an existing Lab database."""

    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS proc.module_similarity_signatures (
            module_version_id bigint PRIMARY KEY
                REFERENCES proc.module_versions (module_version_id)
                ON DELETE CASCADE,
            normalized_name text NOT NULL,
            normalized_work_text text NOT NULL,
            normalized_expected_text text NOT NULL,
            normalized_command_text text NOT NULL,
            normalized_structure_text text NOT NULL,
            normalized_device_header_text text NOT NULL,
            normalized_image_text text NOT NULL,
            combined_text text NOT NULL,
            exact_sha256 varchar(64) NOT NULL,
            row_count integer NOT NULL,
            image_count integer NOT NULL,
            generated_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_module_similarity_signatures_exact_sha256
            ON proc.module_similarity_signatures (exact_sha256);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_module_similarity_signatures_combined_text_trgm
            ON proc.module_similarity_signatures
            USING gin (combined_text gin_trgm_ops);
        """
    )


def list_missing_published_module_versions(
    settings: AppSettings,
) -> list[tuple[int, int, int]]:
    """Return latest published module versions without a signature."""

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
                _ensure_module_similarity_schema(cursor)
                cursor.execute(
                    """
                    WITH latest_published AS (
                        SELECT DISTINCT ON (mv.module_id)
                            mv.module_id,
                            mv.module_version_id,
                            mv.version_no
                        FROM proc.module_versions mv
                        WHERE mv.status = 'published'
                        ORDER BY mv.module_id, mv.version_no DESC
                    )
                    SELECT
                        latest.module_id,
                        latest.module_version_id,
                        latest.version_no
                    FROM latest_published latest
                    LEFT JOIN proc.module_similarity_signatures signature
                        ON signature.module_version_id = latest.module_version_id
                    WHERE signature.module_version_id IS NULL
                    ORDER BY latest.module_id;
                    """
                )
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError(
            "Module similarity signature lookup failed."
        ) from exception

    return [
        (int(row[0]), int(row[1]), int(row[2]))
        for row in rows
    ]


def upsert_module_similarity_signatures(
    settings: AppSettings,
    signatures: list[tuple[int, ModuleSimilaritySignature]],
) -> None:
    """Insert or refresh precomputed signatures for module versions."""

    if not signatures:
        return

    try:
        import psycopg
    except ModuleNotFoundError as exception:
        raise DatabaseConnectionError("PostgreSQL driver is not installed.") from exception

    query = """
        INSERT INTO proc.module_similarity_signatures (
            module_version_id,
            normalized_name,
            normalized_work_text,
            normalized_expected_text,
            normalized_command_text,
            normalized_structure_text,
            normalized_device_header_text,
            normalized_image_text,
            combined_text,
            exact_sha256,
            row_count,
            image_count,
            generated_at
        )
        VALUES (
            %(module_version_id)s,
            %(normalized_name)s,
            %(normalized_work_text)s,
            %(normalized_expected_text)s,
            %(normalized_command_text)s,
            %(normalized_structure_text)s,
            %(normalized_device_header_text)s,
            %(normalized_image_text)s,
            %(combined_text)s,
            %(exact_sha256)s,
            %(row_count)s,
            %(image_count)s,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (module_version_id)
        DO UPDATE SET
            normalized_name = EXCLUDED.normalized_name,
            normalized_work_text = EXCLUDED.normalized_work_text,
            normalized_expected_text = EXCLUDED.normalized_expected_text,
            normalized_command_text = EXCLUDED.normalized_command_text,
            normalized_structure_text = EXCLUDED.normalized_structure_text,
            normalized_device_header_text = EXCLUDED.normalized_device_header_text,
            normalized_image_text = EXCLUDED.normalized_image_text,
            combined_text = EXCLUDED.combined_text,
            exact_sha256 = EXCLUDED.exact_sha256,
            row_count = EXCLUDED.row_count,
            image_count = EXCLUDED.image_count,
            generated_at = CURRENT_TIMESTAMP;
    """

    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout_seconds,
        ) as connection:
            with connection.cursor() as cursor:
                _ensure_module_similarity_schema(cursor)
                for module_version_id, signature in signatures:
                    cursor.execute(
                        query,
                        {
                            "module_version_id": module_version_id,
                            "normalized_name": signature.normalized_name,
                            "normalized_work_text": signature.normalized_work_text,
                            "normalized_expected_text": signature.normalized_expected_text,
                            "normalized_command_text": signature.normalized_command_text,
                            "normalized_structure_text": signature.normalized_structure_text,
                            "normalized_device_header_text": (
                                signature.normalized_device_header_text
                            ),
                            "normalized_image_text": signature.normalized_image_text,
                            "combined_text": signature.combined_text,
                            "exact_sha256": signature.exact_sha256,
                            "row_count": signature.row_count,
                            "image_count": signature.image_count,
                        },
                    )
    except Exception as exception:
        raise DatabaseConnectionError(
            "Module similarity signature update failed."
        ) from exception


def list_module_similarity_candidates(
    settings: AppSettings,
    incoming_signature: ModuleSimilaritySignature,
    excluded_module_key: str | None,
    limit: int,
) -> list[ModuleSimilarityCandidateRecord]:
    """Return a trigram-shortlisted set of latest published modules."""

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
                _ensure_module_similarity_schema(cursor)
                cursor.execute(
                    """
                    WITH latest_published AS (
                        SELECT DISTINCT ON (mv.module_id)
                            m.module_id,
                            m.module_key,
                            m.name,
                            mv.module_version_id,
                            mv.version_no,
                            mv.version_major,
                            mv.version_minor,
                            mv.status
                        FROM proc.modules m
                        JOIN proc.module_versions mv
                            ON mv.module_id = m.module_id
                        WHERE mv.status = 'published'
                        ORDER BY mv.module_id, mv.version_no DESC
                    )
                    SELECT
                        latest.module_id,
                        latest.module_key,
                        latest.name,
                        latest.module_version_id,
                        latest.version_no,
                        latest.version_major,
                        latest.version_minor,
                        latest.status,
                        signature.normalized_name,
                        signature.normalized_work_text,
                        signature.normalized_expected_text,
                        signature.normalized_command_text,
                        signature.normalized_structure_text,
                        signature.normalized_device_header_text,
                        signature.normalized_image_text,
                        signature.combined_text,
                        signature.exact_sha256,
                        signature.row_count,
                        signature.image_count,
                        CASE
                            WHEN signature.exact_sha256 = %(exact_sha256)s THEN 1.0
                            ELSE similarity(
                                signature.combined_text,
                                %(combined_text)s
                            )
                        END AS shortlist_similarity
                    FROM latest_published latest
                    JOIN proc.module_similarity_signatures signature
                        ON signature.module_version_id = latest.module_version_id
                    WHERE (
                        CAST(%(excluded_module_key)s AS text) IS NULL
                        OR latest.module_key <> CAST(%(excluded_module_key)s AS text)
                    )
                    ORDER BY
                        (signature.exact_sha256 = %(exact_sha256)s) DESC,
                        shortlist_similarity DESC,
                        latest.module_key
                    LIMIT %(limit)s;
                    """,
                    {
                        "exact_sha256": incoming_signature.exact_sha256,
                        "combined_text": incoming_signature.combined_text,
                        "excluded_module_key": excluded_module_key,
                        "limit": limit,
                    },
                )
                rows = cursor.fetchall()
    except Exception as exception:
        raise DatabaseConnectionError(
            "Module similarity candidate query failed."
        ) from exception

    candidates: list[ModuleSimilarityCandidateRecord] = []
    for row in rows:
        signature = ModuleSimilaritySignature(
            normalized_name=str(row[8]),
            normalized_work_text=str(row[9]),
            normalized_expected_text=str(row[10]),
            normalized_command_text=str(row[11]),
            normalized_structure_text=str(row[12]),
            normalized_device_header_text=str(row[13]),
            normalized_image_text=str(row[14]),
            combined_text=str(row[15]),
            exact_sha256=str(row[16]),
            row_count=int(row[17]),
            image_count=int(row[18]),
        )
        candidates.append(
            ModuleSimilarityCandidateRecord(
                module_id=int(row[0]),
                module_key=str(row[1]),
                module_name=str(row[2]),
                module_version_id=int(row[3]),
                version_no=int(row[4]),
                version_major=int(row[5] or 0),
                version_minor=int(row[6] or 0),
                status=str(row[7]),
                signature=signature,
                shortlist_similarity=float(row[19]),
            )
        )

    return candidates
