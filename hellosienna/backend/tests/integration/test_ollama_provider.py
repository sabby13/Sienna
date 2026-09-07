"""Provider code path for #9: OllamaLLMProvider.generate parses Ollama's streaming
NDJSON into text chunks, and connection failures raise ProviderUnavailableError.
(Real model weights emitting text is the only part that needs a Windows+Ollama host.)"""
from __future__ import annotations

import json

import httpx
import pytest

from hellosienna.providers.base import ChatMessage, ProviderUnavailableError
from hellosienna.providers.ollama_llm import OllamaLLMProvider


async def test_generate_parses_ollama_ndjson():
    lines = [
        {"message": {"role": "assistant", "content": "Hel"}, "done": False},
        {"message": {"role": "assistant", "content": "lo!"}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True},
    ]
    ndjson = "\n".join(json.dumps(x) for x in lines) + "\n"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(200, content=ndjson.encode())

    provider = OllamaLLMProvider("http://x", "m", transport=httpx.MockTransport(handler))
    chunks = [c async for c in provider.generate([ChatMessage("user", "hi")])]
    assert chunks == ["Hel", "lo!"]  # empty final chunk skipped; stops on done


async def test_generate_connection_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    provider = OllamaLLMProvider("http://x", "m", transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderUnavailableError):
        async for _ in provider.generate([ChatMessage("user", "hi")]):
            pass
