"""Acceptance #6 + Change 1: per-launch token via X-HS-Token header only.
Missing/wrong -> 401; correct -> 200; token never accepted via query string."""
from __future__ import annotations

import pytest


async def test_health_requires_token(client):
    r = await client.get("/api/health")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


async def test_wrong_token_rejected(client):
    r = await client.get("/api/health", headers={"X-HS-Token": "nope"})
    assert r.status_code == 401


async def test_correct_token_accepted(client, auth_headers):
    r = await client.get("/api/health", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_token_in_query_string_is_ignored(client, token):
    # Passing the token as a query param must NOT authenticate (header-only invariant).
    r = await client.get(f"/api/health?token={token}")
    assert r.status_code == 401
