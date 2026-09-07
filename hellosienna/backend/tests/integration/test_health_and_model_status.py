"""Acceptance #5, #7, #8: health returns ok; model/status reports Ollama-unavailable
cleanly (no crash) when Ollama is not running."""
from __future__ import annotations


async def test_health_ok(client, auth_headers):
    r = await client.get("/api/health", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]


async def test_model_status_ollama_unavailable_is_clean(client, auth_headers):
    # No Ollama running in this environment -> reachable False, HTTP 200, no crash.
    r = await client.get("/api/model/status", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["ollama_reachable"] is False
    assert body["chat_model_present"] is False
    assert body["embed_model_present"] is False
    assert body["detail"] and "unavailable" in body["detail"]
