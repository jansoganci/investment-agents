"""uv run python -m shared.bulletin --market                 the figures table (reads the database, writes nothing)
uv run python -m shared.bulletin --gather [--no-search]     what the bulletin would be built from: counts and the first items
                                                            (no model; the web searches cost 0.00075 $ each, --no-search skips them)"""

from __future__ import annotations

import sys

from shared import db as dbmod
from shared.bulletin import gather, market

USAGE = "usage: python -m shared.bulletin --market | --gather [--no-search]"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--market"]:
        conn = dbmod.connect_readonly()
        try:
            print(market.render(market.rows(conn)))
        finally:
            conn.close()
        return 0
    if argv[:1] == ["--gather"] and set(argv[1:]) <= {"--no-search"}:
        try:
            conn = dbmod.connect()
        except dbmod.DatabaseMissing as exc:
            print(f"BULLETIN · failed\n{exc}")
            return 1
        try:
            print(gather.describe(gather.gather(conn, searches="--no-search" not in argv)))
        finally:
            conn.close()
        return 0
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
