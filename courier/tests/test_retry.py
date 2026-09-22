"""Tests for RetryEngine, exponential backoff, and full jitter."""
import asyncio
import email.utils
import ssl
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock
import httpx
import pytest

from courier.config import RetryConfig
from courier.retry import RetryEngine


class TestRetryEngineSync:
    """Synchronous retry execution tests."""

    def test_success_first_attempt(self):
        cfg = RetryConfig(max_retries=3)
        engine = RetryEngine(cfg)

        mock_call = MagicMock(return_value=httpx.Response(200, json={"ok": True}))
        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        assert mock_call.call_count == 1
        assert resp is not None
        assert resp.status_code == 200
        assert exc is None
        assert duration >= 0.0

    def test_retry_on_503_then_success(self, monkeypatch):
        cfg = RetryConfig(max_retries=3, backoff_factor=0.01)
        engine = RetryEngine(cfg)

        # Mock time.sleep to avoid slow tests
        sleep_mock = MagicMock()
        monkeypatch.setattr(time, "sleep", sleep_mock)

        responses = [
            httpx.Response(503, text="Service Unavailable"),
            httpx.Response(200, json={"ok": True}),
        ]
        mock_call = MagicMock(side_effect=responses)

        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        assert mock_call.call_count == 2
        assert resp is not None
        assert resp.status_code == 200
        assert exc is None
        assert sleep_mock.call_count == 1

    def test_retry_exhaustion_on_504(self, monkeypatch):
        cfg = RetryConfig(max_retries=2, backoff_factor=0.01)
        engine = RetryEngine(cfg)

        monkeypatch.setattr(time, "sleep", MagicMock())

        mock_call = MagicMock(return_value=httpx.Response(504, text="Gateway Timeout"))
        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        # 1 initial + 2 retries = 3 calls
        assert mock_call.call_count == 3
        assert resp is not None
        assert resp.status_code == 504
        assert exc is None

    def test_retry_on_connect_timeout_then_success(self, monkeypatch):
        cfg = RetryConfig(max_retries=2, backoff_factor=0.01)
        engine = RetryEngine(cfg)

        monkeypatch.setattr(time, "sleep", MagicMock())

        mock_call = MagicMock(
            side_effect=[
                httpx.ConnectTimeout("Connection timed out"),
                httpx.Response(200, json={"data": "ok"}),
            ]
        )
        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        assert mock_call.call_count == 2
        assert resp is not None
        assert resp.status_code == 200
        assert exc is None

    def test_non_retryable_status_code_no_retry(self):
        cfg = RetryConfig(max_retries=3)
        engine = RetryEngine(cfg)

        mock_call = MagicMock(return_value=httpx.Response(404, text="Not Found"))
        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        assert mock_call.call_count == 1
        assert resp is not None
        assert resp.status_code == 404
        assert exc is None

    def test_non_idempotent_request_does_not_retry_by_default(self):
        cfg = RetryConfig(max_retries=3, retry_on_post=False)
        engine = RetryEngine(cfg)

        mock_call = MagicMock(return_value=httpx.Response(503, text="Unavailable"))
        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=False)

        # Only 1 call because POST/PATCH is non-idempotent
        assert mock_call.call_count == 1
        assert resp is not None
        assert resp.status_code == 503

    def test_non_idempotent_request_retries_when_configured(self, monkeypatch):
        cfg = RetryConfig(max_retries=2, retry_on_post=True, backoff_factor=0.01)
        engine = RetryEngine(cfg)

        monkeypatch.setattr(time, "sleep", MagicMock())

        mock_call = MagicMock(
            side_effect=[
                httpx.Response(503, text="Unavailable"),
                httpx.Response(200, json={"id": 1}),
            ]
        )
        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=False)

        assert mock_call.call_count == 2
        assert resp.status_code == 200

    def test_ssl_error_not_retried(self):
        cfg = RetryConfig(max_retries=3)
        engine = RetryEngine(cfg)

        ssl_err = ssl.SSLError("Certificate verification failed")
        mock_call = MagicMock(side_effect=ssl_err)

        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        assert mock_call.call_count == 1
        assert resp is None
        assert exc is ssl_err

    def test_retry_after_header_parsing(self, monkeypatch):
        cfg = RetryConfig(max_retries=2, backoff_factor=0.01, respect_retry_after=True)
        engine = RetryEngine(cfg)

        sleep_mock = MagicMock()
        monkeypatch.setattr(time, "sleep", sleep_mock)

        resp_429 = httpx.Response(429, headers={"Retry-After": "5"})
        resp_200 = httpx.Response(200, json={"ok": True})
        mock_call = MagicMock(side_effect=[resp_429, resp_200])

        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        assert mock_call.call_count == 2
        assert resp.status_code == 200
        # sleep was called with at least 5 seconds
        assert sleep_mock.call_args[0][0] >= 5.0

    def test_retry_after_http_date_parsing(self):
        cfg = RetryConfig(max_retries=2)
        engine = RetryEngine(cfg)

        # Future date
        future_dt = datetime.now(timezone.utc).timestamp() + 15
        date_str = email.utils.formatdate(future_dt, usegmt=True)

        parsed = engine._parse_retry_after({"Retry-After": date_str})
        assert parsed is not None
        assert 10 <= parsed <= 20

    def test_retry_after_exceeds_max_backoff_aborts_retry(self):
        cfg = RetryConfig(max_retries=3, max_backoff_seconds=30.0)
        engine = RetryEngine(cfg)

        # Retry-After is 60 seconds, which exceeds max_backoff_seconds (30.0)
        resp_429 = httpx.Response(429, headers={"Retry-After": "60"})
        mock_call = MagicMock(return_value=resp_429)

        resp, exc, duration = engine.execute_sync(mock_call, is_idempotent=True)

        # Should abort immediately and not sleep or retry
        assert mock_call.call_count == 1
        assert resp.status_code == 429


class TestRetryEngineAsync:
    """Asynchronous retry execution tests."""

    @pytest.mark.asyncio
    async def test_async_success_first_attempt(self):
        cfg = RetryConfig(max_retries=3)
        engine = RetryEngine(cfg)

        async def mock_call():
            return httpx.Response(200, json={"async": True})

        resp, exc, duration = await engine.execute_async(mock_call, is_idempotent=True)
        assert resp is not None
        assert resp.status_code == 200
        assert exc is None

    @pytest.mark.asyncio
    async def test_async_retry_on_502_then_success(self, monkeypatch):
        cfg = RetryConfig(max_retries=2, backoff_factor=0.01)
        engine = RetryEngine(cfg)

        sleep_mock = MagicMock()

        async def fake_sleep(secs):
            sleep_mock(secs)

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        calls = [
            httpx.Response(502, text="Bad Gateway"),
            httpx.Response(200, json={"ok": True}),
        ]

        async def mock_call():
            return calls.pop(0)

        resp, exc, duration = await engine.execute_async(mock_call, is_idempotent=True)
        assert resp.status_code == 200
        assert sleep_mock.call_count == 1

    @pytest.mark.asyncio
    async def test_async_retry_exhaustion_on_network_error(self, monkeypatch):
        cfg = RetryConfig(max_retries=2, backoff_factor=0.01)
        engine = RetryEngine(cfg)

        async def fake_sleep(_):
            pass

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        call_count = 0

        async def mock_call():
            nonlocal call_count
            call_count += 1
            raise httpx.ReadTimeout("Read timed out")

        resp, exc, duration = await engine.execute_async(mock_call, is_idempotent=True)
        assert call_count == 3
        assert resp is None
        assert isinstance(exc, httpx.ReadTimeout)
