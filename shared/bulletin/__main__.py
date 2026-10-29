"""uv run python -m shared.bulletin --market                 the figures table (reads the database, writes nothing)
uv run python -m shared.bulletin --gather [--no-search]     what the bulletin would be built from: counts and the first items
                                                            (no model; the web searches cost 0.00075 $ each, --no-search skips them)
uv run python -m shared.bulletin --draft                    gather, write, check and translate the items; prints every item with its
                                                            sources and flags (about 0.1 $; saves nothing, sends nothing)"""

from __future__ import annotations

import sys

from shared import db as dbmod
from shared import runlog
from shared.bulletin import gather, market, translate, write

USAGE = "usage: python -m shared.bulletin --market | --gather [--no-search] | --draft"


def draft_text(run) -> str:
    conn = dbmod.connect()
    try:
        pack = gather.gather(conn, run=run)
        draft = translate.translate(write.write(pack, run=run, conn=conn), run=run, conn=conn)
        cited = {s for i in draft.items for s in i.sources}
        left = [f"  {p.id} · {p.site} · {p.title[:80]}" for p in pack.posts + pack.web if p.id not in cited]
        return (gather.describe(pack).split("\n", 2)[1] + "\n\n" + write.describe(draft)
                + f"\n\nNOT USED ({len(left)} of {len(pack.posts) + len(pack.web)} pieces):\n" + "\n".join(left) + f"\n\ncost: ${run.cost_usd:.4f}")
    finally:
        conn.close()


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
    if argv == ["--draft"]:
        return runlog.job_main("bulletin_draft", draft_text)
    print(USAGE)
    return 2


if __name__ == "__main__":
    sys.exit(main())
