"""FastAPI app factory (M0). Binds only via the launcher to 127.0.0.1.

Serves the built React SPA and injects the per-launch token into index.html as
an in-memory `window.__HS_TOKEN__` (never persisted, never in a URL). Installs a
JSON error-envelope handler so clients never receive a raw stack trace.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..config import Settings
from ..core.clock import Clock, SystemClock
from .routes_chat import router as chat_router
from .routes_health import router as health_router

log = logging.getLogger("hellosienna.api")

# frontend/dist relative to repo root (backend/hellosienna/api/app.py -> repo/frontend/dist)
_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def _error_envelope(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _inject_token(html: str, token: str) -> str:
    tag = f'<script>window.__HS_TOKEN__={token!r};</script>'
    if "</head>" in html:
        return html.replace("</head>", tag + "</head>", 1)
    return tag + html


def create_app(settings: Settings, provider, clock: Clock | None = None) -> FastAPI:
    app = FastAPI(title="HelloSienna", docs_url=None, redoc_url=None)
    app.state.settings = settings
    app.state.provider = provider
    app.state.clock = clock or SystemClock()

    app.include_router(health_router)
    app.include_router(chat_router)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(_req: Request, exc: StarletteHTTPException):
        code = "unauthorized" if exc.status_code == 401 else "http_error"
        return _error_envelope(code, str(exc.detail), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(_req: Request, exc: RequestValidationError):
        return _error_envelope("validation_error", "invalid request", 422)

    @app.exception_handler(Exception)
    async def _unhandled(_req: Request, exc: Exception):
        log.exception("unhandled error")
        return _error_envelope("internal_error", "internal server error", 500)

    # --- SPA serving (token injected in-memory) ---
    if (_DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        index_file = _DIST / "index.html"
        if index_file.exists():
            html = index_file.read_text(encoding="utf-8")
        else:
            html = (
                "<!doctype html><html><head><title>HelloSienna — M0</title></head>"
                "<body><h1>HelloSienna — M0</h1>"
                "<p>Backend is up. (No built frontend present.)</p></body></html>"
            )
        return HTMLResponse(_inject_token(html, settings.api_token))

    return app
