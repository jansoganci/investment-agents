"""The read-only way for my free questions (roadmap section 3, "Telegram and Hermes"): Hermes may look, never change.

    uv run python -m shared.ask tables            every table with its columns
    uv run python -m shared.ask sql "SELECT …"    one read-only query
    uv run python -m shared.ask card KO           the text of a card

Three locks: the file is opened read-only (`mode=ro`), `query_only` is on, and an authorizer allows only reading
(no ATTACH, no PRAGMA, no writes).
"""

from __future__ import annotations

import sqlite3
import sys

from shared import db as dbmod
from shared import drive

MAX_ROWS = 200

_ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}


def _authorizer(action, *_):
    return sqlite3.SQLITE_OK if action in _ALLOWED else sqlite3.SQLITE_DENY


def _connect() -> sqlite3.Connection:
    conn = dbmod.connect_readonly()
    conn.set_authorizer(_authorizer)
    return conn


def query(sql: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    conn = _connect()
    try:
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description or []]
        return cols, cur.fetchmany(MAX_ROWS)
    finally:
        conn.close()


def tables_text() -> str:
    conn = dbmod.connect_readonly()  # PRAGMA table_info is needed here; the connection is still read-only
    try:
        lines = []
        for name in dbmod.tables(conn):
            cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{name}")')]
            lines.append(f"{name}: {', '.join(cols)}")
        return "\n".join(lines)
    finally:
        conn.close()


def card(ticker: str) -> str | None:
    path = drive.find_card(ticker.upper())
    return path.read_text(encoding="utf-8") if path else None


def _format(cols: list[str], rows: list[tuple]) -> str:
    out = ["\t".join(cols)] + ["\t".join("" if v is None else str(v) for v in r) for r in rows]
    if len(rows) == MAX_ROWS:
        out.append(f"(first {MAX_ROWS} rows only)")
    return "\n".join(out)


USAGE = 'usage: python -m shared.ask tables | sql "SELECT …" | card <TICKER>'


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["tables"]:
        print(tables_text())
        return 0
    if len(argv) == 2 and argv[0] == "sql":
        try:
            print(_format(*query(argv[1])))
        except sqlite3.Error as exc:
            print(f"Refused or failed (read-only): {exc}")
            return 1
        return 0
    if len(argv) == 2 and argv[0] == "card":
        text = card(argv[1])
        if text is None:
            print(f"No card for {argv[1].upper()}.")
            return 1
        print(text)
        return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
