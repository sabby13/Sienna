"""Acceptance #6/#15 + Change 1: /api/events requires the header token and opens an
SSE stream; validation/unhandled errors return a JSON error envelope, not a stack trace.

The SSE stream is exercised against a REAL uvicorn server so client disconnect
propagates and cancels the server generator cleanly.
"""
from __future__ import annotations

import socket
import time

import httpx

from hellosienna.api.app import create_app
from hellosienna.config import Settings
from hellosienna.core.clock import TestClock
from hellosienna.main import ServerThread, _free_port

from ..fakes import FakeLLMProvider


async def test_events_requires_token(client):
    r = await client.get("/api/events")
    assert r.status_code == 401


async def test_validation_error_returns_envelope(client, auth_headers):
    # Missing required 'message' field -> 422 envelope, not a raw error.
    r = await client.post("/api/chat", headers=auth_headers, json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_events_opens_sse_stream_real_server(tmp_path):
    settings = Settings(data_dir=tmp_path / "HelloSienna")
    app = create_app(settings, FakeLLMProvider(), TestClock())
    port = _free_port()
    server = ServerThread(app, "127.0.0.1", port)
    server.start()
    assert server.wait_until_ready(f"http://127.0.0.1:{port}/", timeout=10)
    try:
        with httpx.stream(
            "GET", f"http://127.0.0.1:{port}/api/events",
            headers={"X-HS-Token": settings.api_token}, timeout=5,
        ) as r:
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/event-stream")
            first = next(r.iter_lines())
            assert first.startswith(":")  # ": connected" comment
        # closing the stream above disconnects the client
    finally:
        server.shutdown()
