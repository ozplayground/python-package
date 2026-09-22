"""Declarative API interface decorators (@api_client, @get, @post, etc.)."""
import asyncio
import functools
import inspect
import re
from typing import Any, Callable, Optional, Type, TypeVar

from courier.client import get_client

T = TypeVar("T")


def _method_decorator(http_method: str, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Generic decorator factory for HTTP methods."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        fn._http_method = http_method.upper()  # type: ignore[attr-defined]
        fn._http_path = path  # type: ignore[attr-defined]
        return fn

    return decorator


def get(path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a GET endpoint."""
    return _method_decorator("GET", path)


def post(path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a POST endpoint."""
    return _method_decorator("POST", path)


def put(path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a PUT endpoint."""
    return _method_decorator("PUT", path)


def delete(path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a DELETE endpoint."""
    return _method_decorator("DELETE", path)


def patch(path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declare a PATCH endpoint."""
    return _method_decorator("PATCH", path)


def api_client(
    service: str = "default",
    base_url: Optional[str] = None,
    **client_kwargs: Any,
) -> Callable[[Type[T]], Type[T]]:
    """Class decorator binding an interface to an HttpClient with declarative routing."""

    def class_decorator(cls: Type[T]) -> Type[T]:
        orig_init = cls.__init__

        @functools.wraps(orig_init)
        def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
            kw = dict(client_kwargs)
            if base_url is not None:
                kw["base_url"] = base_url
            self._client = get_client(service, **kw)
            if orig_init is not object.__init__:
                orig_init(self, *args, **kwargs)

        cls.__init__ = new_init  # type: ignore[misc]

        def _wrap_method(attr_name: str, method: Any) -> None:
            http_method: str = getattr(method, "_http_method")
            route_path: str = getattr(method, "_http_path")
            sig = inspect.signature(method)
            is_async = asyncio.iscoroutinefunction(method)
            path_param_names = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", route_path)

            def _build_call_args(instance: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> tuple[str, dict[str, Any], Any, Any, Any, Any]:
                bound = sig.bind(instance, *args, **kwargs)
                bound.apply_defaults()
                call_kwargs = dict(bound.arguments)
                call_kwargs.pop("self", None)

                # Interpolate path params
                url = route_path
                for p in path_param_names:
                    if p not in call_kwargs:
                        raise ValueError(
                            f"Missing required path parameter '{p}' for route '{route_path}'"
                        )
                    url = url.replace(f"{{{p}}}", str(call_kwargs.pop(p)))

                json_val = call_kwargs.pop("json", None)
                data_val = call_kwargs.pop("data", None)
                headers_val = call_kwargs.pop("headers", None)
                timeout_val = call_kwargs.pop("timeout", None)
                query_params = dict(call_kwargs.pop("params", None) or {})

                if http_method in ("GET", "DELETE", "HEAD", "OPTIONS"):
                    query_params.update(call_kwargs)
                else:
                    if json_val is None and data_val is None and call_kwargs:
                        json_val = call_kwargs

                return url, query_params, headers_val, json_val, data_val, timeout_val

            if is_async:

                @functools.wraps(method)
                async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                    url, q_params, hdrs, j_val, d_val, to_val = _build_call_args(self, args, kwargs)
                    return await self._client.async_request(
                        method=http_method,
                        url=url,
                        params=q_params or None,
                        headers=hdrs,
                        json=j_val,
                        data=d_val,
                        timeout=to_val,
                    )

                setattr(cls, attr_name, async_wrapper)
            else:

                @functools.wraps(method)
                def sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                    url, q_params, hdrs, j_val, d_val, to_val = _build_call_args(self, args, kwargs)
                    return self._client.request(
                        method=http_method,
                        url=url,
                        params=q_params or None,
                        headers=hdrs,
                        json=j_val,
                        data=d_val,
                        timeout=to_val,
                    )

                setattr(cls, attr_name, sync_wrapper)

        for attr_name, method in list(cls.__dict__.items()):
            if callable(method) and hasattr(method, "_http_method"):
                _wrap_method(attr_name, method)

        return cls

    return class_decorator


# High-level aliases
courier_client = api_client
courier = api_client
