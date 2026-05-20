from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from typing import Any

from nanomem.server.admin import handle_admin_get, handle_admin_post
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
            try:
                admin_response = handle_admin_get(service, self.path)
                if admin_response is not None:
                    _write_response(self, admin_response)
                    return
            except KeyError as exc:
                _write_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {"error": "not_found", "detail": str(exc)},
                )
                return
            except ValueError as exc:
                _write_json(
                    self,
                    HTTPStatus.BAD_REQUEST,
                    {"error": "bad_request", "detail": str(exc)},
                )
                return

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
                admin_response = handle_admin_post(service, self.path, payload)
                if admin_response is not None:
                    _write_response(self, admin_response)
                    return
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
            except KeyError as exc:
                _write_json(
                    self,
                    HTTPStatus.NOT_FOUND,
                    {"error": "not_found", "detail": str(exc)},
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
    _write_raw(handler, status, encoded, "application/json; charset=utf-8")


def _write_response(
    handler: BaseHTTPRequestHandler,
    response: Any,
) -> None:
    _write_raw(handler, response.status, response.body, response.content_type)


def _write_raw(
    handler: BaseHTTPRequestHandler,
    status: HTTPStatus,
    body: bytes,
    content_type: str,
) -> None:
    handler.send_response(status.value)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
