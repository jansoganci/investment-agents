"""uv run python -m agents.portfolio            the weekly run (Sunday, with the Friday close): ledger, alerts, new money, snapshot
uv run python -m agents.portfolio --show     the block with the latest closes (changes nothing; the same as /portfolio)"""

from __future__ import annotations

import sys

from agents.portfolio import run
from shared import db as dbmod
from shared import runlog

USAGE = "usage: python -m agents.portfolio [--show]"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv not in ([], ["--show"]):
        print(USAGE)
        return 2
    if argv == ["--show"]:
        conn = dbmod.connect_readonly()
        try:
            print(run.on_demand(conn))
        finally:
            conn.close()
        return 0

    def work(_run):
        conn = dbmod.connect()
        try:
            return run.weekly(conn)
        finally:
            conn.close()

    return runlog.job_main("portfolio", work)


if __name__ == "__main__":
    sys.exit(main())
