"""Unit tests for ohent_shared core modules."""
import pytest
from datetime import datetime, timedelta, timezone


class TestErrors:
    def test_all_error_codes_defined(self):
        from ohent_shared.errors import ErrorCode
        expected = [
            "UNAUTHORIZED", "FORBIDDEN", "QUOTA_EXCEEDED", "NOT_FOUND",
            "CONFLICT", "API_DEPRECATED", "VALIDATION_ERROR", "RATE_LIMITED",
            "INTERNAL_ERROR", "UPSTREAM_UNAVAILABLE", "SERVICE_UNAVAILABLE",
        ]
        for code in expected:
            assert hasattr(ErrorCode, code), f"Missing error code: {code}"

    def test_error_status_map_covers_all_codes(self):
        from ohent_shared.errors import ErrorCode, ErrorStatusMap
        for code_name in vars(ErrorCode):
            if code_name.isupper():
                code = getattr(ErrorCode, code_name)
                assert code in ErrorStatusMap.MAP, f"Missing status for {code}"

    def test_oh_error_creation(self):
        from ohent_shared.errors import OHError
        err = OHError(code="NOT_FOUND", message="test", request_id="req-1", details={"key": "val"})
        assert err["status_code"] == 404
        assert err["detail"]["code"] == "NOT_FOUND"

    def test_error_response_format(self):
        from ohent_shared.errors import error_response
        resp = error_response("VALIDATION_ERROR", "test msg", "req-1", {"field": "name"})
        assert resp == {
            "code": "VALIDATION_ERROR",
            "message": "test msg",
            "request_id": "req-1",
            "details": {"field": "name"},
        }


class TestResponses:
    def test_ok_response(self):
        from ohent_shared.responses import ok_response
        assert ok_response() == {"ok": True}
        assert ok_response(task_id="t-1") == {"ok": True, "task_id": "t-1"}

    def test_data_response(self):
        from ohent_shared.responses import data_response
        assert data_response({"id": "1"}) == {"data": {"id": "1"}}

    def test_list_response(self):
        from ohent_shared.responses import list_response
        resp = list_response([1, 2], total=2, page=1, page_size=20)
        assert resp == {"items": [1, 2], "total": 2, "page": 1, "page_size": 20}


class TestSecurity:
    def test_create_and_decode_access_token(self):
        from ohent_shared.security import create_access_token, decode_token
        token = create_access_token(
            {"sub": "user-1", "org_id": "org-1", "role": "admin", "permissions": ["read"]}
        )
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["org_id"] == "org-1"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read"]
        assert payload["type"] == "access"
        assert "jti" in payload
        assert "exp" in payload

    def test_create_and_decode_refresh_token(self):
        from ohent_shared.security import create_refresh_token, decode_token
        token = create_refresh_token({"sub": "user-1"})
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"

    def test_expired_token_raises(self):
        import jwt
        from ohent_shared.security import create_access_token, decode_token
        token = create_access_token({"sub": "user-1"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

    def test_invalid_token_raises(self):
        import jwt
        from ohent_shared.security import decode_token
        with pytest.raises(jwt.InvalidTokenError):
            decode_token("invalid.token.here")


class TestSchemas:
    def test_request_context(self):
        from ohent_shared.schemas import RequestContext
        ctx = RequestContext(user_id="u-1", org_id="o-1", request_id="r-1")
        assert ctx.user_id == "u-1"
        assert ctx.permissions == []

    def test_paginated_query_defaults(self):
        from ohent_shared.schemas import PaginatedQuery
        q = PaginatedQuery()
        assert q.page == 1
        assert q.page_size == 20

    def test_paginated_query_max(self):
        from ohent_shared.schemas import PaginatedQuery
        with pytest.raises(Exception):
            PaginatedQuery(page_size=200)


class TestConfig:
    def test_service_urls(self):
        from ohent_shared.config import GATEWAY_PORT, AUTH_URL, HOST_URL, SCHEDULER_URL
        assert GATEWAY_PORT == 8000
        assert "8001" in AUTH_URL
        assert "8002" in HOST_URL
        assert "8003" in SCHEDULER_URL


class TestServiceClient:
    @pytest.mark.asyncio
    async def test_service_client_headers(self):
        from ohent_shared.service_client import ServiceClient
        client = ServiceClient(base_url="http://localhost:8001")
        assert client.base_url == "http://localhost:8001"
        await client.close()

    @pytest.mark.asyncio
    async def test_service_client_context_injection(self):
        """ServiceClient.call should inject tenant/user headers from context."""
        from unittest.mock import AsyncMock, patch, MagicMock
        from ohent_shared.service_client import ServiceClient
        client = ServiceClient(base_url="http://localhost:8001")
        ctx = {"user_id": "u-1", "org_id": "o-1", "request_id": "r-1"}
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_resp) as mock_req:
            await client.call("GET", "/test", ctx=ctx)
            call_kwargs = mock_req.call_args
            headers = call_kwargs.kwargs["headers"]
            assert headers["X-User-ID"] == "u-1"
            assert headers["X-Org-ID"] == "o-1"
            assert headers["X-Request-ID"] == "r-1"
            assert headers["X-Internal-Call"] == "true"
        await client.close()

    @pytest.mark.asyncio
    async def test_service_client_call_with_params(self):
        """ServiceClient.call should pass params to httpx."""
        from unittest.mock import AsyncMock, patch, MagicMock
        from ohent_shared.service_client import ServiceClient
        client = ServiceClient(base_url="http://localhost:8001")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"items": []}
        with patch.object(client._client, "request", new_callable=AsyncMock, return_value=mock_resp) as mock_req:
            await client.call("GET", "/agents", params={"page": "2"})
            call_kwargs = mock_req.call_args
            assert call_kwargs.kwargs["params"] == {"page": "2"}
        await client.close()


class TestDB:
    def test_base_class_exists(self):
        from ohent_shared.db import Base
        assert Base is not None

    def test_get_db_is_generator(self):
        import inspect
        from ohent_shared.db import get_db
        assert inspect.isasyncgenfunction(get_db)


class TestRedis:
    def test_get_redis_is_coroutine(self):
        import inspect
        from ohent_shared.redis import get_redis, close_redis
        assert inspect.iscoroutinefunction(get_redis)
        assert inspect.iscoroutinefunction(close_redis)


class TestListResponse:
    def test_list_response_defaults(self):
        from ohent_shared.responses import list_response
        result = list_response(items=[{"id": "1"}], total=1)
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total"] == 1

    def test_list_response_custom_page(self):
        from ohent_shared.responses import list_response
        result = list_response(items=[], total=100, page=3, page_size=10)
        assert result["page"] == 3
        assert result["page_size"] == 10
        assert result["total"] == 100

    def test_list_response_empty(self):
        from ohent_shared.responses import list_response
        result = list_response(items=[], total=0)
        assert result["items"] == []
        assert result["total"] == 0
