"""API request/response DTOs (Pydantic). Distinct from domain types."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class ModelStatusResponse(BaseModel):
    ollama_reachable: bool
    chat_model: str
    chat_model_present: bool
    embed_model: str
    embed_model_present: bool
    detail: str | None = None


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None  # M0: accepted but NOT persisted (non-goal)


class ErrorEnvelope(BaseModel):
    error: "ErrorBody"


class ErrorBody(BaseModel):
    code: str
    message: str


ErrorEnvelope.model_rebuild()
