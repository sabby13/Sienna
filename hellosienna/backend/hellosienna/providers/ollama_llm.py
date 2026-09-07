"""Ollama LLM provider (M0): streaming generate + reachability/model status.

Talks to Ollama's HTTP API. If Ollama is not running, generate() raises
ProviderUnavailableError before yielding, and model_status() returns a clean
"unavailable" payload (acceptance #8) rather than raising.
"""

from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from .base import (
    ChatMessage,
    GenOptions,
    LLMProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class OllamaLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 60.0, transport=None) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._transport = transport  # for tests (httpx.MockTransport); None in production

    async def generate(
        self, messages: list[ChatMessage], *, options: GenOptions | None = None
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
        }
        if options and options.temperature is not None:
            payload["options"] = {"temperature": options.temperature}

        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                async with client.stream(
                    "POST", f"{self._base_url}/api/chat", json=payload
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        chunk = (obj.get("message") or {}).get("content", "")
                        if chunk:
                            yield chunk
                        if obj.get("done"):
                            break
        except httpx.TimeoutException as e:  # noqa
            raise ProviderTimeoutError(str(e)) from e
        except httpx.HTTPError as e:  # connect errors, bad status, etc.
            raise ProviderUnavailableError(str(e)) from e


async def model_status(base_url: str, chat_model: str, embed_model: str) -> dict:
    """Probe Ollama reachability and whether configured models are present.

    Never raises for an unreachable runtime — returns a clean payload (acceptance #8).
    """
    base = base_url.rstrip("/")
    result = {
        "ollama_reachable": False,
        "chat_model": chat_model,
        "chat_model_present": False,
        "embed_model": embed_model,
        "embed_model_present": False,
        "detail": None,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
            data = resp.json()
        names = {m.get("name", "") for m in data.get("models", [])}
        # Ollama tags are like "qwen2.5:7b"; match exact or bare base name.
        bare = {n.split(":")[0] for n in names}
        result["ollama_reachable"] = True
        result["chat_model_present"] = chat_model in names or chat_model.split(":")[0] in bare
        result["embed_model_present"] = embed_model in names or embed_model.split(":")[0] in bare
    except httpx.HTTPError as e:
        result["detail"] = f"unavailable: {type(e).__name__}"
    return result
