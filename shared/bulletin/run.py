"""The morning bulletin as a job (docs/BULLETIN_PLAN.md slice 5): gather → write → check → translate → render → save → print.

    uv run python -m shared.bulletin                 build today's bulletin, save it, print it (Hermes delivers what is printed)
    uv run python -m shared.bulletin --force         build it again (the saved one of today is marked void)
    uv run python -m shared.bulletin --dry           build and print, save nothing
    uv run python -m shared.bulletin --show          print the last saved bulletin again

A second run on the same day prints the saved text and spends nothing. The window of a bulletin starts where the previous saved one
ended (at most 4 days back; the first one: the last weekday's bulletin time). A bulletin whose writer failed is printed with a
warning but not saved, so the next run covers that window too. It changes nothing in the system: no card, score or signal.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from shared import clock, drive
from shared.ai import AIError
from shared.bulletin import gather, market, render, translate, write

MAX_GAP_DAYS = 4


def window_start(conn, now: datetime, day: str) -> datetime:
    """Where this bulletin's window starts: the end of the last saved bulletin of an EARLIER day, or the default."""
    row = conn.execute("SELECT window_end FROM bulletins WHERE void = 0 AND day < ? ORDER BY day DESC LIMIT 1", (day,)).fetchone()
    if not row:
        return gather.window_start(now)
    return max(clock.parse_utc(row[0]), now - timedelta(days=MAX_GAP_DAYS))


def saved(conn, day: str) -> str | None:
    row = conn.execute("SELECT turkish FROM bulletins WHERE day = ? AND void = 0", (day,)).fetchone()
    return row[0] if row else None


def last_saved(conn) -> str | None:
    row = conn.execute("SELECT turkish FROM bulletins WHERE void = 0 ORDER BY day DESC LIMIT 1").fetchone()
    return row[0] if row else None


def save(conn, day: str, pack, draft, rendered, cost: float, now: datetime) -> None:
    """The row in `bulletins` (an earlier row of the same day is marked void) and the Turkish file in Drive `Bulletin/`."""
    notes = pack.notes + draft.notes
    conn.execute("UPDATE bulletins SET void = 1 WHERE day = ? AND void = 0", (day,))
    english = [{"section": i.section, "text": i.text, "sources": list(i.sources), "ticker": i.ticker, "when": i.when, "group": i.group,
                "rank": i.rank, "thesis_point": i.thesis_point, "flags": i.flags, "turkish": i.turkish, "turkish_flag": i.turkish_flag}
               for i in draft.items]
    conn.execute("INSERT INTO bulletins (day, window_start, window_end, english, turkish, sources, notes, cost_usd, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (day, pack.window_start, pack.window_end, json.dumps(english, ensure_ascii=False), rendered.text,
                  json.dumps(rendered.sources, ensure_ascii=False), json.dumps(notes, ensure_ascii=False), cost, clock.utc_iso(now)))
    conn.commit()
    folder = drive.bulletin()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{day}.md").write_text(f"---\nbulletin: {day}\npublish: no\n---\n\n{rendered.text}\n", encoding="utf-8")


def build(conn, run, *, now: datetime | None = None, force: bool = False, dry: bool = False, gather_kwargs: dict | None = None) -> str:
    """Today's bulletin text. `gather_kwargs` lets tests stand in for the web, SEC and Yahoo."""
    now = now or clock.now_utc()
    day = clock.today_local(now)
    if not force and not dry and (text := saved(conn, day)) is not None:
        return text
    pack = gather.gather(conn, now, since=window_start(conn, now, day), run=run, **(gather_kwargs or {}))
    failed = None
    market_text = market.render(market.rows(conn))
    try:
        draft = write.write(pack, run=run, conn=conn, now=now, market_text=market_text)
    except (AIError, ValueError) as exc:
        failed = f"{type(exc).__name__}: {exc}"
        draft = write.Draft(notes=[f"Writer failed ({failed[:200]})"])
    translate.translate(draft, run=run, conn=conn)
    rendered = render.render(pack, draft, market_text, now, failed)
    if not dry and not failed:
        save(conn, day, pack, draft, rendered, run.cost_usd, now)
    return rendered.text
