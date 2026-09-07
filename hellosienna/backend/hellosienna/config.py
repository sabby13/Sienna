"""Configuration and private data-directory resolution (M0).

The private runtime data directory (SQLite DB, logs) must live under
%LOCALAPPDATA%\\HelloSienna on Windows and NEVER inside the repository
(M0 acceptance #10, #16). Resolution order:

  1. HS_DATA_DIR env var (explicit override — used by tests/CI).
  2. %LOCALAPPDATA%\\HelloSienna on Windows (LOCALAPPDATA env var present).
  3. Dev fallback: ~/.local/share/HelloSienna (non-Windows dev only).

The token is generated per launch and held in memory only.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

APP_DIR_NAME = "HelloSienna"


def resolve_data_dir() -> Path:
    """Resolve the private data directory. See module docstring for order."""
    override = os.environ.get("HS_DATA_DIR")
    if override:
        return Path(override).expanduser()

    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:  # Windows (the production target)
        return Path(localappdata) / APP_DIR_NAME

    # Dev/CI fallback on non-Windows hosts.
    return Path.home() / ".local" / "share" / APP_DIR_NAME


@dataclass
class Settings:
    data_dir: Path = field(default_factory=resolve_data_dir)
    host: str = "127.0.0.1"          # loopback only — never 0.0.0.0 (acceptance #5)
    port: int = 0                    # 0 => OS picks an ephemeral free port
    # Per-launch API token (header X-HS-Token). In memory only; never persisted.
    api_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    # Ollama runtime + model config (swappable; nothing assumes one provider serves both).
    ollama_base_url: str = "http://127.0.0.1:11434"
    chat_model: str = "qwen2.5:7b"
    embed_model: str = "nomic-embed-text"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "hellosienna.db"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
