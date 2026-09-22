"""Core DatabaseManager for managing SQLAlchemy engines, session factories, and connection pools."""

import atexit
from typing import Any, AsyncGenerator, Callable, ContextManager, Generator, Optional
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker

from sqla_autoconfig.config import ConfigLoader, DatabaseSettings
from sqla_autoconfig.context import (
    async_session_scope,
    async_transaction_scope,
    create_get_async_db_generator,
    create_get_db_generator,
    session_scope,
    transaction_scope,
)


class DatabaseManager:
    """Manages database connection pools, engines, and session factories with auto-configuration."""

    def __init__(
        self,
        settings: Optional[DatabaseSettings] = None,
        **kwargs: Any
    ):
        if settings is not None:
            self.settings = settings
        else:
            self.settings = ConfigLoader().load_cascading(**kwargs)

        self._sync_engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_session_factory: Optional[sessionmaker[Session]] = None
        self._async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

        # Auto-register process shutdown hook for zero connection leak
        atexit.register(self.dispose)

    def _get_engine_kwargs(self, url: str) -> dict[str, Any]:
        """Configure engine options with production-ready connection pool defaults."""
        kwargs: dict[str, Any] = {
            "echo": self.settings.echo,
        }
        # SQLite in-memory or file databases don't use QueuePool by default
        if not url.startswith("sqlite"):
            kwargs.update({
                "pool_size": self.settings.pool_size,
                "max_overflow": self.settings.max_overflow,
                "pool_recycle": self.settings.pool_recycle,
                "pool_pre_ping": self.settings.pool_pre_ping,
                "pool_timeout": self.settings.pool_timeout,
            })
        return kwargs

    def get_sync_engine(self) -> Engine:
        """Get or initialize the synchronous SQLAlchemy Engine."""
        if self._sync_engine is None:
            sync_url = self.settings.build_url(async_mode=False)
            kwargs = self._get_engine_kwargs(sync_url)
            self._sync_engine = create_engine(sync_url, **kwargs)
        return self._sync_engine

    def get_async_engine(self) -> AsyncEngine:
        """Get or initialize the asynchronous SQLAlchemy AsyncEngine."""
        if self._async_engine is None:
            async_url = self.settings.build_url(async_mode=True)
            kwargs = self._get_engine_kwargs(async_url)
            self._async_engine = create_async_engine(async_url, **kwargs)
        return self._async_engine

    @property
    def sync_session_factory(self) -> sessionmaker[Session]:
        """Get or initialize the synchronous session factory."""
        if self._sync_session_factory is None:
            self._sync_session_factory = sessionmaker(
                bind=self.get_sync_engine(),
                autoflush=False,
                expire_on_commit=False,
            )
        return self._sync_session_factory

    @property
    def async_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or initialize the asynchronous session factory."""
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.get_async_engine(),
                autoflush=False,
                expire_on_commit=False,
            )
        return self._async_session_factory

    def session(self) -> ContextManager[Session]:
        """Context manager yielding a synchronous Session without auto-commit."""
        return session_scope(self.sync_session_factory)

    def transaction(self) -> ContextManager[Session]:
        """Context manager yielding a synchronous Session with automatic commit and rollback."""
        return transaction_scope(self.sync_session_factory)

    def async_session(self):
        """Asynchronous context manager yielding an AsyncSession without auto-commit."""
        return async_session_scope(self.async_session_factory)

    def async_transaction(self):
        """Asynchronous context manager yielding an AsyncSession with automatic commit and rollback."""
        return async_transaction_scope(self.async_session_factory)

    def get_db(self) -> Generator[Session, None, None]:
        """FastAPI synchronous dependency injection generator."""
        return create_get_db_generator(self.sync_session_factory)()

    def get_async_db(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI asynchronous dependency injection generator."""
        return create_get_async_db_generator(self.async_session_factory)()

    def transactional(self, func: Optional[Callable[..., Any]] = None):
        """Instance decorator for transactional methods bound to this manager."""
        from sqla_autoconfig.decorators import transactional as _transactional
        if func is not None:
            return _transactional(manager=self)(func)
        return _transactional(manager=self)

    def async_transactional(self, func: Optional[Callable[..., Any]] = None):
        """Instance decorator for async transactional methods bound to this manager."""
        from sqla_autoconfig.decorators import async_transactional as _async_transactional
        if func is not None:
            return _async_transactional(manager=self)(func)
        return _async_transactional(manager=self)

    def dispose(self) -> None:
        """Dispose of the synchronous engine and close all idle/checked-in connections."""
        if self._sync_engine is not None:
            self._sync_engine.dispose()
            self._sync_engine = None
            self._sync_session_factory = None

    async def async_dispose(self) -> None:
        """Dispose of the asynchronous engine and close all connections."""
        if self._async_engine is not None:
            await self._async_engine.dispose()
            self._async_engine = None
            self._async_session_factory = None
