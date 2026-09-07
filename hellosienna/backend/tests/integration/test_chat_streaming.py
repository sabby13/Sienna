"""Acceptance #9: a streamed response is delivered as incremental SSE token events,
followed by done. Also verifies the provider-error path emits an SSE error event."""
from __future__ import annotations

import json

import httpx
import pytest

from hellosienna.api.app import create_app
from hellosienna.config import Settings
from hellosienna.core.clock import TestClock

from ..fakes import UnavailableLLMProvider


def _parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip() or block.startswith(":"):
            continue
        ev, data = None, None
        for line in block.splitlines():
            if line.startswith("event:"):
                ev = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = json.loads(line[len("data:"):].strip())
        if ev:
            events.append((ev, data))
    return events


async def test_chat_streams_incremental_tokens_then_done(client, auth_headers):
    async with client.stream(
        "POST", "/api/chat", headers=auth_headers, json={"message": "hi"}
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = ""
        async for chunk in r.aiter_text():
            body += chunk
    events = _parse_sse(body)
    kinds = [e for e, _ in events]
    assert "token" in kinds and kinds[-1] == "done"
    text = "".join(d["text"] for e, d in events if e == "token")
    assert text == "Hello, Sahib!"
    assert kinds.count("token") >= 2  # genuinely incremental, not one blob


async def test_chat_requires_token(client):
    r = await client.post("/api/chat", json={"message": "hi"})
    assert r.status_code == 401


async def test_chat_provider_error_emits_sse_error(tmp_path):
    settings = Settings(data_dir=tmp_path / "HelloSienna")
    app = create_app(settings, UnavailableLLMProvider(), TestClock())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        async with c.stream(
            "POST", "/api/chat",
            headers={"X-HS-Token": settings.api_token}, json={"message": "hi"}
        ) as r:
            assert r.status_code == 200
            body = ""
            async for chunk in r.aiter_text():
                body += chunk
    events = _parse_sse(body)
    assert any(e == "error" and d["code"] == "provider_unavailable" for e, d in events)
