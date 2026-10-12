"""uv run python -m agents.research            the weekly run: the Counter's top stocks without a card are scored and get a card
uv run python -m agents.research KO         one stock, as one I added myself (mentions and tone from the posts there are, news from the web)
Needs the Counter's latest run (python -m agents.counter) for the weekly run. Web search and the strong model cost about 0.1–0.3 $ a stock."""

from __future__ import annotations

import re
import sys

from agents.research import run
from shared import db as dbmod
from shared import notify, runlog

USAGE = "usage: python -m agents.research [TICKER]"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1 or (argv and not re.fullmatch(r"[A-Za-z0-9.\-]{1,10}", argv[0])):
        print(USAGE)
        return 2

    def work(job):
        conn = dbmod.connect()
        try:
            if argv:
                try:
                    o = run.research_one(conn, argv[0], added_by="user", run=job)
                except run.Refused as error:
                    return notify.message("RESEARCH", [str(error)])
                return notify.message(f"RESEARCH · {o.ticker}", o.lines() + [f"Card: {o.card_path}"])
            return run.weekly(conn, run=job)
        finally:
            conn.close()

    return runlog.job_main("research", work)


if __name__ == "__main__":
    sys.exit(main())
