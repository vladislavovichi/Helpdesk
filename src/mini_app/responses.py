from __future__ import annotations

import asyncio
import json
import mimetypes
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any


@dataclass(slots=True, frozen=True)
class BinaryPayload:
    filename: str
    content_type: str
    content: bytes


def write_async_json(handler: Any, awaitable: Any) -> None:
    result = asyncio.run(awaitable)
    if hasattr(handler, "_write_json"):
        handler._write_json(HTTPStatus.OK, result)
        return
    write_json(handler, HTTPStatus.OK, result)


def write_json(handler: Any, status: HTTPStatus, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status.value)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def write_binary(handler: Any, payload: BinaryPayload) -> None:
    handler.send_response(HTTPStatus.OK.value)
    handler.send_header("Content-Type", payload.content_type)
    handler.send_header(
        "Content-Disposition",
        f'attachment; filename="{payload.filename}"',
    )
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(payload.content)))
    handler.end_headers()
    handler.wfile.write(payload.content)


def serve_file(
    handler: Any,
    path: Path,
    *,
    static_dir: Path,
    content_type: str | None = None,
) -> None:
    resolved_base = static_dir.resolve()
    resolved_path = path.resolve()
    if resolved_base not in resolved_path.parents and resolved_path != resolved_base:
        write_json(handler, HTTPStatus.NOT_FOUND, {"error": "Файл Mini App не найден."})
        return
    if not resolved_path.is_file():
        write_json(handler, HTTPStatus.NOT_FOUND, {"error": "Файл Mini App не найден."})
        return

    payload = resolved_path.read_bytes()
    guessed_type = content_type or mimetypes.guess_type(resolved_path.name)[0]
    handler.send_response(HTTPStatus.OK.value)
    handler.send_header(
        "Content-Type",
        guessed_type or "application/octet-stream",
    )
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)
