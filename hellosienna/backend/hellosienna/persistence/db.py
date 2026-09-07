"""SQLite engine + the single place PRAGMAs are enforced (Contract §1.1, flag #7).

Every connection gets foreign_keys=ON (SQLite does NOT enforce FKs otherwise),
WAL journal mode (lets background cognition read while foreground writes), and a
busy_timeout. Because all connections come from here, no code path can forget them.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import Connection


def _apply_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA busy_timeout=5000;")
    cur.close()


def make_engine(db_path: Path) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    event.listen(engine, "connect", _apply_pragmas)
    return engine


# ---- app_meta helpers (M0 write/read round-trip; acceptance #12) ----
def app_meta_set(conn: Connection, key: str, value: str, updated_at: str) -> None:
    conn.execute(
        text(
            "INSERT INTO app_meta(key, value, updated_at) VALUES (:k, :v, :u) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at"
        ),
        {"k": key, "v": value, "u": updated_at},
    )


def app_meta_get(conn: Connection, key: str) -> str | None:
    row = conn.execute(
        text("SELECT value FROM app_meta WHERE key = :k"), {"k": key}
    ).fetchone()
    return row[0] if row else None
