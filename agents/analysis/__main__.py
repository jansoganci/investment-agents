"""uv run python -m agents.analysis KO               analyze one stock now (numbers only, as in phase 1)
uv run python -m agents.analysis KO --ai          the numbers + the AI parts (why answers, thesis, audits, sell suggestion)
uv run python -m agents.analysis --weekly [--ai]  every watching stock with a new filing (archived stocks never)
uv run python -m agents.analysis --drop-alerts    the pending drop alerts: latest filing against the thesis"""

from __future__ import annotations

import sys

from agents.analysis import run
from shared import db as dbmod
from shared import runlog

USAGE = "usage: python -m agents.analysis <TICKER> [--ai] | --weekly [--ai] | --drop-alerts"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    use_ai = "--ai" in argv
    args = [a for a in argv if a != "--ai"]
    if len(args) != 1 or (args[0] == "--drop-alerts" and use_ai):
        print(USAGE)
        return 2

    def work(r):
        conn = dbmod.connect()
        try:
            if args[0] == "--weekly":
                return run.weekly(conn, use_ai=use_ai, run=r)
            if args[0] == "--drop-alerts":
                return run.drop_alerts(conn, run=r)
            return run.analyze(conn, args[0], use_ai=use_ai, run=r, ask_missing=use_ai).text
        finally:
            conn.close()

    return runlog.job_main("analysis", work)


if __name__ == "__main__":
    sys.exit(main())
