"""Test doubles: a deterministic LLM provider and an always-unavailable one.

These let the streaming pipeline (SSE + header auth + client consumption) be
verified end-to-end without a running Ollama.
"""

from __future__ import annotations

from typing import AsyncIterator

from hellosienna.providers.base import ChatMessage, GenOptions, ProviderUnavailableError


class FakeLLMProvider:
    def __init__(self, tokens: list[str] | None = None) -> None:
        self._tokens = tokens or ["Hello", ", ", "Sahib", "!"]

    async def generate(
        self, messages: list[ChatMessage], *, options: GenOptions | None = None
    ) -> AsyncIterator[str]:
        for t in self._tokens:
            yield t


class UnavailableLLMProvider:
    async def generate(self, messages, *, options=None) -> AsyncIterator[str]:
        raise ProviderUnavailableError("ollama not running")
        yield  # pragma: no cover  (makes this an async generator)
