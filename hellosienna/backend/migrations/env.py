"""Alembic environment (M0).

Resolves the DB URL from the private data dir (config.resolve_data_dir) unless
sqlalchemy.url is set explicitly, and enforces foreign_keys=ON for migrations too.
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import event, pool

# Make the hellosienna package importable when alembic runs from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hellosienna.config import resolve_data_dir  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # M0 migrations are hand-written; no ORM autogenerate.


def _db_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    return f"sqlite:///{resolve_data_dir() / 'hellosienna.db'}"


def _apply_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.close()


def run_migrations_offline() -> None:
    context.configure(url=_db_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_db_url(), poolclass=pool.NullPool, future=True)
    event.listen(engine, "connect", _apply_pragmas)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
