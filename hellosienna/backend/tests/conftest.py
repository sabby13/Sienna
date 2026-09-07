from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from hellosienna.api.app import create_app
from hellosienna.api.auth import TOKEN_HEADER
from hellosienna.config import Settings
from hellosienna.core.clock import TestClock

from .fakes import FakeLLMProvider


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    # Private data dir points at a temp path (never the repo).
    return Settings(data_dir=tmp_path / "HelloSienna")


@pytest.fixture
def app(settings: Settings):
    return create_app(settings, FakeLLMProvider(), TestClock())


@pytest.fixture
def token(settings: Settings) -> str:
    return settings.api_token


@pytest.fixture
def auth_headers(token: str) -> dict:
    return {TOKEN_HEADER: token}


@pytest.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
