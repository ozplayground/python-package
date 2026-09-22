"""Context managers for synchronous and asynchronous sessions and transactions."""

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, AsyncIterator, Callable, Generator, Iterator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session


@contextmanager
def session_scope(session_factory: Callable[[], Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def transaction_scope(session_factory: Callable[[], Session]) -> Iterator[Session]:
    """Provide a transactional scope that automatically commits on success and rolls back on failure."""
    session = session_factory()
    try:
        with session.begin():
            yield session
    except Exception:
        # session.begin() already issues rollback on exception, but explicit guarantee
        if session.in_transaction():
            session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def async_session_scope(
    async_session_factory: Callable[[], AsyncSession]
) -> AsyncIterator[AsyncSession]:
    """Provide an asynchronous session scope around operations."""
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def async_transaction_scope(
    async_session_factory: Callable[[], AsyncSession]
) -> AsyncIterator[AsyncSession]:
    """Provide an asynchronous transactional scope that automatically commits on success and rolls back on failure."""
    session = async_session_factory()
    try:
        async with session.begin():
            yield session
    except Exception:
        if session.in_transaction():
            await session.rollback()
        raise
    finally:
        await session.close()


def create_get_db_generator(session_factory: Callable[[], Session]) -> Callable[[], Generator[Session, None, None]]:
    """Factory for FastAPI sync Depends(get_db) dependency."""
    def get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()
    return get_db


def create_get_async_db_generator(
    async_session_factory: Callable[[], AsyncSession]
) -> Callable[[], AsyncGenerator[AsyncSession, None]]:
    """Factory for FastAPI async Depends(get_async_db) dependency."""
    async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
        session = async_session_factory()
        try:
            yield session
        finally:
            await session.close()
    return get_async_db
