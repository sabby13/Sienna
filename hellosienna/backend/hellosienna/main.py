"""HelloSienna launcher (M0).

Wires the foundation together: logging -> settings/dirs -> migrations ->
write/read round-trip -> uvicorn on 127.0.0.1 (daemon thread) -> pywebview window,
with clean shutdown when the window closes.
"""

from __future__ import annotations

import argparse
import logging
import os
import socket
import threading
import time

import httpx
import uvicorn

from . import __version__
from .api.app import create_app
from .config import Settings
from .core.clock import SystemClock, isoformat_utc
from .logging_setup import setup_logging
from .persistence.db import app_meta_get, app_meta_set, make_engine
from .persistence.migrate import upgrade_to_head
from .providers.ollama_llm import OllamaLLMProvider

log = logging.getLogger("hellosienna.main")


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class ServerThread:
    """Runs uvicorn in a daemon thread; supports clean shutdown (acceptance #14)."""

    def __init__(self, app, host: str, port: int) -> None:
        self._config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        self._server = uvicorn.Server(self._config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def wait_until_ready(self, url: str, timeout: float = 10.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._server.started:
                return True
            time.sleep(0.05)
        return False

    def shutdown(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10.0)


def _startup_roundtrip(settings: Settings, clock: SystemClock) -> None:
    """Migrate + prove a write/read round-trip (acceptance #11, #12)."""
    upgrade_to_head(settings.db_path)
    engine = make_engine(settings.db_path)
    now = isoformat_utc(clock.now())
    with engine.begin() as conn:
        first = app_meta_get(conn, "schema_initialized_at")
        if first is None:
            app_meta_set(conn, "schema_initialized_at", now, now)
        app_meta_set(conn, "last_launch_at", now, now)
        readback = app_meta_get(conn, "last_launch_at")
        assert readback == now, "app_meta write/read round-trip failed"
    engine.dispose()


def run() -> None:
    settings = Settings()
    settings.ensure_dirs()
    setup_logging(settings.log_dir, token=settings.api_token)
    clock = SystemClock()

    log.info("HelloSienna %s starting; data dir resolved (private, not in repo)", __version__)
    _startup_roundtrip(settings, clock)

    provider = OllamaLLMProvider(settings.ollama_base_url, settings.chat_model)
    app = create_app(settings, provider, clock)

    settings.port = int(os.environ["HS_PORT"]) if os.environ.get("HS_PORT") else _free_port()
    url = f"http://{settings.host}:{settings.port}/"
    server = ServerThread(app, settings.host, settings.port)
    server.start()
    if not server.wait_until_ready(url):
        log.error("server failed to start"); server.shutdown(); return
    log.info("server ready on loopback")

    try:
        from .shell.window import open_window
        open_window(url, on_closed=server.shutdown)
    except ImportError:
        log.warning("pywebview unavailable (headless) — running until interrupted")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        server.shutdown()
        log.info("shutdown complete")


def main() -> None:
    parser = argparse.ArgumentParser(prog="hellosienna")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args()
    if args.version:
        print(__version__)
        return
    run()


if __name__ == "__main__":
    main()
