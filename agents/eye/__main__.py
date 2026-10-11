"""uv run python -m agents.eye                  one pass: the new posts of both sites (slow: up to ~35 minutes)
uv run python -m agents.eye --accept-many     the same, but read even when more than 200 new addresses are found
The first run of a site only records its addresses as seen (nothing is read)."""

from __future__ import annotations

import sys

from agents.eye import run
from shared import db as dbmod
from shared import runlog

USAGE = "usage: python -m agents.eye [--accept-many]"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv not in ([], ["--accept-many"]):
        print(USAGE)
        return 2

    def work(_run):
        conn = dbmod.connect()
        try:
            return run.run_pass(conn, accept_many="--accept-many" in argv).message()
        finally:
            conn.close()

    return runlog.job_main("eye", work)


if __name__ == "__main__":
    sys.exit(main())
