"""Declarative transaction decorators for synchronous and asynchronous functions."""

import functools
import inspect
from typing import Any, Callable, Optional, TypeVar, cast

from sqla_autoconfig.exceptions import TransactionError

F = TypeVar("F", bound=Callable[..., Any])


def transactional(
    manager: Optional[Any] = None
) -> Callable[[F], F]:
    """Declarative transaction decorator for synchronous functions.
    
    If 'session' is in the target function's parameters, the active transaction session
    is automatically injected into kwargs['session'].
    Automatically commits on normal return and rolls back on exception.
    """
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        has_session_param = "session" in sig.parameters

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Resolve manager (passed explicitly or fallback to global db)
            db_manager = manager
            if db_manager is None:
                from sqla_autoconfig import db
                db_manager = db

            with db_manager.transaction() as session:
                if has_session_param and "session" not in kwargs:
                    kwargs["session"] = session
                return func(*args, **kwargs)

        return cast(F, wrapper)

    # Support @transactional without parentheses
    if callable(manager):
        actual_func = manager
        manager = None
        return decorator(actual_func)

    return decorator


def async_transactional(
    manager: Optional[Any] = None
) -> Callable[[F], F]:
    """Declarative transaction decorator for asynchronous coroutines.
    
    If 'session' is in the target function's parameters, the active async transaction session
    is automatically injected into kwargs['session'].
    Automatically commits on normal return and rolls back on exception.
    """
    def decorator(func: F) -> F:
        sig = inspect.signature(func)
        has_session_param = "session" in sig.parameters

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            db_manager = manager
            if db_manager is None:
                from sqla_autoconfig import db
                db_manager = db

            async with db_manager.async_transaction() as session:
                if has_session_param and "session" not in kwargs:
                    kwargs["session"] = session
                return await func(*args, **kwargs)

        return cast(F, wrapper)

    if callable(manager):
        actual_func = manager
        manager = None
        return decorator(actual_func)

    return decorator
