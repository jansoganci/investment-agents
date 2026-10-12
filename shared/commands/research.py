"""/candidates (roadmap section 10.2; phase 5): the latest week's scores with their reasons, best first. Read only."""

from __future__ import annotations

import json

from shared.commands import Command, register

NAMES = ("mentions", "tone", "sector_tailwind", "news_flow", "quick_health")


def _candidates(conn, args):
    week = conn.execute("SELECT max(week) FROM scores").fetchone()[0]
    if week is None:
        return "CANDIDATES\nNo stock has been scored yet (agent 2 runs on Sunday: python -m agents.research)."
    rows = conn.execute(
        "SELECT s.ticker, s.company, s.status, s.added_by, c.mentions, c.tone, c.sector_tailwind, c.news_flow, c.quick_health, c.score, "
        "c.reasons FROM scores c JOIN stocks s ON s.id = c.stock_id WHERE c.week = ? ORDER BY c.score DESC, s.ticker", (week,)).fetchall()
    lines = [f"CANDIDATES · week {week} · {len(rows)} scored"]
    for i, (ticker, company, status, added_by, *points, total, reasons) in enumerate(rows, 1):
        why = json.loads(reasons)
        label = f"{i}. {ticker} {company or ''} — {total}/10 ({' · '.join(f'{n.replace('_', ' ')} {p}' for n, p in zip(NAMES, points))})"
        lines.append(label.replace("  ", " ") + (" · added by me" if added_by == "user" else "") + f" · {status}")
        lines += [f"   {n.replace('_', ' ')}: {why[n][:200]}" for n in NAMES if n in why]
    lines.append("Start watching one: /watch TICKER. The score is a ranking, not a buy.")
    return "\n".join(lines)


register(Command("candidates", "This week's candidates with scores and reasons", "/candidates", phase=5, info=_candidates))


def _summary(conn, args):
    from shared import config, notify, summary

    try:
        found = summary.latest()
    except config.SettingMissing as exc:
        from shared.commands import Refused

        raise Refused(str(exc)) from exc
    if found is None:
        return "SUMMARY\nNo Sunday summary has been written yet (python -m shared.sunday)."
    name, text = found
    lines = text.splitlines()
    return notify.message(lines[0], lines[1:])


register(Command("summary", "Shows the latest Sunday summary again", "/summary", phase=6, info=_summary))
