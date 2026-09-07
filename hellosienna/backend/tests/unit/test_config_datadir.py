"""Acceptance #10, #16: data dir resolves under %LOCALAPPDATA% on Windows and is
never inside the repository."""
from __future__ import annotations

from pathlib import Path

from hellosienna.config import resolve_data_dir


def test_localappdata_wins_on_windows(monkeypatch, tmp_path):
    monkeypatch.delenv("HS_DATA_DIR", raising=False)
    fake_lad = tmp_path / "AppData" / "Local"
    monkeypatch.setenv("LOCALAPPDATA", str(fake_lad))
    resolved = resolve_data_dir()
    assert resolved == fake_lad / "HelloSienna"


def test_explicit_override_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("HS_DATA_DIR", str(tmp_path / "custom"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "ignored"))
    assert resolve_data_dir() == tmp_path / "custom"


def test_data_dir_is_not_inside_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("HS_DATA_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    resolved = resolve_data_dir().resolve()
    repo_root = Path(__file__).resolve().parents[3]  # .../hellosienna
    assert repo_root not in resolved.parents and resolved != repo_root
