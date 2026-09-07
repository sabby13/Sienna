"""Provider interface contracts (frozen in the Pre-M0 Contract §3.1–3.2).

Definitions only for the parts M0 does not use: EmbeddingProvider and
LLMProvider.complete_json are declared here so the shapes are frozen, but M0
implements only LLMProvider.generate + reachability (no embeddings — M0 non-goal).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AsyncIterator, Protocol, runtime_checkable


# ---- shared value types ----------------------------------------------------
@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class GenOptions:
    temperature: float | None = None
    max_tokens: int | None = None
    extra: dict = field(default_factory=dict)


# ---- error taxonomy --------------------------------------------------------
class ProviderError(Exception):
    """Base class for provider transport errors."""


class ProviderUnavailableError(ProviderError):
    """The model runtime could not be reached."""


class ProviderTimeoutError(ProviderError):
    """The model runtime did not respond in time."""


class StructuredOutputError(ProviderError):
    """complete_json could not produce schema-valid output (used from M2)."""


# ---- interfaces ------------------------------------------------------------
@runtime_checkable
class LLMProvider(Protocol):
    """Owns transport to a text-generation model. Caller owns prompt + budget."""

    def generate(
        self, messages: list[ChatMessage], *, options: GenOptions | None = None
    ) -> AsyncIterator[str]:
        """Stream response text chunks. Raises ProviderUnavailableError before the
        first chunk if the runtime is unreachable."""
        ...

    # Declared (frozen) but NOT used at M0 — first exercised at M2.
    async def complete_json(self, messages, schema, *, options=None):  # pragma: no cover
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Independent of LLMProvider. Declared (frozen) but NOT implemented at M0."""

    model: str
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        ...
