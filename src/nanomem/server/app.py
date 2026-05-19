from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from nanomem.service.core import NanoMemService
from nanomem.server.schemas import (
    capture_request_from_json,
    capture_result_to_json,
    read_request_from_json,
    read_result_to_json,
)


class NanoMemHTTPServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        service: NanoMemService,
        *,
        max_body_bytes: int = 1_000_000,
    ) -> None:
        handler = make_handler(service, max_body_bytes=max_body_bytes)
        super().__init__(server_address, handler)
        self.service = service


def make_handler(
    service: NanoMemService,
    *,
    max_body_bytes: int = 1_000_000,
) -> type[BaseHTTPRequestHandler]:
    class NanoMemHandler(BaseHTTPRequestHandler):
        server_version = "NanoMemHTTP/0.1"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path == "/v1/health":
                _write_json(
                    self,
                    HTTPStatus.OK,
                    {
                        "status": "ok",
                        "service": "nanomem",
                    },
                )
                return
            _write_json(
                self,
                HTTPStatus.NOT_FOUND,
                {"error": "not_found", "path": self.path},
            )

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            try:
                payload = _read_json_body(self, max_body_bytes=max_body_bytes)
                if self.path == "/v1/capture":
                    result = service.capture(capture_request_from_json(payload))
                    _write_json(self, HTTPStatus.OK, capture_result_to_json(result))
                    return
                if self.path == "/v1/read":
                    result = service.read(read_request_from_json(payload))
                    _write_json(self, HTTPStatus.OK, read_result_to_json(result))
                    return
                _write_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {"error": "not_found", "path": self.path},
                )
            except ValueError as exc:
                _write_json(
                    self,
                    HTTPStatus.BAD_REQUEST,
                    {"error": "bad_request", "detail": str(exc)},
                )
            except Exception as exc:  # pragma: no cover - safety net
                _write_json(
                    self,
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {"error": "internal_error", "detail": str(exc)},
                )

        def log_message(self, format: str, *args: Any) -> None:
            return

    return NanoMemHandler


def _read_json_body(
    handler: BaseHTTPRequestHandler,
    *,
    max_body_bytes: int,
) -> dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length > max_body_bytes:
        raise ValueError("request body too large")
    raw = handler.rfile.read(content_length)
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("request body must be a JSON object")
    return payload


def _write_json(
    handler: BaseHTTPRequestHandler,
    status: HTTPStatus,
    payload: dict[str, Any],
) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)
