"""Tests for ClientConfig, RetryConfig, and ConfigLoader."""
import json
import os
import ssl
import tempfile
import httpx
import pytest
from pydantic import ValidationError

from courier.config import ClientConfig, ConfigLoader, RetryConfig
from courier.exceptions import ConfigurationValidationError


class TestRetryConfig:
    """Tests for RetryConfig model and methods."""

    def test_default_retry_config(self):
        cfg = RetryConfig()
        assert cfg.max_retries == 3
        assert cfg.backoff_factor == 0.5
        assert cfg.max_backoff_seconds == 30.0
        assert cfg.retry_status_codes == [429, 502, 503, 504]
        assert cfg.retry_on_post is False
        assert cfg.respect_retry_after is True
        assert cfg.jitter_type == "full"

    def test_calculate_wait_time_within_bounds(self):
        cfg = RetryConfig(backoff_factor=1.0, max_backoff_seconds=10.0)
        # For attempt 0: max exp = 1.0 * 2^0 = 1.0. Jitter in [0, 1.0]
        wait = cfg.calculate_wait_time(attempt=0)
        assert 0.0 <= wait <= 1.0

        # For attempt 3: max exp = 1.0 * 2^3 = 8.0. Jitter in [0, 8.0]
        wait = cfg.calculate_wait_time(attempt=3)
        assert 0.0 <= wait <= 8.0

        # For attempt 10: clamped to max_backoff_seconds = 10.0
        wait = cfg.calculate_wait_time(attempt=10)
        assert 0.0 <= wait <= 10.0

    def test_calculate_wait_time_with_retry_after(self):
        cfg = RetryConfig(backoff_factor=0.5, max_backoff_seconds=30.0)
        # If retry_after is 5.0, wait time should be at least 5.0
        wait = cfg.calculate_wait_time(attempt=0, retry_after=5.0)
        assert wait >= 5.0
        assert wait <= 30.0

    def test_calculate_wait_time_with_excessive_retry_after(self):
        cfg = RetryConfig(max_backoff_seconds=30.0)
        # If retry_after exceeds max_backoff_seconds (e.g. 60.0), clamped to max_backoff_seconds
        wait = cfg.calculate_wait_time(attempt=0, retry_after=60.0)
        assert wait == 30.0

    def test_is_retryable_status(self):
        cfg = RetryConfig()
        assert cfg.is_retryable_status(429) is True
        assert cfg.is_retryable_status(502) is True
        assert cfg.is_retryable_status(503) is True
        assert cfg.is_retryable_status(504) is True
        assert cfg.is_retryable_status(200) is False
        assert cfg.is_retryable_status(400) is False
        assert cfg.is_retryable_status(404) is False
        assert cfg.is_retryable_status(500) is False

    def test_is_retryable_exception(self):
        cfg = RetryConfig()
        assert cfg.is_retryable_exception(httpx.ConnectTimeout("timeout")) is True
        assert cfg.is_retryable_exception(httpx.ReadTimeout("timeout")) is True
        assert cfg.is_retryable_exception(httpx.ConnectError("refused")) is True
        # SSL errors must NOT be retryable
        assert cfg.is_retryable_exception(ssl.SSLError("cert expired")) is False
        assert cfg.is_retryable_exception(ValueError("some other error")) is False


