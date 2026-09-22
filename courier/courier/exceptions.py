"""Standard domain exception hierarchy for courier."""
from typing import Any, Optional


class CourierError(Exception):
    """Base exception for all courier errors."""

    def __init__(self, message: str = "An error occurred in courier") -> None:
        super().__init__(message)
        self.message = message


# Backwards compatibility aliases
ApiClientError = CourierError
HttpAutoconfigError = CourierError


class ApiCallError(CourierError):
    """Raised when an API call fails or unwrap() is called on a failed response."""

    def __init__(
        self,
        status_code: int,
        error: Optional[Any] = None,
        request_url: str = "",
        message: Optional[str] = None,
    ) -> None:
        msg = (
            message
            or (error.message if error and hasattr(error, "message") else f"API call failed with status {status_code}")
        )
        super().__init__(f"[{status_code}] {msg} (url: {request_url})")
        self.status_code = status_code
        self.error = error
        self.request_url = request_url


class ApiTimeoutError(ApiCallError):
    """Raised when an API request times out."""

    def __init__(
        self,
        timeout_type: str = "request",
        request_url: str = "",
        message: Optional[str] = None,
    ) -> None:
        super().__init__(
            status_code=0,
            request_url=request_url,
            message=message or f"Request timed out during {timeout_type}",
        )
        self.timeout_type = timeout_type


class ApiConnectionError(ApiCallError):
    """Raised when connection to target URL fails."""

    def __init__(
        self,
        target_url: str = "",
        message: Optional[str] = None,
    ) -> None:
        super().__init__(
            status_code=0,
            request_url=target_url,
            message=message or f"Failed to connect to {target_url}",
        )
        self.target_url = target_url


class DtoValidationError(CourierError):
    """Raised when deserialization into a Pydantic DTO fails."""

    def __init__(
        self,
        target_cls: type,
        validation_errors: list[Any],
        message: Optional[str] = None,
    ) -> None:
        msg = message or f"Failed to validate response into {target_cls.__name__}: {validation_errors}"
        super().__init__(msg)
        self.target_cls = target_cls
        self.validation_errors = validation_errors


class ConfigurationValidationError(CourierError):
    """Raised when client configuration is invalid."""

    def __init__(self, config_key: str, message: Optional[str] = None) -> None:
        super().__init__(message or f"Configuration validation failed for '{config_key}'")
        self.config_key = config_key
