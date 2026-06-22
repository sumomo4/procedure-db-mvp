"""Application-specific exceptions."""


class DatabaseConnectionError(RuntimeError):
    """Raised when the API cannot confirm PostgreSQL connectivity."""
