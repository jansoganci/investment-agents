"""Immediate messages (roadmap, "Telegram and Hermes" and "Agent 2 rules" 9). Hermes runs this every hour; it prints nothing when there is
nothing new, and each alert is printed once (`alerts_sent`). Only events of the last 2 days are looked at, so a first run does not repeat
old history.

    a holding's grade dropped · a stock became solid (the green list) · a drop alert is waiting for agent 3 · the auditor disagreed on a
    card · OpenRouter spend reached the warning (10 $)

An agent error already reaches Telegram by itself (`runlog.job_main`)."""

from __future__ import annotations

import sys
from datetime import timedelta

from shared import ai, clock, config, notify, runlog
from shared import db as dbmod

RECENT_DAYS = 2
RANK = {"weak": 0, "mid": 1, "solid": 2}


def _recent_day(now) -> str:
    return (now - timedelta(days=RECENT_DAYS)).date().isoformat()


def _previous(conn, stock_id: int, entry_id: int) -> str | None:
    row = conn.execute("SELECT grade FROM card_entries WHERE stock_id = ? AND record = 'fundamental' AND id < ? ORDER BY id DESC LIMIT 1",
                       (stock_id, entry_id)).fetchone()
    return row[0] if row else None


def pending(conn, now=None) -> list[tuple[str, str]]:
    now = now or clock.now_utc()
    since_day, since = _recent_day(now), clock.utc_iso(now - timedelta(days=RECENT_DAYS))
    out: list[tuple[str, str]] = []

    for entry_id, stock_id, ticker, day, grade, held, status in conn.execute(
            "SELECT e.id, e.stock_id, s.ticker, e.date, e.grade, s.in_portfolio, s.status FROM card_entries e JOIN stocks s ON s.id = e.stock_id "
            "WHERE e.record = 'fundamental' AND e.date >= ? ORDER BY e.id", (since_day,)).fetchall():
        previous = _previous(conn, stock_id, entry_id)
        if held == "yes" and grade in RANK and previous in RANK and RANK[grade] < RANK[previous]:
            out.append((f"grade_drop:{entry_id}", f"GRADE DROP · {ticker}: {previous} → {grade} ({day}). It is in your portfolio: read its "
                                                  "card and its sell triggers. The decision is yours."))
        if status == "watching" and grade == "solid" and previous != "solid":
            out.append((f"solid:{entry_id}", f"GREEN LIST · {ticker} is solid now ({day}). A grade is not a buy; read its card."))

    for signal_id, ticker, day, detail in conn.execute(
            "SELECT g.id, s.ticker, g.date, g.detail FROM signals g JOIN stocks s ON s.id = g.stock_id "
            "WHERE g.kind = 'drop_alert' AND g.status = 'pending' AND g.date >= ? ORDER BY g.id", (since_day,)).fetchall():
        out.append((f"drop:{signal_id}", f"DROP ALERT · {ticker} fell 20% or more from its 52-week high ({day}). Agent 3 checks the latest "
                                          "filing and news; the check is not a sell signal." + (f" Detail: {detail}" if detail else "")))

    for audit_id, ticker, kind in conn.execute(
            "SELECT a.id, s.ticker, a.audit FROM audits a JOIN stocks s ON s.id = a.stock_id WHERE a.result = 'fail' AND a.created_at >= ? "
            "ORDER BY a.id", (since,)).fetchall():
        out.append((f"audit:{audit_id}", f"AUDITOR DISAGREES · {ticker}: the {kind} audit failed and the card is marked unverified. "
                                         "Check the figure before acting."))

    warn = (config.settings().get("budget") or {}).get("openrouter_warning_usd")
    if warn is not None:
        spent = sum(r["usd"] for r in ai.spend_by_provider(conn) if r["provider"] == "openrouter")
        if spent >= float(warn):
            out.append((f"spend:{ai.month_start()}", f"SPEND · OpenRouter has cost ${spent:.2f} this month (the warning is ${float(warn):g}; "
                                                      f"the monthly limit is ${(config.settings().get('budget') or {}).get('openrouter_monthly_limit_usd', 15)})."))
    return out


def run(conn, now=None) -> str | None:
    """The new alerts as one message, marked as sent; None when there are none."""
    sent = {r[0] for r in conn.execute("SELECT key FROM alerts_sent")}
    new = [(k, t) for k, t in pending(conn, now) if k not in sent]
    if not new:
        return None
    stamp = clock.utc_iso(now)
    conn.executemany("INSERT OR IGNORE INTO alerts_sent (key, sent_at, text) VALUES (?, ?, ?)", [(k, stamp, t) for k, t in new])
    conn.commit()
    return notify.message(f"ALERTS · {len(new)} new", [t for _, t in new])


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        print("usage: python -m shared.alerts")
        return 2

    def work(_run):
        conn = dbmod.connect()
        try:
            return run(conn)
        finally:
            conn.close()

    return runlog.job_main("alerts", work)


if __name__ == "__main__":
    sys.exit(main())
