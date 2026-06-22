"""PostgreSQL connectivity helpers."""

from app.core.config import AppSettings
from app.core.exceptions import DatabaseConnectionError
from app.core.responses import DatabaseHealthData


def check_database_connection(settings: AppSettings) -> DatabaseHealthData:
    """Confirm that PostgreSQL accepts a basic query.

    Args:
        settings: Application settings that contain PostgreSQL connection values.

    Returns:
        Database health payload.

    Raises:
        DatabaseConnectionError: If the PostgreSQL driver is missing, the
            connection fails, or the validation query returns an unexpected value.
    """

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
                cursor.execute("SELECT 1")
                query_result = cursor.fetchone()
    except Exception as exception:
        raise DatabaseConnectionError("PostgreSQL connection check failed.") from exception

    if query_result != (1,):
        raise DatabaseConnectionError("PostgreSQL connection check returned an invalid result.")

    return DatabaseHealthData(
        database=settings.db_name,
        host=settings.db_host,
        port=settings.db_port,
        status="ok",
    )
