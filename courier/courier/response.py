"""Unified ApiResponse[T], ApiError models and Result pattern implementation."""
from typing import Any, Callable, Generic, Mapping, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from courier.exceptions import ApiCallError, DtoValidationError

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)
U = TypeVar("U")


class ApiError(BaseModel):
    """Encapsulates detailed error information from a failed HTTP request."""

    code: str
    message: str
    details: Optional[dict[str, Any]] = None
    retry_after: Optional[float] = None
    is_retryable: bool = False

    model_config = ConfigDict(frozen=True)


class ApiResponse(BaseModel, Generic[T]):
    """Unified immutable generic response container supporting Result patterns."""

    status_code: int
    is_success: bool
    data: Optional[T] = None
    error: Optional[ApiError] = None
    duration_ms: float = 0.0
    headers: Mapping[str, str] = Field(default_factory=dict)
    raw_text: Optional[str] = None
    request_url: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    def unwrap(self) -> T:
        """Return data if successful, otherwise raise ApiCallError."""
        if not self.is_success:
            raise ApiCallError(
                status_code=self.status_code,
                error=self.error,
                request_url=self.request_url,
                message=self.error.message if self.error else None,
            )
        return self.data  # type: ignore

    def unwrap_or(self, default: T) -> T:
        """Return data if successful, otherwise return the provided default value."""
        if not self.is_success:
            return default
        return self.data  # type: ignore

    def into(self, target_cls: type[M]) -> M:
        """Validate and deserialize data into the given Pydantic BaseModel class."""
        if not self.is_success:
            raw_snippet = (
                (self.raw_text[:200] + "...")
                if self.raw_text and len(self.raw_text) > 200
                else (self.raw_text or "")
            )
            raise DtoValidationError(
                target_cls=target_cls,
                validation_errors=[self.error.model_dump()] if self.error else [],
                message=(
                    f"Cannot convert failed response (status {self.status_code}) "
                    f"into {target_cls.__name__}. Raw snippet: {raw_snippet}"
                ),
            )
        if isinstance(self.data, target_cls):
            return self.data
        if not isinstance(self.data, (dict, list)):
            raw_snippet = (
                (self.raw_text[:200] + "...")
                if self.raw_text and len(self.raw_text) > 200
                else str(self.data)
            )
            raise DtoValidationError(
                target_cls=target_cls,
                validation_errors=["Data is not a dict or list, cannot validate into Pydantic model."],
                message=f"Data is not a dict or list, cannot validate into {target_cls.__name__}. Received: {raw_snippet}",
            )
        try:
            return target_cls.model_validate(self.data)
        except ValidationError as e:
            raise DtoValidationError(
                target_cls=target_cls,
                validation_errors=e.errors(),
                message=f"Validation failed for {target_cls.__name__}: {e.errors()}",
            ) from e

    def map(self, transform: Callable[[T], U]) -> "ApiResponse[U]":
        """Apply a transform function to data if successful."""
        if not self.is_success:
            return ApiResponse[U](
                status_code=self.status_code,
                is_success=False,
                data=None,
                error=self.error,
                duration_ms=self.duration_ms,
                headers=self.headers,
                raw_text=self.raw_text,
                request_url=self.request_url,
            )
        new_data = transform(self.data) if self.data is not None else None
        return ApiResponse[U](
            status_code=self.status_code,
            is_success=True,
            data=new_data,
            error=None,
            duration_ms=self.duration_ms,
            headers=self.headers,
            raw_text=self.raw_text,
            request_url=self.request_url,
        )
