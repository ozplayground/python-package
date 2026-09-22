"""Tests for ApiResponse[T], ApiError, and Result pattern."""
import pytest
from pydantic import BaseModel, Field

from courier.exceptions import (
    ApiCallError,
    ApiClientError,
    CourierError,
    DtoValidationError,
    HttpAutoconfigError,
)
from courier.response import ApiError, ApiResponse


class SampleUserDto(BaseModel):
    id: int
    name: str
    email: str = Field(default="user@example.com")


class TestApiResponseNormalCases:
    """Normal success cases for ApiResponse[T]."""

    def test_successful_response_attributes(self):
        resp = ApiResponse[dict](
            status_code=200,
            is_success=True,
            data={"id": 1, "name": "Alice"},
            headers={"content-type": "application/json"},
            duration_ms=45.2,
            request_url="https://api.example.com/users/1",
        )
        assert resp.status_code == 200
        assert resp.is_success is True
        assert resp.data == {"id": 1, "name": "Alice"}
        assert resp.error is None
        assert resp.duration_ms == 45.2
        assert resp.request_url == "https://api.example.com/users/1"

    def test_unwrap_success(self):
        resp = ApiResponse[dict](
            status_code=200,
            is_success=True,
            data={"id": 1, "name": "Alice"},
        )
        assert resp.unwrap() == {"id": 1, "name": "Alice"}

    def test_unwrap_or_success(self):
        resp = ApiResponse[dict](
            status_code=200,
            is_success=True,
            data={"id": 1, "name": "Alice"},
        )
        assert resp.unwrap_or({"id": 0, "name": "Guest"}) == {"id": 1, "name": "Alice"}

    def test_into_pydantic_model_success(self):
        resp = ApiResponse[dict](
            status_code=200,
            is_success=True,
            data={"id": 10, "name": "Bob", "email": "bob@example.com"},
        )
        dto = resp.into(SampleUserDto)
        assert isinstance(dto, SampleUserDto)
        assert dto.id == 10
        assert dto.name == "Bob"
        assert dto.email == "bob@example.com"

    def test_map_success(self):
        resp = ApiResponse[dict](
            status_code=200,
            is_success=True,
            data={"id": 1, "name": "Alice"},
        )
        mapped = resp.map(lambda d: d["name"].upper())
        assert mapped.is_success is True
        assert mapped.data == "ALICE"
        assert mapped.status_code == 200


class TestApiResponseBoundaryCases:
    """Boundary cases for ApiResponse[T]."""

    def test_204_no_content_response(self):
        resp = ApiResponse[None](
            status_code=204,
            is_success=True,
            data=None,
        )
        assert resp.is_success is True
        assert resp.unwrap() is None
        assert resp.unwrap_or("fallback") is None

    def test_map_with_none_data(self):
        resp = ApiResponse[None](
            status_code=200,
            is_success=True,
            data=None,
        )
        mapped = resp.map(lambda x: "transformed")
        assert mapped.is_success is True
        assert mapped.data is None


class TestApiResponseErrorCases:
    """Error cases and Result pattern failure handling."""

    def test_unwrap_failure_raises_api_call_error(self):
        err = ApiError(
            code="ERR_HTTP_404",
            message="User not found",
            details={"user_id": 999},
            is_retryable=False,
        )
        resp = ApiResponse[dict](
            status_code=404,
            is_success=False,
            data=None,
            error=err,
            request_url="https://api.example.com/users/999",
        )
        with pytest.raises(ApiCallError) as exc_info:
            resp.unwrap()

        e = exc_info.value
        assert isinstance(e, HttpAutoconfigError)
        assert e.status_code == 404
        assert e.error is not None
        assert e.error.code == "ERR_HTTP_404"
        assert e.request_url == "https://api.example.com/users/999"
        assert "User not found" in str(e)

    def test_unwrap_or_failure_returns_default(self):
        resp = ApiResponse[dict](
            status_code=500,
            is_success=False,
            error=ApiError(code="ERR_SERVER", message="Internal error"),
        )
        default_val = {"id": 0, "name": "Default"}
        assert resp.unwrap_or(default_val) == default_val

    def test_into_when_response_failed_raises_dto_validation_error(self):
        resp = ApiResponse[dict](
            status_code=500,
            is_success=False,
            error=ApiError(code="ERR_SERVER", message="Internal error"),
            raw_text='{"error": "server crash"}',
        )
        with pytest.raises(DtoValidationError) as exc_info:
            resp.into(SampleUserDto)
        assert "Cannot convert failed response" in str(exc_info.value)
        assert exc_info.value.target_cls is SampleUserDto

    def test_into_when_schema_mismatch_raises_dto_validation_error(self):
        resp = ApiResponse[dict](
            status_code=200,
            is_success=True,
            data={"invalid_key": 123},  # missing required 'id' and 'name'
            raw_text='{"invalid_key": 123}',
        )
        with pytest.raises(DtoValidationError) as exc_info:
            resp.into(SampleUserDto)
        assert exc_info.value.target_cls is SampleUserDto
        assert len(exc_info.value.validation_errors) > 0

    def test_into_when_data_is_non_dict_raises_dto_validation_error(self):
        resp = ApiResponse[str](
            status_code=200,
            is_success=True,
            data="plain text response",
            raw_text="plain text response",
        )
        with pytest.raises(DtoValidationError) as exc_info:
            resp.into(SampleUserDto)
        assert exc_info.value.target_cls is SampleUserDto
        assert "plain text response" in str(exc_info.value)

    def test_map_on_failure_retains_error(self):
        err = ApiError(code="ERR_403", message="Forbidden")
        resp = ApiResponse[dict](
            status_code=403,
            is_success=False,
            error=err,
        )
        mapped = resp.map(lambda d: d["something"])
        assert mapped.is_success is False
        assert mapped.status_code == 403
        assert mapped.error == err
        assert mapped.data is None

    def test_domain_exception_instantiation(self):
        from courier.exceptions import ApiTimeoutError, ApiConnectionError, ConfigurationValidationError, CourierError

        to_err = ApiTimeoutError(timeout_type="connect", request_url="https://timeout.com")
        assert to_err.status_code == 0
        assert to_err.timeout_type == "connect"
        assert "connect" in str(to_err)

        conn_err = ApiConnectionError(target_url="https://refused.com")
        assert conn_err.status_code == 0
        assert conn_err.target_url == "https://refused.com"

        cfg_err = ConfigurationValidationError("pool_size", "Invalid pool size")
        assert cfg_err.config_key == "pool_size"
        assert "Invalid pool size" in str(cfg_err)
