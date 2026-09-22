"""Core HTTPX client engine, connection pooling, and global proxy registry."""
import asyncio
import atexit
import threading
from typing import Any, Mapping, Optional, Sequence, Union
import httpx
from pydantic import BaseModel

from courier.config import ClientConfig, ConfigLoader
from courier.exceptions import ApiConnectionError, ApiTimeoutError
from courier.response import ApiError, ApiResponse
from courier.retry import RetryEngine

MAX_BODY_BUFFER_SIZE = 1024 * 1024  # 1MB buffer safety threshold


class HttpClient:
    """Thread-safe, high-resilience HTTP client supporting sync and async operations."""

    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self._sync_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
        self._retry_engine = RetryEngine(config.retry)
        self._sync_lock = threading.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_sync_client(self) -> httpx.Client:
        """Lazily initialize or return thread-safe sync httpx.Client."""
        with self._sync_lock:
            if self._sync_client is None or self._sync_client.is_closed:
                self._sync_client = httpx.Client(
                    base_url=self.config.base_url,
                    timeout=self.config.to_httpx_timeout(),
                    limits=self.config.to_httpx_limits(),
                    headers=self.config.headers,
                )
            return self._sync_client

    def _get_async_client(self) -> httpx.AsyncClient:
        """Lazily initialize or return async httpx.AsyncClient bound to current running loop."""
        current_loop = asyncio.get_running_loop()
        if (
            self._async_client is None
            or self._async_client.is_closed
            or self._loop != current_loop
            or (self._loop and self._loop.is_closed())
        ):
            self._loop = current_loop
            self._async_client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.to_httpx_timeout(),
                limits=self.config.to_httpx_limits(),
                headers=self.config.headers,
            )
        return self._async_client

    def _prepare_payload(
        self,
        json_data: Optional[Union[Mapping[str, Any], Sequence[Any], BaseModel]] = None,
        data: Optional[Union[Mapping[str, Any], bytes]] = None,
    ) -> tuple[Any, Any]:
        """Convert Pydantic BaseModel to JSON-compatible dict."""
        if json_data is not None and isinstance(json_data, BaseModel):
            json_data = json_data.model_dump(mode="json")
        return json_data, data

    def _build_response(
        self,
        response: Optional[httpx.Response],
        exception: Optional[Exception],
        duration_ms: float,
        request_url: str,
    ) -> ApiResponse[Any]:
        """Convert raw HTTPX response or exception into unified ApiResponse[T]."""
        if response is not None:
            status_code = response.status_code
            headers = dict(response.headers)
            raw_bytes = response.content

            if len(raw_bytes) > MAX_BODY_BUFFER_SIZE:
                raw_text = (
                    raw_bytes[:MAX_BODY_BUFFER_SIZE].decode("utf-8", errors="replace")
                    + " [TRUNCATED: Response body exceeded 1MB]"
                )
            else:
                raw_text = response.text

            data: Any = None
            if status_code != 204 and raw_text:
                try:
                    data = response.json()
                except Exception:
                    data = raw_text

            is_success = 200 <= status_code < 300
            error: Optional[ApiError] = None

            if not is_success:
                error_msg = f"HTTP {status_code}"
                if isinstance(data, dict) and "message" in data:
                    error_msg = str(data["message"])
                elif raw_text:
                    error_msg = raw_text[:200]

                retry_after = self._retry_engine._parse_retry_after(headers)
                error = ApiError(
                    code=f"ERR_HTTP_{status_code}",
                    message=error_msg,
                    details=data if isinstance(data, dict) else None,
                    retry_after=retry_after,
                    is_retryable=self.config.retry.is_retryable_status(status_code),
                )

            return ApiResponse[Any](
                status_code=status_code,
                is_success=is_success,
                data=data if is_success else None,
                error=error,
                duration_ms=round(duration_ms, 2),
                headers=headers,
                raw_text=raw_text,
                request_url=str(response.url) if response.url else request_url,
            )

        # Exception handling
        if isinstance(exception, httpx.TimeoutException):
            err_code = "ERR_ENG_TIMEOUT"
            err_msg = str(exception) or "Request timed out"
        elif isinstance(exception, httpx.ConnectError):
            err_code = "ERR_ENG_CONNECT_FAILED"
            err_msg = str(exception) or "Failed to connect to host"
        elif isinstance(exception, httpx.NetworkError):
            err_code = "ERR_ENG_NETWORK"
            err_msg = str(exception) or "Network communication failure"
        else:
            err_code = "ERR_ENG_UNKNOWN"
            err_msg = str(exception) if exception else "Unknown request failure"

        error = ApiError(
            code=err_code,
            message=err_msg,
            details={"exception_type": type(exception).__name__} if exception else None,
            is_retryable=(
                self.config.retry.is_retryable_exception(exception)
                if exception
                else False
            ),
        )

        return ApiResponse[Any](
            status_code=0,
            is_success=False,
            data=None,
            error=error,
            duration_ms=round(duration_ms, 2),
            headers={},
            raw_text=None,
            request_url=request_url,
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        json: Optional[Union[Mapping[str, Any], Sequence[Any], BaseModel]] = None,
        data: Optional[Union[Mapping[str, Any], bytes]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        **kwargs: Any,
    ) -> ApiResponse[Any]:
        """Synchronously send HTTP request with automatic retry and error mapping."""
        is_idempotent = method.upper() in ("GET", "HEAD", "PUT", "DELETE", "OPTIONS")
        json_payload, form_data = self._prepare_payload(json, data)

        def call_fn() -> httpx.Response:
            client = self._get_sync_client()
            return client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_payload,
                data=form_data,
                timeout=timeout,
                **kwargs,
            )

        resp, exc, duration = self._retry_engine.execute_sync(
            call_fn, is_idempotent=is_idempotent
        )
        return self._build_response(resp, exc, duration, url)

    async def async_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        json: Optional[Union[Mapping[str, Any], Sequence[Any], BaseModel]] = None,
        data: Optional[Union[Mapping[str, Any], bytes]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        **kwargs: Any,
    ) -> ApiResponse[Any]:
        """Asynchronously send HTTP request with automatic retry and error mapping."""
        is_idempotent = method.upper() in ("GET", "HEAD", "PUT", "DELETE", "OPTIONS")
        json_payload, form_data = self._prepare_payload(json, data)

        async def call_fn() -> httpx.Response:
            client = self._get_async_client()
            return await client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_payload,
                data=form_data,
                timeout=timeout,
                **kwargs,
            )

        resp, exc, duration = await self._retry_engine.execute_async(
            call_fn, is_idempotent=is_idempotent
        )
        return self._build_response(resp, exc, duration, url)

    # Convenience sync methods
    def get(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return self.request("DELETE", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return self.request("PATCH", url, **kwargs)

    # Convenience async methods
    async def async_get(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return await self.async_request("GET", url, **kwargs)

    async def async_post(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return await self.async_request("POST", url, **kwargs)

    async def async_put(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return await self.async_request("PUT", url, **kwargs)

    async def async_delete(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return await self.async_request("DELETE", url, **kwargs)

    async def async_patch(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        return await self.async_request("PATCH", url, **kwargs)

    def close(self) -> None:
        """Close synchronous client socket connection pool."""
        with self._sync_lock:
            if self._sync_client is not None:
                self._sync_client.close()
                self._sync_client = None

    async def aclose(self) -> None:
        """Close asynchronous client socket connection pool."""
        if self._async_client is not None:
            await self._async_client.aclose()
            self._async_client = None


class _GlobalHttpProxy:
    """Global singleton proxy delegating requests to service-specific HttpClient instances."""

    def __init__(self) -> None:
        self._registry: dict[str, HttpClient] = {}
        self._lock = threading.Lock()

    def get_client(self, service_name: str = "default", **kwargs: Any) -> HttpClient:
        """Get or create singleton HttpClient instance for specified service."""
        with self._lock:
            if kwargs:
                cfg = ConfigLoader.load(service_name, **kwargs)
                client = HttpClient(cfg)
                self._registry[service_name] = client
                return client
            if service_name not in self._registry:
                cfg = ConfigLoader.load(service_name)
                self._registry[service_name] = HttpClient(cfg)
            return self._registry[service_name]

    def close_all(self) -> None:
        """Close all registered synchronous clients."""
        with self._lock:
            clients = list(self._registry.values())
            self._registry.clear()
        for client in clients:
            try:
                client.close()
            except Exception:
                pass

    async def aclose_all(self) -> None:
        """Close all registered asynchronous clients."""
        with self._lock:
            clients = list(self._registry.values())
            self._registry.clear()
        for client in clients:
            try:
                await client.aclose()
            except Exception:
                pass

    def get(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return self.get_client(service).get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return self.get_client(service).post(url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return self.get_client(service).put(url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return self.get_client(service).delete(url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return self.get_client(service).patch(url, **kwargs)

    async def async_get(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return await self.get_client(service).async_get(url, **kwargs)

    async def async_post(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return await self.get_client(service).async_post(url, **kwargs)

    async def async_put(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return await self.get_client(service).async_put(url, **kwargs)

    async def async_delete(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return await self.get_client(service).async_delete(url, **kwargs)

    async def async_patch(self, url: str, **kwargs: Any) -> ApiResponse[Any]:
        service = kwargs.pop("service", "default")
        return await self.get_client(service).async_patch(url, **kwargs)


# Global singleton instance and factory
http = _GlobalHttpProxy()
get_client = http.get_client
CourierClient = HttpClient

# Register atexit shutdown hook for zero socket leaks
atexit.register(http.close_all)
