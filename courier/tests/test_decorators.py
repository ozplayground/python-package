"""Tests for declarative API decorators (@api_client, @get, @post, etc.)."""
import pytest
import respx
from pydantic import BaseModel

from courier import ApiResponse
from courier.decorators import api_client, courier, courier_client, get, post, put, delete, patch


class CreateUserRequest(BaseModel):
    name: str
    email: str


@api_client(service="user_service", base_url="https://api.users.com")
class UserClient:
    @get("/users/{user_id}")
    def get_user(self, user_id: int) -> ApiResponse[dict]:
        ...

    @post("/users")
    def create_user(self, json: CreateUserRequest) -> ApiResponse[dict]:
        ...

    @put("/users/{user_id}")
    def update_user(self, user_id: int, json: dict) -> ApiResponse[dict]:
        ...

    @delete("/users/{user_id}")
    def delete_user(self, user_id: int) -> ApiResponse[None]:
        ...


@api_client(service="async_service", base_url="https://api.async.com")
class AsyncOrderClient:
    @get("/orders/{order_id}")
    async def get_order(self, order_id: str, status: str = "active") -> ApiResponse[dict]:
        ...

    @post("/orders")
    async def create_order(self, json: dict) -> ApiResponse[dict]:
        ...


class TestDeclarativeDecoratorsSync:
    """Synchronous declarative API client tests."""

    @respx.mock
    def test_sync_get_with_path_param(self):
        respx.get("https://api.users.com/users/42").respond(
            200, json={"id": 42, "name": "Alice"}
        )
        client = UserClient()
        resp = client.get_user(42)

        assert resp.is_success is True
        assert resp.status_code == 200
        assert resp.data == {"id": 42, "name": "Alice"}

    @respx.mock
    def test_sync_post_with_pydantic_body(self):
        route = respx.post("https://api.users.com/users").respond(
            201, json={"id": 99, "name": "Bob", "email": "bob@example.com"}
        )
        client = UserClient()
        req = CreateUserRequest(name="Bob", email="bob@example.com")
        resp = client.create_user(req)

        assert resp.is_success is True
        assert resp.status_code == 201
        assert route.called
        assert b'"name":"Bob"' in route.calls.last.request.content

    @respx.mock
    def test_sync_put_and_delete(self):
        respx.put("https://api.users.com/users/42").respond(
            200, json={"id": 42, "name": "Alice Updated"}
        )
        respx.delete("https://api.users.com/users/42").respond(204)

        client = UserClient()
        put_resp = client.update_user(42, json={"name": "Alice Updated"})
        assert put_resp.is_success is True

        del_resp = client.delete_user(42)
        assert del_resp.is_success is True
        assert del_resp.status_code == 204


class TestDeclarativeDecoratorsAsync:
    """Asynchronous declarative API client tests."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_get_with_query_params(self):
        route = respx.get("https://api.async.com/orders/ord-100").respond(
            200, json={"order_id": "ord-100", "status": "active"}
        )
        client = AsyncOrderClient()
        resp = await client.get_order("ord-100", status="active")

        assert resp.is_success is True
        assert resp.data["order_id"] == "ord-100"
        assert route.called
        assert "status=active" in str(route.calls.last.request.url)

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_post_with_json(self):
        route = respx.post("https://api.async.com/orders").respond(
            201, json={"order_id": "ord-101", "created": True}
        )
        client = AsyncOrderClient()
        resp = await client.create_order(json={"item": "Widget"})

        assert resp.is_success is True
        assert resp.status_code == 201
        assert route.called


class TestDeclarativeDecoratorsEdgeCases:
    """Edge cases and validations."""

    def test_missing_path_parameter_raises_error(self):
        @api_client(base_url="https://api.test.com")
        class IncompleteClient:
            @get("/items/{item_id}/{sub_id}")
            def get_sub_item(self, item_id: int):
                ...

        client = IncompleteClient()
        with pytest.raises(ValueError) as exc_info:
            client.get_sub_item(item_id=10)
        assert "sub_id" in str(exc_info.value)
