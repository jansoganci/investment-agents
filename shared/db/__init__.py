"""The SQLite database: the contract between the agents (roadmap section 5).

- WAL mode + a wait time: readers never wait, a second writer waits instead of failing.
- A version number (`PRAGMA user_version`) and numbered upgrade steps (`migrations.py`), applied on start.
- An upgrade takes the write lock first (a second job waits, then finds nothing to do), runs with the foreign-key
  check off (so a table can be rebuilt), checks every link before it commits, and saves a full copy to
  `<data_dir>/pre-upgrade/` first. A failing step changes nothing.
"""

from __future__ import annotations

import os
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
    conn.execute("PRAGMA recursive_triggers = ON")  # so INSERT OR REPLACE cannot get round the no-delete triggers
    return conn


def version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def copy_to(conn: sqlite3.Connection, target: Path) -> Path:
    """A consistent copy with SQLite's own backup command, as one self-contained file (no -wal / -shm beside it).
    Written under a temporary name first, so a half-written copy never carries the final name."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.unlink(missing_ok=True)  # our own leftover from a broken run
    dest = sqlite3.connect(tmp)
    try:
        conn.backup(dest)
        dest.execute("PRAGMA journal_mode = DELETE")
    finally:
        dest.close()
    os.replace(tmp, target)
    return target


def _copy_file(source: Path, target: Path) -> Path:
    """Copy through a separate read connection (works while another connection holds the write lock)."""
    src = sqlite3.connect(source, timeout=_timeout_ms() / 1000)
    try:
        return copy_to(src, target)
    finally:
        src.close()


def _statements(sql: str):
    """Split a step into single statements; `CREATE TRIGGER … END;` and `;` inside text stay whole."""
    parts = sql.split(";")
    buf = ""
    for i, part in enumerate(parts):
        buf += part
        if i < len(parts) - 1:
            buf += ";"
            if sqlite3.complete_statement(buf):
                yield buf
                buf = ""
    if buf.strip():
        yield buf  # an unfinished last statement: SQLite reports the error


def upgrade(conn: sqlite3.Connection, steps: list[tuple[int, str]] | None = None) -> list[int]:
    """Apply every step above the current version in one transaction. Returns the applied numbers."""
    steps = migrations.STEPS if steps is None else steps
    current = version(conn)
    if not any(n > current for n, _ in steps):
        return []
    conn.commit()
    old_level = conn.isolation_level
    fk_was_on = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    conn.isolation_level = None  # this function opens and closes the transaction itself
    copy = None
    try:
        conn.execute("PRAGMA foreign_keys = OFF")  # a no-op inside a transaction, so before BEGIN
        conn.execute("BEGIN IMMEDIATE")  # the write lock: a second job waits here
        try:
            current = version(conn)  # read again under the lock: another job may have done it already
            todo = [(n, sql) for n, sql in steps if n > current]
            if todo and current > 0:
                stamp = clock.now_utc().strftime("%Y%m%dT%H%M%SZ")
                path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
                copy = _copy_file(path, config.data_dir() / "pre-upgrade" / f"v{current}-{stamp}.sqlite")
            for n, sql in todo:
                for statement in _statements(sql):
                    conn.execute(statement)
                broken = conn.execute("PRAGMA foreign_key_check").fetchall()
                if broken:
                    raise sqlite3.IntegrityError(f"upgrade step {n} breaks links between tables: {broken[:3]}")
                conn.execute(f"PRAGMA user_version = {int(n)}")
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            if copy is not None:
                copy.unlink(missing_ok=True)  # nothing changed, so the copy is not needed
            raise
        return [n for n, _ in todo]
    finally:
        conn.execute(f"PRAGMA foreign_keys = {'ON' if fk_was_on else 'OFF'}")
        conn.isolation_level = old_level


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
