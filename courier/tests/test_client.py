"""Tests for HttpClient, _GlobalHttpProxy, connection pooling, and lifecycle management."""
import asyncio
import httpx
import pytest
import respx
from pydantic import BaseModel

from courier import http, get_client, HttpClient, ClientConfig, ApiResponse, CourierClient


class ItemPayload(BaseModel):
    name: str
    price: float


class TestHttpClientSync:
    """Synchronous HTTP client operations."""

    @respx.mock
    def test_sync_get_success(self):
        respx.get("https://api.example.com/items/1").respond(
            200, json={"id": 1, "name": "Keyboard"}
        )
        client = HttpClient(ClientConfig(base_url="https://api.example.com"))
        resp = client.get("/items/1")

        assert resp.is_success is True
        assert resp.status_code == 200
        assert resp.data == {"id": 1, "name": "Keyboard"}
        assert resp.duration_ms > 0
        client.close()

    @respx.mock
    def test_sync_post_with_pydantic_payload(self):
        route = respx.post("https://api.example.com/items").respond(
            201, json={"id": 101, "name": "Mouse", "price": 25.5}
        )
        client = HttpClient(ClientConfig(base_url="https://api.example.com"))
        payload = ItemPayload(name="Mouse", price=25.5)
        resp = client.post("/items", json=payload)

        assert resp.is_success is True
        assert resp.status_code == 201
        assert resp.data["id"] == 101
        assert route.called
        assert route.calls.last.request.content == b'{"name":"Mouse","price":25.5}'
        client.close()

    @respx.mock
    def test_sync_get_404_error(self):
        respx.get("https://api.example.com/items/999").respond(
            404, json={"message": "Item not found"}
        )
        client = HttpClient(ClientConfig(base_url="https://api.example.com"))
        resp = client.get("/items/999")

        assert resp.is_success is False
        assert resp.status_code == 404
        assert resp.error is not None
        assert resp.error.code == "ERR_HTTP_404"
        assert resp.error.message == "Item not found"
        client.close()

    @respx.mock
    def test_sync_connect_timeout_maps_to_api_response(self):
        respx.get("https://api.example.com/timeout").mock(
            side_effect=httpx.ConnectTimeout("Connect timeout")
        )
        # max_retries=0 to test immediate error mapping
        client = HttpClient(
            ClientConfig(
                base_url="https://api.example.com",
                retry={"max_retries": 0},
            )
        )
        resp = client.get("/timeout")

        assert resp.is_success is False
        assert resp.status_code == 0
        assert resp.error is not None
        assert resp.error.code == "ERR_ENG_TIMEOUT"
        client.close()

    @respx.mock
    def test_sync_connect_error_maps_to_api_response(self):
        respx.get("https://api.example.com/refused").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        client = HttpClient(
            ClientConfig(
                base_url="https://api.example.com",
                retry={"max_retries": 0},
            )
        )
        resp = client.get("/refused")

        assert resp.is_success is False
        assert resp.status_code == 0
        assert resp.error is not None
        assert resp.error.code == "ERR_ENG_CONNECT_FAILED"
        client.close()