class TestClientConfig:
    """Tests for ClientConfig model and conversions."""

    def test_default_client_config(self):
        cfg = ClientConfig()
        assert cfg.service_name == "default"
        assert cfg.base_url == ""
        assert cfg.timeout == 10.0
        assert cfg.connect_timeout == 3.0
        assert cfg.read_timeout == 10.0
        assert cfg.write_timeout == 10.0
        assert cfg.pool_timeout == 5.0
        assert cfg.pool_size == 20
        assert cfg.max_keepalive == 10
        assert cfg.keepalive_expiry == 30.0
        assert cfg.headers == {}
        assert isinstance(cfg.retry, RetryConfig)

    def test_to_httpx_limits(self):
        cfg = ClientConfig(pool_size=50, max_keepalive=25, keepalive_expiry=45.0)
        limits = cfg.to_httpx_limits()
        assert isinstance(limits, httpx.Limits)
        assert limits.max_connections == 50
        assert limits.max_keepalive_connections == 25
        assert limits.keepalive_expiry == 45.0

    def test_to_httpx_timeout(self):
        cfg = ClientConfig(
            timeout=12.0,
            connect_timeout=4.0,
            read_timeout=8.0,
            write_timeout=8.0,
            pool_timeout=6.0,
        )
        timeout = cfg.to_httpx_timeout()
        assert isinstance(timeout, httpx.Timeout)
        assert timeout.connect == 4.0
        assert timeout.read == 8.0
        assert timeout.write == 8.0
        assert timeout.pool == 6.0

    def test_valid_base_url(self):
        cfg1 = ClientConfig(base_url="https://api.example.com")
        assert cfg1.base_url == "https://api.example.com"
        cfg2 = ClientConfig(base_url="http://localhost:8080")
        assert cfg2.base_url == "http://localhost:8080"

    def test_invalid_base_url_raises_configuration_validation_error(self):
        with pytest.raises(ConfigurationValidationError) as exc_info:
            ClientConfig(base_url="ftp://ftp.example.com")
        assert "base_url" in str(exc_info.value)

        with pytest.raises(ConfigurationValidationError):
            ClientConfig(base_url="not-a-valid-url")

    def test_negative_timeout_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ClientConfig(timeout=-1.0)


class TestConfigLoader:
    """Tests for hierarchical ConfigLoader."""

    def setup_method(self):
        ConfigLoader.clear_cache()

    def test_load_default_config(self):
        cfg = ConfigLoader.load("default")
        assert cfg.service_name == "default"
        assert cfg.timeout == 10.0

    def test_load_with_kwargs_override(self):
        cfg = ConfigLoader.load(
            "payment",
            base_url="https://api.payments.com",
            timeout=5.0,
            retry={"max_retries": 5},
        )
        assert cfg.service_name == "payment"
        assert cfg.base_url == "https://api.payments.com"
        assert cfg.timeout == 5.0
        assert cfg.retry.max_retries == 5

    def test_load_with_env_override(self, monkeypatch):
        monkeypatch.setenv("HTTP_CLIENT_AUTH_BASE_URL", "https://auth.internal")
        monkeypatch.setenv("HTTP_CLIENT_AUTH_TIMEOUT", "7.5")
        monkeypatch.setenv("HTTP_CLIENT_AUTH_POOL_SIZE", "40")

        cfg = ConfigLoader.load("auth")
        assert cfg.base_url == "https://auth.internal"
        assert cfg.timeout == 7.5
        assert cfg.pool_size == 40

    def test_load_with_json_and_yaml_file(self, tmp_path, monkeypatch):
        # Create a temp yaml config
        yaml_content = """
payment:
  base_url: https://yaml.payments.com
  timeout: 8.0
  retry:
    max_retries: 4
"""
        yaml_file = tmp_path / "http_clients.yaml"
        yaml_file.write_text(yaml_content)

        # Create a temp json config
        json_content = {
            "auth": {
                "base_url": "https://json.auth.com",
                "timeout": 4.0
            }
        }
        json_file = tmp_path / "http_clients.json"
        json_file.write_text(json.dumps(json_content))

        # Let ConfigLoader search in tmp_path
        monkeypatch.setattr(ConfigLoader, "_config_dirs", [str(tmp_path)])

        cfg_yaml = ConfigLoader.load("payment")
        assert cfg_yaml.base_url == "https://yaml.payments.com"
        assert cfg_yaml.timeout == 8.0
        assert cfg_yaml.retry.max_retries == 4

        cfg_json = ConfigLoader.load("auth")
        assert cfg_json.base_url == "https://json.auth.com"
        assert cfg_json.timeout == 4.0

    def test_hierarchical_precedence(self, tmp_path, monkeypatch):
        # YAML has timeout 8.0
        yaml_content = """
order:
  base_url: https://yaml.order.com
  timeout: 8.0
"""
        (tmp_path / "http_clients.yaml").write_text(yaml_content)
        monkeypatch.setattr(ConfigLoader, "_config_dirs", [str(tmp_path)])

        # ENV overrides timeout to 12.0
        monkeypatch.setenv("HTTP_CLIENT_ORDER_TIMEOUT", "12.0")

        # kwargs overrides timeout to 20.0
        cfg = ConfigLoader.load("order", timeout=20.0)
        assert cfg.timeout == 20.0  # kwargs wins
        assert cfg.base_url == "https://yaml.order.com"  # inherited from YAML
