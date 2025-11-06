from __future__ import annotations

import base64
import hashlib
import json
import logging
import uuid
from typing import Any, Iterable, MutableMapping, Optional, Tuple, Union
import httpx
from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)

JSONType = Union[MutableMapping[str, Any], Iterable[Any], str, int, float, bool, None]

# Methods served from the root endpoint (no database segment in the URL)
ROOT_ENDPOINT_METHODS = {
    "common.server.version",
    "common.db.list",
    "common.authentication.services",
}


class TrytonRPCError(RuntimeError):
    """Base error raised when the Tryton JSON-RPC gateway returns an error payload."""

    def __init__(self, message: str, *, code: Optional[int] = None, data: Optional[dict] = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data or {}


class TrytonAuthError(TrytonRPCError):
    """Raised when authentication or session renewal fails."""


class TrytonClient:
    """Lightweight JSON-RPC client tailored for Tryton interactions."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        database: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        cache_alias: str = "default",
        cache_ttl: Optional[int] = None,
        transport: Optional[httpx.BaseTransport] = None,
        http_client: Optional[httpx.Client] = None,
        session_id: Optional[str] = None,
    ) -> None:
        self.base_url = base_url or getattr(settings, "TRYTON_RPC_URL")
        self.database = database or getattr(settings, "TRYTON_DATABASE", "tryton")
        self.username = username or getattr(settings, "TRYTON_USER", None)
        self.password = password or getattr(settings, "TRYTON_PASSWORD", None)
        if not self.username or not self.password:
            raise ValueError("TRYTON_USER and TRYTON_PASSWORD settings are required to init TrytonClient.")

        timeout_value = timeout if timeout is not None else getattr(settings, "TRYTON_TIMEOUT", 10.0)
        retries_value = retries if retries is not None else getattr(settings, "TRYTON_RETRY_ATTEMPTS", 3)

        transport_instance = transport or httpx.HTTPTransport(retries=retries_value)
        self._client = http_client or httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout_value),
            transport=transport_instance,
        )

        self._cache = caches[cache_alias]
        self._cache_ttl = cache_ttl if cache_ttl is not None else getattr(settings, "TRYTON_SESSION_TTL", 300)
        self._session_id = session_id
        self._session_user_id: Optional[int] = None
        self._session_token: Optional[str] = None
        self._auth_header: Optional[str] = None
        self._testing_mode = getattr(settings, "TESTING", False)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _database_path(self) -> str:
        return f"{self.database.rstrip('/')}/"

    def _build_payload(self, method: str, params: Iterable[Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "method": method, "params": list(params), "id": str(uuid.uuid4())}

    def _request(
        self,
        payload: dict[str, Any],
        *,
        path: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> Any:
        request_path = "" if path is None else path
        try:
            response = self._client.post(request_path, json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in (401, 403):
                raise TrytonAuthError("Authentication with Tryton failed.", code=status) from exc
            logger.error("Tryton HTTP error calling %s: %s", payload.get("method"), exc)
            raise TrytonRPCError("HTTP error while contacting Tryton.", data={"method": payload.get("method")}) from exc
        except httpx.HTTPError as exc:
            logger.error("Tryton HTTP error calling %s: %s", payload.get("method"), exc)
            raise TrytonRPCError("HTTP error while contacting Tryton.", data={"method": payload.get("method")}) from exc

        # Tryton may return bare JSON arrays (e.g. login success)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON response from Tryton for %s", payload.get("method"))
            raise TrytonRPCError("Received invalid JSON from Tryton.", data={"body": response.text}) from exc

        if isinstance(data, dict):
            if data.get("error"):
                error = data["error"]
                code = error.get("code")
                message = error.get("message", "Tryton RPC error")
                if code in (401, 403):
                    raise TrytonAuthError(message, code=code, data=error.get("data"))
                raise TrytonRPCError(message, code=code, data=error.get("data"))
            return data.get("result")

        return data

    def _authenticate(self, force: bool = False) -> str:
        if self._testing_mode and self._auth_header and not force:
            return self._auth_header
        if self._auth_header and not force:
            return self._auth_header

        payload = self._build_payload(
            "common.db.login",
            [self.username, {"password": self.password}],
        )
        try:
            result = self._request(payload, path=self._database_path())
        except TrytonRPCError as exc:
            logger.error("Failed to authenticate against Tryton (user=%s): %s", self.username, exc)
            raise

        if not result:
            raise TrytonAuthError("Tryton did not return a session identifier.")

        # Tryton returns [user_id, session_token]
        if isinstance(result, (list, tuple)) and len(result) == 2:
            user_id, session_token = result
        elif isinstance(result, dict) and "session" in result:
            user_id = result.get("user")
            session_token = result["session"]
        else:
            raise TrytonAuthError("Unexpected login payload returned by Tryton.")

        self._session_id = session_token
        self._session_user_id = int(user_id)
        self._session_token = session_token
        token_value = base64.b64encode(f"{self.username}:{user_id}:{session_token}".encode("utf-8")).decode("ascii")
        self._auth_header = f"Session {token_value}"
        return self._auth_header

    def call(
        self,
        service: str,
        method: str,
        params: Optional[Union[Iterable[Any], JSONType]] = None,
        *,
        use_session: bool = True,
        force_refresh: bool = False,
    ) -> Any:
        full_method = self._compose_method(service, method)
        attempt = 0
        current_params = params or []
        while attempt < 2:
            headers = None
            if use_session:
                auth_header = self._authenticate(force=force_refresh or attempt > 0)
                headers = {"Authorization": auth_header}
            payload = self._build_payload(full_method, current_params)
            request_path = self._resolve_path(full_method)
            try:
                return self._request(payload, path=request_path, headers=headers)
            except TrytonAuthError:
                logger.info("Tryton session expired, attempting re-authentication.")
                self.reset_session()
                attempt += 1
        raise TrytonAuthError("Unable to authenticate with Tryton after retrying.")

    def cached_call(
        self,
        method: Union[str, Tuple[str, str]],
        params: Optional[Union[Iterable[Any], JSONType]] = None,
        *,
        ttl: Optional[int] = None,
        use_session: bool = True,
    ) -> Any:
        service_name, method_name, full_method = self._normalize_method(method)
        cache_key = self.cache_key(full_method, params)
        result = self._cache.get(cache_key)
        if result is not None:
            return result

        result = self.call(service_name, method_name, params=params, use_session=use_session)
        cache_ttl = self._cache_ttl if ttl is None else ttl
        if cache_ttl:
            self._cache.set(cache_key, result, cache_ttl)
        return result

    def ping(self) -> bool:
        try:
            result = self._request(
                self._build_payload("common.db.list", []),
                path=self._resolve_path("common.db.list"),
            )
            if isinstance(result, list):
                return bool(result)
            return True
        except TrytonRPCError:
            logger.exception("Tryton ping failed.")
            return False

    @staticmethod
    def cache_key(method: str, params: Optional[Union[Iterable[Any], JSONType]]) -> str:
        serialized_params: str
        if params is None:
            serialized_params = "null"
        else:
            try:
                serialized_params = json.dumps(params, sort_keys=True, default=str)
            except TypeError:
                serialized_params = repr(params)
        digest = hashlib.sha256(serialized_params.encode("utf-8")).hexdigest()
        return f"tryton:{method}:{digest}"

    @staticmethod
    def _normalize_method(method: Union[str, Tuple[str, str]]) -> Tuple[str, str, str]:
        if isinstance(method, tuple):
            if len(method) != 2:
                raise ValueError("Method tuple must contain exactly two elements (service, method).")
            service, method_name = method
        elif "." in method:
            parts = method.split(".", 1)
            if len(parts) != 2:
                raise ValueError("Method must contain a dot separator or be provided as a tuple.")
            service, method_name = parts
        else:
            raise ValueError("Method must contain a dot separator or be provided as a tuple.")
        return service, method_name, f"{service}.{method_name}"

    def reset_session(self):
        """Clear the cached session identifier."""
        self._session_id = None
        self._session_user_id = None
        self._session_token = None
        self._auth_header = None

    def _compose_method(self, service: str, method: str) -> str:
        if method.startswith(f"{service}.") or method.startswith("common."):
            return method
        return f"{service}.{method}"

    def _resolve_path(self, method: str) -> str:
        if method in ROOT_ENDPOINT_METHODS:
            return ""
        if method == "common.db.login" or method.startswith(("model.", "wizard.", "report.", "common.db.")):
            return self._database_path()
        return ""