class TestHttpClientAsync:
    """Asynchronous HTTP client operations."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_get_success(self):
        respx.get("https://api.async.com/users").respond(
            200, json=[{"id": 1, "username": "admin"}]
        )
        client = HttpClient(ClientConfig(base_url="https://api.async.com"))
        resp = await client.async_get("/users")

        assert resp.is_success is True
        assert resp.status_code == 200
        assert resp.data == [{"id": 1, "username": "admin"}]
        await client.aclose()

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_post_success(self):
        respx.post("https://api.async.com/users").respond(
            201, json={"status": "created"}
        )
        client = HttpClient(ClientConfig(base_url="https://api.async.com"))
        resp = await client.async_post("/users", json={"username": "newuser"})

        assert resp.is_success is True
        assert resp.status_code == 201
        await client.aclose()

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_event_loop_recreation_safety(self):
        """Verify client re-creates AsyncClient if running in a new event loop."""
        respx.get("https://api.async.com/ping").respond(200, json={"pong": True})
        client = HttpClient(ClientConfig(base_url="https://api.async.com"))

        # First call on current loop
        resp1 = await client.async_get("/ping")
        assert resp1.status_code == 200

        # Simulate loop transition by modifying client._loop to an already-closed fake loop
        closed_loop = asyncio.new_event_loop()
        closed_loop.close()
        client._loop = closed_loop

        # Should transparently recreate async client and succeed without 'loop is closed' error
        resp2 = await client.async_get("/ping")
        assert resp2.status_code == 200
        await client.aclose()


class TestHttpClientBufferSafety:
    """Buffer safety and response truncation tests."""

    @respx.mock
    def test_response_body_exceeding_1mb_is_truncated(self):
        large_content = "A" * (1024 * 1024 + 500)  # > 1MB
        respx.get("https://api.example.com/large").respond(
            200, text=large_content, headers={"Content-Type": "text/plain"}
        )
        client = HttpClient(ClientConfig(base_url="https://api.example.com"))
        resp = client.get("/large")

        assert resp.is_success is True
        assert resp.raw_text is not None
        assert "[TRUNCATED: Response body exceeded 1MB]" in resp.raw_text
        assert len(resp.raw_text) <= 1024 * 1024 + 100
        client.close()


class TestGlobalHttpProxy:
    """Tests for the global singleton proxy and get_client factory."""

    @respx.mock
    def test_global_http_get_and_post(self):
        respx.get("https://global.example.com/status").respond(200, json={"status": "ok"})
        respx.post("https://global.example.com/submit").respond(200, json={"submitted": True})

        r1 = http.get("https://global.example.com/status")
        assert r1.is_success is True
        assert r1.data == {"status": "ok"}

        r2 = http.post("https://global.example.com/submit", json={"data": 123})
        assert r2.is_success is True
        assert r2.data == {"submitted": True}

    def test_get_client_caching(self):
        c1 = get_client("analytics")
        c2 = get_client("analytics")
        assert c1 is c2

    def test_get_client_with_override_creates_distinct_or_updated(self):
        c1 = get_client("service_a", timeout=5.0)
        assert c1.config.timeout == 5.0

    def test_close_all(self):
        c1 = get_client("test_close_1")
        c2 = get_client("test_close_2")
        # should close cleanly without exceptions
        http.close_all()

    @pytest.mark.asyncio
    async def test_aclose_all(self):
        c1 = get_client("test_aclose_1")
        await http.aclose_all()

    @respx.mock
    def test_all_sync_methods(self):
        respx.put("https://api.example.com/put").respond(200, json={"p": 1})
        respx.delete("https://api.example.com/del").respond(204)
        respx.patch("https://api.example.com/patch").respond(200, json={"patch": True})

        client = HttpClient(ClientConfig(base_url="https://api.example.com"))
        assert client.put("/put").is_success is True
        assert client.delete("/del").is_success is True
        assert client.patch("/patch").is_success is True
        client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_all_async_methods(self):
        respx.put("https://api.async.com/put").respond(200, json={"p": 1})
        respx.delete("https://api.async.com/del").respond(204)
        respx.patch("https://api.async.com/patch").respond(200, json={"patch": True})

        client = HttpClient(ClientConfig(base_url="https://api.async.com"))
        r1 = await client.async_put("/put")
        r2 = await client.async_delete("/del")
        r3 = await client.async_patch("/patch")
        assert r1.is_success is True
        assert r2.is_success is True
        assert r3.is_success is True
        await client.aclose()

    @pytest.mark.asyncio
    @respx.mock
    async def test_all_proxy_methods(self):
        respx.put("https://proxy.example.com/put").respond(200, json={"ok": True})
        respx.delete("https://proxy.example.com/del").respond(204)
        respx.patch("https://proxy.example.com/patch").respond(200, json={"ok": True})
        respx.get("https://proxy.example.com/async-get").respond(200, json={"ok": True})
        respx.post("https://proxy.example.com/async-post").respond(201, json={"ok": True})
        respx.put("https://proxy.example.com/async-put").respond(200, json={"ok": True})
        respx.delete("https://proxy.example.com/async-del").respond(204)
        respx.patch("https://proxy.example.com/async-patch").respond(200, json={"ok": True})

        assert http.put("https://proxy.example.com/put").is_success is True
        assert http.delete("https://proxy.example.com/del").is_success is True
        assert http.patch("https://proxy.example.com/patch").is_success is True

        assert (await http.async_get("https://proxy.example.com/async-get")).is_success is True
        assert (await http.async_post("https://proxy.example.com/async-post")).is_success is True
        assert (await http.async_put("https://proxy.example.com/async-put")).is_success is True
        assert (await http.async_delete("https://proxy.example.com/async-del")).is_success is True
        assert (await http.async_patch("https://proxy.example.com/async-patch")).is_success is True
