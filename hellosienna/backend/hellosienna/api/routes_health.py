"""Health + model-status routes (M0, acceptance #5, #7, #8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from .. import __version__
from ..providers.ollama_llm import model_status
from .auth import require_token
from .schemas import HealthResponse, ModelStatusResponse

router = APIRouter(prefix="/api", dependencies=[Depends(require_token)])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(version=__version__)


@router.get("/model/status", response_model=ModelStatusResponse)
async def model_status_route(request: Request) -> ModelStatusResponse:
    s = request.app.state.settings
    data = await model_status(s.ollama_base_url, s.chat_model, s.embed_model)
    return ModelStatusResponse(**data)
