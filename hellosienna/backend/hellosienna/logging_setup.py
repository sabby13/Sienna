"""Logging setup (M0): console + a file under the private log dir.

The per-launch API token must never be written to logs (Change 1 / acceptance #6),
so this module installs a filter that redacts it if it ever appears in a record.
"""

from __future__ import annotations

import logging
from pathlib import Path


class _RedactTokenFilter(logging.Filter):
    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._token:
            return True
        try:
            rendered = record.getMessage()  # applies %-args
        except Exception:
            return True
        if self._token in rendered:
            record.msg = rendered.replace(self._token, "<redacted-token>")
            record.args = ()
        return True


def setup_logging(log_dir: Path, token: str | None = None, level: int = logging.INFO) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "hellosienna.log"

    root = logging.getLogger()
    root.setLevel(level)
    # Idempotent: clear handlers so repeated setup (tests) doesn't duplicate.
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)

    if token:
        redact = _RedactTokenFilter(token)
        console.addFilter(redact)
        file_handler.addFilter(redact)

    root.addHandler(console)
    root.addHandler(file_handler)
    return log_file
