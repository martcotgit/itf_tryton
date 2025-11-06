import base64
import json

import httpx
import pytest
from django.core.cache import caches

from apps.core.services.tryton_client import TrytonClient


@pytest.fixture(autouse=True)
def clear_cache():
    caches["default"].clear()
    yield
    caches["default"].clear()


@pytest.fixture
def configured_settings(settings):
    settings.TRYTON_RPC_URL = "http://tryton.test/"
    settings.TRYTON_DATABASE = "tryton"
    settings.TRYTON_USER = "admin"
    settings.TRYTON_PASSWORD = "secret"
    settings.TRYTON_TIMEOUT = 1.0
    settings.TRYTON_RETRY_ATTEMPTS = 1
    settings.TRYTON_SESSION_TTL = 60
    settings.TESTING = True
    return settings


def _build_transport(handler):
    def _dispatch(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        return handler(payload, request)

    return httpx.MockTransport(_dispatch)


def test_call_authenticates_and_executes(configured_settings):
    calls = {"login": 0, "search": 0}

    def handler(payload, request):
        if payload["method"] == "common.db.login":
            calls["login"] += 1
            assert request.url.path == "/tryton/"
            assert payload["params"] == ["admin", {"password": "secret"}]
            return httpx.Response(200, json=[1, "session-123"])

        expected_token = base64.b64encode(b"admin:1:session-123").decode()
        assert request.headers["Authorization"] == f"Session {expected_token}"
        assert request.url.path == "/tryton/"
        assert payload["method"] == "model.party.party.search"
        assert payload["params"] == [[], 0, None, {}]
        calls["search"] += 1
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": payload["id"], "result": [{"id": 42, "name": "Test"}]},
        )

    client = TrytonClient(transport=_build_transport(handler))
    result = client.call("model", "party.party.search", [[], 0, None, {}])

    assert calls == {"login": 1, "search": 1}
    assert result == [{"id": 42, "name": "Test"}]


def test_call_reauthenticates_on_expired_session(configured_settings):
    calls = {"login": 0, "search": 0}

    def handler(payload, request):
        if payload["method"] == "common.db.login":
            calls["login"] += 1
            return httpx.Response(200, json=[calls["login"], f"session-{calls['login']}"])

        calls["search"] += 1
        if calls["search"] == 1:
            return httpx.Response(status_code=401)

        expected_token = base64.b64encode(f"admin:2:session-{calls['login']}".encode()).decode()
        assert request.headers["Authorization"] == f"Session {expected_token}"
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": payload["id"], "result": "ok"})

    client = TrytonClient(transport=_build_transport(handler))
    assert client.call("model", "party.party.search", [[], 0, None, {}]) == "ok"
    assert calls["login"] == 2
    assert calls["search"] == 2


def test_cached_call_returns_cached_result(configured_settings):
    execute_calls = 0

    def handler(payload, request):
        nonlocal execute_calls
        if payload["method"] == "common.db.login":
            return httpx.Response(200, json=[1, "session"])
        execute_calls += 1
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": payload["id"], "result": {"status": "ok"}},
        )

    client = TrytonClient(transport=_build_transport(handler))

    first = client.cached_call(("model", "party.party.search"), [[], 0, None, {}], ttl=120)
    second = client.cached_call(("model", "party.party.search"), [[], 0, None, {}], ttl=120)

    assert first == {"status": "ok"}
    assert second == {"status": "ok"}
    assert execute_calls == 1


def test_call_without_credentials_raises(settings):
    settings.TRYTON_RPC_URL = "http://tryton.test/"
    settings.TRYTON_DATABASE = "tryton"
    settings.TRYTON_USER = None
    settings.TRYTON_PASSWORD = None
    with pytest.raises(ValueError):
        TrytonClient()


def test_ping_handles_plain_list_response(configured_settings):
    def handler(payload, request):
        assert request.url.path == "/"
        assert payload["method"] == "common.db.list"
        return httpx.Response(200, json=["tryton"])

    client = TrytonClient(transport=_build_transport(handler))
    assert client.ping() is True
