"""The SQLite database: the contract between the agents (roadmap section 5).

- WAL mode + a wait time: readers never wait, a second writer waits instead of failing.
- A version number (`PRAGMA user_version`) and numbered upgrade steps (`migrations.py`), applied on start.
- Before an upgrade a full copy goes to `<data_dir>/pre-upgrade/`; a failing step changes nothing.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from shared import clock, config
from shared.db import migrations


class DatabaseMissing(RuntimeError):
    pass


def _timeout_ms() -> int:
    return int(config.settings()["database"]["busy_timeout_ms"])


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=_timeout_ms() / 1000)
    conn.execute(f"PRAGMA busy_timeout = {_timeout_ms()}")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def copy_to(conn: sqlite3.Connection, target: Path) -> Path:
    """A consistent copy with SQLite's own backup command."""
    target.parent.mkdir(parents=True, exist_ok=True)
    dest = sqlite3.connect(target)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def upgrade(conn: sqlite3.Connection, steps: list[tuple[int, str]] | None = None) -> list[int]:
    """Apply every step above the current version, each in its own transaction. Returns the applied numbers."""
    steps = migrations.STEPS if steps is None else steps
    current = version(conn)
    todo = [(n, sql) for n, sql in steps if n > current]
    if not todo:
        return []
    if current > 0:
        stamp = clock.now_utc().strftime("%Y%m%dT%H%M%SZ")
        copy_to(conn, config.data_dir() / "pre-upgrade" / f"v{current}-{stamp}.sqlite")
    applied = []
    for n, sql in todo:
        conn.commit()
        try:
            conn.executescript(f"BEGIN;\n{sql}\n;PRAGMA user_version = {int(n)};\nCOMMIT;")
        except sqlite3.Error:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        applied.append(n)
    return applied


def init() -> Path:
    """Create the database (or upgrade it). Safe to run again: no row is touched."""
    path = config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _open(path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        upgrade(conn)
    finally:
        conn.close()
    return path


def connect() -> sqlite3.Connection:
    """A write connection. Applies pending upgrade steps on start."""
    path = config.db_path()
    if not path.exists():
        raise DatabaseMissing(f"No database at {path}. Run: uv run python -m shared.db init")
    conn = _open(path)
    upgrade(conn)
    return conn


def connect_readonly() -> sqlite3.Connection:
    """A connection that cannot write (for free questions and information commands)."""
    path = config.db_path()
    if not path.exists():
        raise DatabaseMissing(f"No database at {path}. Run: uv run python -m shared.db init")
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=_timeout_ms() / 1000)
    conn.execute(f"PRAGMA busy_timeout = {_timeout_ms()}")
    conn.execute("PRAGMA query_only = ON")
    return conn


def tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    return [r[0] for r in rows]
