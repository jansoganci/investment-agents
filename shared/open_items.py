"""The Wednesday message: everything that waits for me (my decision, 2026-11-01), code only, read from the database.

    uv run python -m shared.open_items             Hermes runs it on Wednesday 20:00 Turkey time (docs/SCHEDULE.md)
    uv run python -m shared.open_items --day 2026-11-04

Sections, in this order: my holdings, the stocks I watch, the candidates, the rest. Missing figures, tags that wait for me, documents
for non-US companies, unclear grades, archive reminders. A question about a candidate I do not watch drops after 4 weeks (or at once
when I archive that stock). "Resolved since last time" compares with the list saved the week before. The message is never cut:
Hermes sends a long one in parts. The commands are written without the slash (Hermes takes "/…" as its own command)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta

from shared import clock, drive, notify, runlog, summary
from shared import db as dbmod
from agents.analysis import ask

DROP_AFTER_DAYS = 28            # a question about a candidate I do not watch
SECTIONS = ("MY HOLDINGS", "STOCKS I WATCH", "CANDIDATES")


@dataclass
class Items:
    missing: dict = field(default_factory=dict)       # section → {ticker: [(key, line)]}
    tags: list = field(default_factory=list)           # [(key, line)]
    other: list = field(default_factory=list)          # lines (documents wanted, subsectors, unclear grades, archive reminders)
    other_n: int = 0                                   # how many of those lines are items (a heading is not one)
    hidden: int = 0                                    # candidate questions older than 4 weeks (not shown)
    has_candidates: bool = False

    def keys(self) -> set[str]:
        out = {key for per in self.missing.values() for rows in per.values() for key, _ in rows}
        return out | {key for key, _ in self.tags}

    def count(self) -> int:
        return len(self.keys()) + self.other_n


def _section_of(status: str, in_portfolio: str) -> str | None:
    if in_portfolio == "yes":
        return SECTIONS[0]
    return {"watching": SECTIONS[1], "candidate": SECTIONS[2]}.get(status)      # archived → None: not asked any more


def collect(conn, day: str | None = None) -> Items:
    day = day or clock.today_local()
    limit = (date.fromisoformat(day) - timedelta(days=DROP_AFTER_DAYS)).isoformat()
    items = Items()
    for row in ask.pending(conn):
        stock = conn.execute("SELECT status, in_portfolio FROM stocks WHERE id = ?", (row["stock_id"],)).fetchone()
        section = _section_of(*stock)
        if section is None:
            continue
        created = conn.execute("SELECT created_at FROM missing_data WHERE id = ?", (row["id"],)).fetchone()[0] or ""
        if section == SECTIONS[2] and created[:10] < limit:
            items.hidden += 1
            continue
        items.has_candidates |= section == SECTIONS[2]
        name, _why, where = ask._help(row["figure"])
        year = row["year"] or "?"
        cmd_year = year[4:] if year.startswith("TTM ") else year
        ttm = "TTM " if year.startswith("TTM ") else ""
        line = (f"- {year} · {name} ({where}) → data {row['ticker']} {ttm}{cmd_year} {row['figure']} <value, e.g. 0.25bn>")
        key = f"missing|{row['ticker']}|{year}|{row['figure']}"
        items.missing.setdefault(section, {}).setdefault(row["ticker"], []).append((key, line))
    for tag, note in conn.execute("SELECT tag, note FROM tags WHERE status = 'waiting' ORDER BY id"):
        items.tags.append((f"tag|{tag}", f"- {tag} — {note or 'the SEC check did not confirm it'} → tag {tag} company <TICKER>  "
                                         f"(or: tag {tag} company non-us)"))
    _carded, non_us = summary.counter_lines(conn)
    if non_us:
        items.other.append("Non-US companies mentioned a lot (no card: the system has no filings for them). For each, please find and "
                           "send the last annual report, the last interim report and the latest investor presentation:")
        items.other += non_us
        items.other_n += len(non_us)
    subsectors = [line.replace(" — add one with /subsector add", " — add one with: subsector add")
                  for line in summary.tag_questions(conn) if "fit no approved subsector" in line]
    items.other += subsectors
    unclear = [r[0] for r in conn.execute("SELECT ticker FROM stocks WHERE status = 'watching' AND grade = 'unclear' ORDER BY ticker")]
    if unclear:
        items.other.append("Grade unclear: " + ", ".join(unclear))
    reminders = [line.replace("/archive ", "archive ") for line in summary.archive_reminders(conn)]
    items.other += reminders
    items.other_n += len(subsectors) + len(unclear) + len(reminders)
    return items


def _resolved(conn, previous: set[str], current: set[str]) -> list[str]:
    """The items of last time that are closed now (not just hidden): a figure no longer open, a tag no longer waiting."""
    out = []
    for key in sorted(previous - current):
        kind, *rest = key.split("|")
        if kind == "missing":
            ticker, year, figure = rest
            still = conn.execute("SELECT 1 FROM missing_data m JOIN stocks s ON s.id = m.stock_id WHERE upper(s.ticker) = ? AND m.year = ? "
                                 "AND m.figure = ? AND m.status = 'open'", (ticker.upper(), year, figure)).fetchone()
            given = conn.execute("SELECT 1 FROM financials f JOIN stocks s ON s.id = f.stock_id WHERE upper(s.ticker) = ? AND f.figure = ? "
                                 "AND f.period_end = ? AND f.source = 'user' AND f.void = 0", (ticker.upper(), figure, year)).fetchone()
            if not still or given:
                out.append(f"{ticker} {year} {figure}")
        elif kind == "tag":
            row = conn.execute("SELECT status FROM tags WHERE tag = ?", (rest[0],)).fetchone()
            if row and row[0] != "waiting":
                out.append(f"tag {rest[0]}")
    return out


def _previous(day: str) -> set[str]:
    folder = drive.weekly()
    files = sorted(f for f in folder.glob("*-open-items.json") if f.name[:10] < day) if folder.exists() else []
    if not files:
        return set()
    try:
        return set(json.loads(files[-1].read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def build(conn, day: str | None = None) -> tuple[list[str], Items]:
    day = day or clock.today_local()
    items = collect(conn, day)
    previous = _previous(day)
    resolved = _resolved(conn, previous, items.keys()) if previous else []
    if not items.count():
        lines = [f"OPEN ITEMS · {day} — nothing open"]
    else:
        lines = [f"OPEN ITEMS · {day} · {items.count()} item(s)"]
    if items.missing:
        lines += ["SEC's data does not have the figures below; a missing figure is never counted as zero."]
    if resolved:
        lines += ["", f"Resolved since last time: {len(resolved)} ({', '.join(resolved[:8])}{' …' if len(resolved) > 8 else ''})"]
    for section in SECTIONS:
        per = items.missing.get(section)
        if not per:
            continue
        lines += ["", section]
        for ticker, rows in sorted(per.items()):
            lines.append(f"{ticker}")
            lines += [f"  {line}" for _key, line in rows]
    if items.tags:
        lines += ["", f"TAGS THAT WAIT FOR ME ({len(items.tags)}) — tell me which stock each name is:"] + [line for _k, line in items.tags]
    if items.other:
        lines += ["", "OTHER"] + [line if line.startswith(("-", "Non-US", "Grade", "Archive")) else f"- {line}" for line in items.other]
    if items.has_candidates or items.hidden:
        lines += ["", f"A question about a candidate I do not watch drops after {DROP_AFTER_DAYS // 7} weeks"
                      + (f" ({items.hidden} dropped this time)" if items.hidden else "")
                      + "; to drop one now, write: archive <TICKER>."]
    return lines, items


def save(day: str, lines: list[str], items: Items):
    folder = drive.weekly()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{day}-open-items.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / f"{day}-open-items.json").write_text(json.dumps(sorted(items.keys())), encoding="utf-8")
    return path


def run(day: str | None = None) -> str:
    day = day or clock.today_local()
    conn = dbmod.connect()
    try:
        lines, items = build(conn, day)
    finally:
        conn.close()
    try:
        save(day, lines, items)
    except Exception as exc:  # noqa: BLE001 — a Drive problem must not hide the message
        lines.append(f"(the list could not be saved to Drive: {exc})")
    return notify.message(lines[0], lines[1:], cut=False)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    day = None
    if argv[:1] == ["--day"] and len(argv) == 2:
        day = argv[1]
    elif argv:
        print("usage: python -m shared.open_items [--day YYYY-MM-DD]")
        return 2
    return runlog.job_main("open_items", lambda _run: run(day))


if __name__ == "__main__":
    sys.exit(main())
