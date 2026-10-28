"""uv run python -m shared.bulletin --market     the figures table (reads the database, writes nothing)"""

from __future__ import annotations

import sys

from shared import db as dbmod
from shared.bulletin import market


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--market"]:
        conn = dbmod.connect_readonly()
        try:
            print(market.render(market.rows(conn)))
        finally:
            conn.close()
        return 0
    print("usage: python -m shared.bulletin --market")
    return 2


if __name__ == "__main__":
    sys.exit(main())
