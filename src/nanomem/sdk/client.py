from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from nanomem.contracts import (
    CaptureRequest,
    CaptureResult,
    FlushRequest,
    FlushResult,
    ReadRequest,
    ReadResult,
)
from nanomem.serde import (
    capture_request_to_json,
    capture_result_from_json,
    flush_request_to_json,
    flush_result_from_json,
    read_request_to_json,
    read_result_from_json,
)


class NanoMemClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class NanoMemClient:
    """Small HTTP client for a NanoMem server.

    The client intentionally exposes the same two memory operations as the
    server: capture and read. Admin and maintenance APIs stay outside this SDK.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = dict(headers or {})

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/v1/health")

    def capture(self, request: CaptureRequest) -> CaptureResult:
        payload = self._request(
            "POST",
            "/v1/capture",
            capture_request_to_json(request),
        )
        return capture_result_from_json(payload)

    def read(self, request: ReadRequest) -> ReadResult:
        payload = self._request("POST", "/v1/read", read_request_to_json(request))
        return read_result_from_json(payload)

    def flush(self, request: FlushRequest | None = None) -> FlushResult:
        payload = self._request(
            "POST",
            "/v1/flush",
            flush_request_to_json(request or FlushRequest()),
        )
        return flush_result_from_json(payload)

    def close(self) -> None:
        return None

    def __enter__(self) -> NanoMemClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None
        headers = {
            "Accept": "application/json",
            **self.headers,
        }
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urlrequest.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlrequest.urlopen(request, timeout=self.timeout) as response:
                return _decode_json(response.read())
        except HTTPError as exc:
            error_payload = _decode_error_payload(exc)
            detail = error_payload.get("detail") or error_payload.get("error")
            message = f"NanoMem request failed with HTTP {exc.code}"
            if detail:
                message = f"{message}: {detail}"
            raise NanoMemClientError(
                message,
                status_code=exc.code,
                payload=error_payload,
            ) from exc
        except URLError as exc:
            raise NanoMemClientError(f"NanoMem request failed: {exc}") from exc


class AsyncNanoMemClient:
    """Async wrapper around the standard-library HTTP client."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._client = NanoMemClient(
            base_url,
            timeout=timeout,
            headers=headers,
        )

    async def health(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._client.health)

    async def capture(self, request: CaptureRequest) -> CaptureResult:
        return await asyncio.to_thread(self._client.capture, request)

    async def read(self, request: ReadRequest) -> ReadResult:
        return await asyncio.to_thread(self._client.read, request)

    async def flush(self, request: FlushRequest | None = None) -> FlushResult:
        return await asyncio.to_thread(self._client.flush, request)

    async def close(self) -> None:
        await asyncio.to_thread(self._client.close)

    async def __aenter__(self) -> AsyncNanoMemClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()


def _decode_json(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise NanoMemClientError("NanoMem response was not a JSON object")
    return payload


def _decode_error_payload(exc: HTTPError) -> dict[str, Any]:
    raw = exc.read()
    if not raw:
        return {}
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {"error": raw.decode("utf-8", errors="replace")}
    if isinstance(payload, dict):
        return payload
    return {"error": str(payload)}
