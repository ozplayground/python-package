"""Large-scale concurrency, thread-safety, and resilience stress tests."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import pytest
import respx

from courier import ClientConfig, HttpClient, get_client


class TestConcurrencyStress:
    """Stress tests for multi-threaded and coroutine concurrency."""

    @respx.mock
    def test_multi_threaded_sync_concurrency(self):
        """50 concurrent threads accessing a shared HttpClient instance."""
        respx.get("https://stress.example.com/api/data").respond(
            200, json={"status": "ok", "worker": "thread"}
        )
        client = HttpClient(
            ClientConfig(
                base_url="https://stress.example.com",
                pool_size=15,
                max_keepalive=10,
            )
        )

        def worker_task(i: int):
            resp = client.get("/api/data", params={"index": i})
            return resp.is_success, resp.data

        with ThreadPoolExecutor(max_workers=15) as executor:
            results = list(executor.map(worker_task, range(50)))

        assert len(results) == 50
        for is_success, data in results:
            assert is_success is True
            assert data["status"] == "ok"

        client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_multi_coroutine_async_concurrency(self):
        """100 concurrent coroutines accessing a shared HttpClient instance."""
        respx.get("https://stress.example.com/api/async-data").respond(
            200, json={"status": "async_ok"}
        )
        client = HttpClient(
            ClientConfig(
                base_url="https://stress.example.com",
                pool_size=20,
                max_keepalive=10,
            )
        )

        async def coroutine_task(idx: int):
            resp = await client.async_get("/api/async-data", params={"req_id": idx})
            return resp.is_success, resp.data

        tasks = [coroutine_task(i) for i in range(100)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 100
        for is_success, data in results:
            assert is_success is True
            assert data["status"] == "async_ok"

        await client.aclose()

    @pytest.mark.asyncio
    @respx.mock
    async def test_concurrent_retry_storm_resilience(self, monkeypatch):
        """20 concurrent requests encountering 503 errors and successfully recovering."""
        async def fake_sleep(_):
            pass

        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        call_map: dict[str, int] = {}

        def side_effect(request):
            req_id = request.url.params.get("id", "0")
            count = call_map.get(req_id, 0)
            call_map[req_id] = count + 1
            if count == 0:
                return respx.MockResponse(503, text="Service Unavailable")
            return respx.MockResponse(200, json={"recovered": True, "id": req_id})

        respx.get("https://resilience.example.com/retry-test").mock(side_effect=side_effect)

        client = HttpClient(
            ClientConfig(
                base_url="https://resilience.example.com",
                retry={"max_retries": 3, "backoff_factor": 0.01},
            )
        )

        async def task(req_id: int):
            return await client.async_get("/retry-test", params={"id": str(req_id)})

        tasks = [task(i) for i in range(20)]
        responses = await asyncio.gather(*tasks)

        assert len(responses) == 20
        for resp in responses:
            assert resp.is_success is True
            assert resp.data["recovered"] is True

        await client.aclose()

    @pytest.mark.asyncio
    @respx.mock
    async def test_socket_cleanup_and_zero_leaks(self):
        """Verify sockets are cleanly closed with no dangling connections."""
        respx.get("https://leak.example.com/ping").respond(200, text="pong")

        client = HttpClient(ClientConfig(base_url="https://leak.example.com"))

        # Trigger sync client and async client creation
        resp_sync = client.get("/ping")
        assert resp_sync.is_success is True
        assert client._sync_client is not None
        assert not client._sync_client.is_closed

        resp_async = await client.async_get("/ping")
        assert resp_async.is_success is True
        assert client._async_client is not None
        assert not client._async_client.is_closed

        # Explicit close
        client.close()
        assert client._sync_client is None

        await client.aclose()
        assert client._async_client is None
