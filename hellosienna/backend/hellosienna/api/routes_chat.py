"""Chat streaming + server-push event channel (M0, acceptance #9).

POST /api/chat  -> SSE token stream (raw Ollama pass-through; NOT persisted, no memory).
GET  /api/events -> long-lived SSE for server-initiated pushes; silent until M3
                    (heartbeat comments only). Both require the X-HS-Token header.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from ..providers.base import ChatMessage, ProviderError
from .auth import require_token
from .schemas import ChatRequest

log = logging.getLogger("hellosienna.chat")
router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])

SIENNA_SYSTEM_PROMPT = "You are Sienna, a warm, persistent AI companion."


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    provider = request.app.state.provider

    async def stream() -> AsyncIterator[str]:
        messages = [
            ChatMessage(role="system", content=SIENNA_SYSTEM_PROMPT),
            ChatMessage(role="user", content=body.message),
        ]
        try:
            async for chunk in provider.generate(messages):
                yield _sse("token", {"text": chunk})
            yield _sse("done", {})
        except ProviderError as e:
            log.warning("chat stream provider error: %s", type(e).__name__)
            yield _sse("error", {"code": "provider_unavailable", "message": str(e)})

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    """Ambient server->client channel. M0: emits an initial comment then heartbeats.
    No domain events are pushed until M3."""

    async def stream() -> AsyncIterator[str]:
        yield ": connected\n\n"  # SSE comment; proves the channel is open
        ticks = 0
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(0.5)  # poll disconnect responsively
            ticks += 1
            if ticks % 30 == 0:       # ~every 15s
                yield ": keepalive\n\n"
            # M3 pushes real server-initiated events here.

    return StreamingResponse(stream(), media_type="text/event-stream")
