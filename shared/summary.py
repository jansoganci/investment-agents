"""The Sunday summary (roadmap section 3, "Telegram and Hermes" and "Agent 2 rules" 9): code only, read from the database.

    lines = summary.build(conn, day, portfolio_text, analysis_text, errors)
    summary.save(day, lines)           # Investing/Weekly/<day>-summary.md (the whole text; the Telegram message is cut at 4,096)

A section with nothing to say is left out, except the portfolio block and the spend line."""

from __future__ import annotations

import json
from datetime import date, timedelta

from shared import ai, clock, config, drive, notify

ORDER = {"weak": 0, "mid": 1, "solid": 2}
NAMES = ("mentions", "tone", "sector_tailwind", "news_flow", "quick_health")


def _section(title: str, body: list[str]) -> list[str]:
    return ["", title] + body if body else []


def candidates(conn) -> list[str]:
    rows = conn.execute(
        "SELECT s.ticker, s.company, s.added_by, c.score, c.mentions, c.tone, c.sector_tailwind, c.news_flow, c.quick_health FROM scores c "
        "JOIN stocks s ON s.id = c.stock_id WHERE c.week = (SELECT max(week) FROM scores) AND s.status = 'candidate' "
        "ORDER BY c.score DESC, s.ticker LIMIT 10").fetchall()
    return [f"- {t} {co or ''} — {sc}/10 (mentions {m} · tone {to} · tailwind {ta} · news {n} · health {h})" + (" · added by me" if by == "user" else "")
            for t, co, by, sc, m, to, ta, n, h in rows]


def grade_changes(conn, since: str) -> list[str]:
    rows = conn.execute(
        "SELECT s.ticker, e.date, e.grade, (SELECT p.grade FROM card_entries p WHERE p.stock_id = e.stock_id AND p.record = 'fundamental' "
        "AND p.id < e.id ORDER BY p.id DESC LIMIT 1), (SELECT count(*) FROM card_entries p WHERE p.stock_id = e.stock_id AND "
        "p.record = 'fundamental' AND p.id < e.id) FROM card_entries e JOIN stocks s ON s.id = e.stock_id "
        "WHERE e.record = 'fundamental' AND e.date >= ? ORDER BY s.ticker, e.id", (since,)).fetchall()
    out = []
    for ticker, day, grade, previous, before in rows:
        if before == 0:
            out.append(f"- {ticker}: first analysis, grade {grade} ({day})")
        elif previous != grade:
            out.append(f"- {ticker}: grade {previous} → {grade} ({day})")
    return out


def counter_lines(conn) -> tuple[list[str], list[str]]:
    run_at = conn.execute("SELECT max(run_at) FROM counts").fetchone()[0]
    if run_at is None:
        return [], []
    bar = int((config.settings().get("counter") or {}).get("card_mention_bar", 6))
    carded = conn.execute("SELECT key, posts_7d FROM counts WHERE run_at = ? AND kind = 'stock' AND has_card = 1 AND posts_7d >= ? "
                          "ORDER BY posts_7d DESC, key", (run_at, bar)).fetchall()
    non_us = conn.execute("SELECT label, posts_7d FROM counts WHERE run_at = ? AND kind = 'non_us' ORDER BY rank LIMIT 5", (run_at,)).fetchall()
    return ([f"- {t} ({n} posts)" for t, n in carded], [f"- {label} ({n} posts)" for label, n in non_us])


def tag_questions(conn) -> list[str]:
    waiting = [r[0] for r in conn.execute("SELECT tag FROM tags WHERE status = 'waiting' ORDER BY id")]
    other = [r[0] for r in conn.execute("SELECT tag FROM tags WHERE subsector = 'other' AND status = 'confirmed' ORDER BY id")]
    out = []
    if waiting:
        out.append(f"- {len(waiting)} tag(s) wait for you (US-looking companies the SEC check did not confirm): "
                   + ", ".join(waiting[:5]) + (" …" if len(waiting) > 5 else "") + " — send /tag")
    if other:
        out.append(f"- {len(other)} tag(s) fit no approved subsector: " + ", ".join(other[:5]) + (" …" if len(other) > 5 else "")
                   + " — add one with /subsector add <sector> <name>")
    return out


def unclear_data(conn) -> list[str]:
    open_rows = conn.execute("SELECT count(*) FROM missing_data WHERE status = 'open'").fetchone()[0]
    unclear = [r[0] for r in conn.execute("SELECT ticker FROM stocks WHERE status = 'watching' AND grade = 'unclear' ORDER BY ticker")]
    out = []
    if unclear:
        out.append("- grade unclear: " + ", ".join(unclear))
    if open_rows:
        out.append(f"- {open_rows} missing figure(s) are still open — send /missing")
    return out


def archive_reminders(conn) -> list[str]:
    out = []
    for sid, ticker in conn.execute("SELECT id, ticker FROM stocks WHERE status = 'watching' AND in_portfolio = 'no' ORDER BY ticker").fetchall():
        grades = [g for (g,) in conn.execute("SELECT grade FROM card_entries WHERE stock_id = ? AND record = 'fundamental' ORDER BY id DESC LIMIT 2", (sid,))]
        if len(grades) == 2 and all(g != "solid" for g in grades):
            out.append(f"- {ticker}: not solid on its last two cards ({grades[1]} → {grades[0]}) — archive it? /archive {ticker}")
    return out


def spend_line(conn) -> str:
    spent = ai.month_spend(conn)
    limit = (config.settings().get("budget") or {}).get("ai_monthly_max_usd")
    return f"AI spend this month: ${spent:.2f}" + (f" of ${limit}" if limit else "")


def build(conn, day: str | None = None, portfolio_text: str | None = None, analysis_text: str | None = None,
          errors: list[str] | tuple = ()) -> list[str]:
    day = day or clock.today_local()
    since = (date.fromisoformat(day) - timedelta(days=7)).isoformat()
    carded, non_us = counter_lines(conn)
    lines = [f"SUNDAY SUMMARY · {day}"]
    if errors:
        lines += ["", "THINGS THAT FAILED THIS WEEK"] + [f"- {e}" for e in errors]
    lines += _section("New candidates (a score is a ranking, not a buy):", candidates(conn))
    lines += _section("Card changes this week:", grade_changes(conn, since))
    if analysis_text:
        lines += ["", "Agent 3 this week:", analysis_text]
    lines += _section("Stocks with a card mentioned a lot:", carded)
    lines += _section("Non-US names mentioned a lot:", non_us)
    lines += _section("Questions for you:", tag_questions(conn))
    lines += _section("Data still unclear:", unclear_data(conn))
    lines += _section("Archive reminders:", archive_reminders(conn))
    lines += ["", "Portfolio:", portfolio_text or "(the portfolio run did not give a block this week)"]
    lines += ["", spend_line(conn)]
    return lines


def save(day: str, lines: list[str]):
    path = drive.weekly() / f"{day}-summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def latest() -> tuple[str, str] | None:
    """(file name, text) of the newest saved summary, or None."""
    folder = drive.weekly()
    files = sorted(folder.glob("*-summary.md")) if folder.exists() else []
    return (files[-1].name, files[-1].read_text(encoding="utf-8")) if files else None


def message(lines: list[str]) -> str:
    return notify.message(lines[0], lines[1:])
