"""Standard exceptions for sqla-autoconfig."""


class SqlaAutoconfigError(Exception):
    """Base exception for all sqla-autoconfig errors."""
    pass


class ConfigurationError(SqlaAutoconfigError):
    """Raised when configuration validation or loading fails."""
    pass


class UnsupportedDialectError(ConfigurationError):
    """Raised when an unsupported database dialect is requested."""
    pass


class DriverNotFoundError(SqlaAutoconfigError):
    """Raised when a required database driver package is not installed."""
    pass


class ConnectionPoolError(SqlaAutoconfigError):
    """Raised when connection pool management encounters an issue."""
    pass


class TransactionError(SqlaAutoconfigError):
    """Raised when a database transaction fails and is rolled back."""
    pass
