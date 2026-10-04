"""uv run python -m shared.db init | upgrade | info"""

from __future__ import annotations

import sys

from shared import config
from shared import db as dbmod
from shared.db import migrations

USAGE = "usage: python -m shared.db init | upgrade | info"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in ("init", "upgrade", "info"):
        print(USAGE)
        return 2
    cmd = argv[0]
    if cmd == "init":
        path = dbmod.init()
        print(f"Database ready: {path} (version {migrations.latest()})")
        return 0
    if cmd == "upgrade":
        conn = dbmod._open(config.db_path()) if config.db_path().exists() else None
        if conn is None:
            print(f"No database at {config.db_path()}. Run: uv run python -m shared.db init")
            return 1
        before = dbmod.version(conn)
        applied = dbmod.upgrade(conn)
        conn.close()
        if applied:
            print(f"Upgraded from version {before} to {applied[-1]} (steps {', '.join(map(str, applied))}).")
        else:
            print(f"Already at version {before}; nothing to do.")
        return 0
    conn = dbmod.connect_readonly()
    try:
        print(f"Database: {config.db_path()}")
        print(f"Version: {dbmod.version(conn)} (code knows {migrations.latest()})")
        print(f"Journal mode: {conn.execute('PRAGMA journal_mode').fetchone()[0]}")
        for name in dbmod.tables(conn):
            count = conn.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
            print(f"  {name:<16} {count} rows")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
