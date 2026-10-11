"""uv run python -m agents.counter           count the last 7 days, store the run in `counts`, print the ranking
uv run python -m agents.counter --show    print the latest stored run (changes nothing)"""

from __future__ import annotations

import sys

from agents.counter import block, count
from shared import db as dbmod
from shared import runlog

USAGE = "usage: python -m agents.counter [--show]"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv not in ([], ["--show"]):
        print(USAGE)
        return 2
    if argv == ["--show"]:
        conn = dbmod.connect_readonly()
        try:
            r = count.latest(conn)
            print(block.render(r, f"COUNTER · stored run of {r.run_at}") if r else "The Counter has not run yet.")
        finally:
            conn.close()
        return 0

    def work(_run):
        conn = dbmod.connect()
        try:
            return block.render(count.count(conn))
        finally:
            conn.close()

    return runlog.job_main("counter", work)


if __name__ == "__main__":
    sys.exit(main())
