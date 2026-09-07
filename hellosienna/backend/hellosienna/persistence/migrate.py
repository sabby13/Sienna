"""Programmatic Alembic runner (M0, acceptance #11).

Lets the launcher and tests apply migrations without a shell, using an explicit
absolute script_location and DB URL.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

_BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../backend


def make_alembic_config(db_path: Path) -> Config:
    cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return cfg


def upgrade_to_head(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(make_alembic_config(db_path), "head")
