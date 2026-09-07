"""Per-launch token auth (Change 1): header X-HS-Token only, on every request.

The token is never read from a query string. Uses a constant-time comparison.
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request

TOKEN_HEADER = "X-HS-Token"


async def require_token(request: Request, x_hs_token: str | None = Header(default=None)) -> None:
    expected: str = request.app.state.settings.api_token
    if not x_hs_token or not secrets.compare_digest(x_hs_token, expected):
        raise HTTPException(status_code=401, detail="invalid or missing X-HS-Token")
