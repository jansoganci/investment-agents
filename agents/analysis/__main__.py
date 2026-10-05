"""uv run python -m agents.analysis KO        analyze one stock now (numbers only; no AI in phase 1)
uv run python -m agents.analysis --weekly    every watching stock with a new filing (archived stocks never)"""

from __future__ import annotations

import sys

from agents.analysis import run
from shared import db as dbmod
from shared import runlog

USAGE = "usage: python -m agents.analysis <TICKER> | --weekly"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(USAGE)
        return 2

    def work(_run):
        conn = dbmod.connect()
        try:
            if argv[0] == "--weekly":
                return run.weekly(conn)
            return run.analyze(conn, argv[0]).text
        finally:
            conn.close()

    return runlog.job_main("analysis", work)


if __name__ == "__main__":
    sys.exit(main())
