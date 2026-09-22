"""sqla-autoconfig: Database Auto-Configuration and Connection Pool Manager for Python."""

from typing import Any, AsyncGenerator, Generator
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from sqla_autoconfig.config import ConfigLoader, DatabaseSettings
from sqla_autoconfig.dialects import DialectRegistry
from sqla_autoconfig.exceptions import (
    ConfigurationError,
    ConnectionPoolError,
    DriverNotFoundError,
    SqlaAutoconfigError,
    TransactionError,
    UnsupportedDialectError,
)
from sqla_autoconfig.manager import DatabaseManager
from sqla_autoconfig.decorators import async_transactional, transactional

__version__ = "0.1.0"


class _GlobalDatabaseProxy:
    """Lazy-initializing proxy for the global singleton `db` instance.
    
    This ensures that importing `from sqla_autoconfig import db` does not trigger
    immediate database connection attempts until an operation is actually performed.
    """

    def __init__(self):
        self._instance: DatabaseManager | None = None

    def _get_instance(self) -> DatabaseManager:
        if self._instance is None:
            self._instance = DatabaseManager()
        return self._instance

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get_instance(), name)


# Global singleton instance for zero-configuration usage
db = _GlobalDatabaseProxy()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for sync database session."""
    yield from db.get_db()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database session."""
    async for s in db.get_async_db():
        yield s


__all__ = [
    "db",
    "DatabaseManager",
    "DatabaseSettings",
    "ConfigLoader",
    "DialectRegistry",
    "transactional",
    "async_transactional",
    "get_db",
    "get_async_db",
    "SqlaAutoconfigError",
    "ConfigurationError",
    "UnsupportedDialectError",
    "DriverNotFoundError",
    "ConnectionPoolError",
    "TransactionError",
]
