"""Acceptance #10, #11, #12: DB created under the private data dir, migration
applies to head, and a write/read round-trip succeeds."""
from __future__ import annotations

from sqlalchemy import inspect, text

from hellosienna.config import Settings
from hellosienna.core.clock import TestClock, isoformat_utc
from hellosienna.persistence.db import app_meta_get, app_meta_set, make_engine
from hellosienna.persistence.migrate import make_alembic_config, upgrade_to_head


def test_migration_creates_app_meta_and_db_file(tmp_path):
    settings = Settings(data_dir=tmp_path / "HelloSienna")
    upgrade_to_head(settings.db_path)

    assert settings.db_path.exists()
    # DB file lives under the configured private data dir, not the repo.
    assert str(settings.db_path).startswith(str(settings.data_dir))

    engine = make_engine(settings.db_path)
    tables = set(inspect(engine).get_table_names())
    assert "app_meta" in tables
    # M0 non-goal check: no domain tables yet.
    for forbidden in ("memory", "evidence", "person", "conversation", "message",
                      "event", "open_thread"):
        assert forbidden not in tables, f"unexpected domain table at M0: {forbidden}"

    # alembic is at head
    from alembic.script import ScriptDirectory
    from alembic.runtime.migration import MigrationContext
    script = ScriptDirectory.from_config(make_alembic_config(settings.db_path))
    with engine.connect() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
    assert current == script.get_current_head() == "0001_app_meta"
    engine.dispose()


def test_write_read_roundtrip(tmp_path):
    settings = Settings(data_dir=tmp_path / "HelloSienna")
    upgrade_to_head(settings.db_path)
    engine = make_engine(settings.db_path)
    now = isoformat_utc(TestClock().now())
    with engine.begin() as conn:
        app_meta_set(conn, "schema_initialized_at", now, now)
    with engine.connect() as conn:
        assert app_meta_get(conn, "schema_initialized_at") == now
    engine.dispose()


def test_foreign_keys_pragma_enabled(tmp_path):
    settings = Settings(data_dir=tmp_path / "HelloSienna")
    upgrade_to_head(settings.db_path)
    engine = make_engine(settings.db_path)
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
    engine.dispose()
