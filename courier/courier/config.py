"""Configuration models and hierarchical config loader for http-autoconfig."""
import json
import os
import random
import ssl
import threading
from typing import Any, Optional
import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from courier.exceptions import ConfigurationValidationError


class RetryConfig(BaseModel):
    """Configuration for smart exponential backoff and jitter retries."""

    max_retries: int = Field(default=3, ge=0)
    backoff_factor: float = Field(default=0.5, ge=0.0)
    max_backoff_seconds: float = Field(default=30.0, ge=0.0)
    retry_status_codes: list[int] = Field(default_factory=lambda: [429, 502, 503, 504])
    retry_on_post: bool = False
    respect_retry_after: bool = True
    jitter_type: str = "full"

    model_config = ConfigDict(frozen=True)

    def calculate_wait_time(self, attempt: int, retry_after: Optional[float] = None) -> float:
        """Calculate wait time using exponential backoff with full jitter and Retry-After clamping."""
        # T_exp = min(max_backoff_seconds, backoff_factor * 2^attempt)
        exp_backoff = min(self.max_backoff_seconds, self.backoff_factor * (2**attempt))

        if self.jitter_type == "full":
            wait_time = random.uniform(0, exp_backoff)
        else:
            wait_time = exp_backoff

        if self.respect_retry_after and retry_after is not None:
            wait_time = max(wait_time, retry_after)

        return min(wait_time, self.max_backoff_seconds)

    def is_retryable_status(self, status_code: int) -> bool:
        """Check if HTTP status code is retryable."""
        return status_code in self.retry_status_codes

    def is_retryable_exception(self, exc: Exception) -> bool:
        """Check if exception is a transient network error and not a security/SSL error."""
        if isinstance(exc, ssl.SSLError):
            return False

        # Inspect nested causes
        cur: Optional[BaseException] = exc
        while cur is not None:
            if isinstance(cur, ssl.SSLError):
                return False
            cur = cur.__cause__ or cur.__context__

        return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError))


class ClientConfig(BaseModel):
    """Configuration schema for HTTP clients with pooling and timeouts."""

    service_name: str = "default"
    base_url: str = ""
    timeout: float = Field(default=10.0, gt=0.0)
    connect_timeout: float = Field(default=3.0, gt=0.0)
    read_timeout: float = Field(default=10.0, gt=0.0)
    write_timeout: float = Field(default=10.0, gt=0.0)
    pool_timeout: float = Field(default=5.0, gt=0.0)
    pool_size: int = Field(default=20, gt=0)
    max_keepalive: int = Field(default=10, ge=0)
    keepalive_expiry: float = Field(default=30.0, gt=0.0)
    headers: dict[str, str] = Field(default_factory=dict)
    retry: RetryConfig = Field(default_factory=RetryConfig)

    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_config(self) -> "ClientConfig":
        """Validate URL scheme and format."""
        if self.base_url:
            clean_url = self.base_url.strip()
            if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
                raise ConfigurationValidationError(
                    "base_url",
                    f"Invalid base_url '{self.base_url}'. Must start with 'http://' or 'https://'.",
                )
        return self

    def to_httpx_limits(self) -> httpx.Limits:
        """Convert to httpx.Limits instance."""
        return httpx.Limits(
            max_connections=self.pool_size,
            max_keepalive_connections=self.max_keepalive,
            keepalive_expiry=self.keepalive_expiry,
        )

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Convert to httpx.Timeout instance."""
        return httpx.Timeout(
            timeout=self.timeout,
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.write_timeout,
            pool=self.pool_timeout,
        )


class ConfigLoader:
    """Hierarchical configuration loader with 5-level precedence and deep merge."""

    _cache: dict[str, ClientConfig] = {}
    _lock: threading.Lock = threading.Lock()
    _config_dirs: list[str] = [".", "config"]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cached ClientConfig instances."""
        with cls._lock:
            cls._cache.clear()

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def _load_from_json(cls, service_name: str) -> dict[str, Any]:
        """Load service configuration from JSON files."""
        candidates = ["courier.json", "api_client.json", "http_clients.json", "config.json"]
        for directory in cls._config_dirs:
            for filename in candidates:
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict) and service_name in data:
                                return data[service_name]
                    except Exception:
                        pass
        return {}

    @classmethod
    def _load_from_yaml(cls, service_name: str) -> dict[str, Any]:
        """Load service configuration from YAML files."""
        candidates = [
            "courier.yaml",
            "courier.yml",
            "api_client.yaml",
            "api_client.yml",
            "http_clients.yaml",
            "http_clients.yml",
            "config.yaml",
            "config.yml",
        ]
        for directory in cls._config_dirs:
            for filename in candidates:
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                            if isinstance(data, dict) and service_name in data:
                                return data[service_name]
                    except Exception:
                        pass
        return {}

    @classmethod
    def _parse_env_val(cls, val: str) -> Any:
        """Parse primitive values from environment strings."""
        val_lower = val.lower()
        if val_lower in ("true", "1", "yes"):
            return True
        if val_lower in ("false", "0", "no"):
            return False
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val

    @classmethod
    def _load_from_env(cls, service_name: str) -> dict[str, Any]:
        """Load service configuration from environment variables."""
        prefix = f"HTTP_CLIENT_{service_name.upper()}_"
        result: dict[str, Any] = {}

        for env_key, env_val in os.environ.items():
            if env_key.startswith(prefix):
                key_name = env_key[len(prefix) :].lower()
                parsed_val = cls._parse_env_val(env_val)

                if key_name.startswith("retry_"):
                    retry_key = key_name[6:]
                    if "retry" not in result:
                        result["retry"] = {}
                    result["retry"][retry_key] = parsed_val
                else:
                    result[key_name] = parsed_val
        return result

    @classmethod
    def load(cls, service_name: str = "default", **kwargs: Any) -> ClientConfig:
        """Load ClientConfig using 5-level precedence: kwargs > ENV > YAML > JSON > Defaults."""
        # If no kwargs override and already cached, return immediately
        if not kwargs:
            with cls._lock:
                if service_name in cls._cache:
                    return cls._cache[service_name]

        # 1. Defaults
        config_dict: dict[str, Any] = {"service_name": service_name}

        # 2. JSON
        json_data = cls._load_from_json(service_name)
        config_dict = cls._deep_merge(config_dict, json_data)

        # 3. YAML
        yaml_data = cls._load_from_yaml(service_name)
        config_dict = cls._deep_merge(config_dict, yaml_data)

        # 4. ENV
        env_data = cls._load_from_env(service_name)
        config_dict = cls._deep_merge(config_dict, env_data)

        # 5. kwargs
        config_dict = cls._deep_merge(config_dict, kwargs)

        client_config = ClientConfig(**config_dict)

        if not kwargs:
            with cls._lock:
                cls._cache[service_name] = client_config

        return client_config
