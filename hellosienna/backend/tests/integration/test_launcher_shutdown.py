"""Acceptance #5 (real loopback bind) + #14 (clean shutdown, port re-bindable).

Starts a real uvicorn server in a daemon thread, hits it over real HTTP, then
shuts it down and confirms the port is free again.
"""
from __future__ import annotations

import socket
import time

import httpx

from hellosienna.api.app import create_app
from hellosienna.config import Settings
from hellosienna.core.clock import TestClock
from hellosienna.main import ServerThread, _free_port

from ..fakes import FakeLLMProvider


def _port_free(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def test_server_binds_loopback_and_shuts_down_cleanly(tmp_path):
    settings = Settings(data_dir=tmp_path / "HelloSienna")
    app = create_app(settings, FakeLLMProvider(), TestClock())
    port = _free_port()
    server = ServerThread(app, "127.0.0.1", port)

    assert server._config.host == "127.0.0.1"  # never 0.0.0.0

    server.start()
    assert server.wait_until_ready(f"http://127.0.0.1:{port}/", timeout=10)

    # real HTTP round-trip with the header token
    r = httpx.get(f"http://127.0.0.1:{port}/api/health",
                  headers={"X-HS-Token": settings.api_token}, timeout=5)
    assert r.status_code == 200 and r.json()["status"] == "ok"

    server.shutdown()
    # give the OS a moment to release the socket
    for _ in range(20):
        if _port_free(port):
            break
        time.sleep(0.1)
    assert _port_free(port), "port not released after shutdown"
