"""Acceptance #6/#15: logging exists (file under log dir) and the per-launch token
is never written to logs (redaction filter)."""
from __future__ import annotations

import logging

from hellosienna.logging_setup import setup_logging


def test_log_file_created_and_token_redacted(tmp_path):
    token = "SECRET-TOKEN-abc123"
    log_file = setup_logging(tmp_path / "logs", token=token)
    assert log_file.exists()

    logging.getLogger("test").info("attempting with token %s in message", token)
    for h in logging.getLogger().handlers:
        h.flush()

    contents = log_file.read_text(encoding="utf-8")
    assert token not in contents
    assert "<redacted-token>" in contents
