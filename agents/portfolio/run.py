"""Agent 4's weekly run (Sunday, with the Friday close) and the on-demand block for `/portfolio`.

The weekly run, in one transaction: the code's dividend and split rows (`holdings`), the drop alerts, the valuation watch, the
new-money ranking, and the frozen weekly `snapshots` row. A week already recorded is not written again (snapshots are frozen);
its block is shown as it is now.
"""

from __future__ import annotations

from shared import clock
from agents.portfolio import ledger as ledgermod
from agents.portfolio import watch
from agents.portfolio.block import render
from agents.portfolio.value import Portfolio, compute

SNAP = ("week_end", "stock_value", "put_in", "got_back")


def _prev(conn, before: str) -> dict | None:
    row = conn.execute(f"SELECT {', '.join(SNAP)} FROM snapshots WHERE week_end < ? ORDER BY week_end DESC LIMIT 1",
                       (before,)).fetchone()
    return dict(zip(SNAP, row)) if row else None


def _green(conn) -> list[dict]:
    rows = conn.execute("SELECT id, ticker FROM stocks WHERE status='watching' AND grade='solid' AND out_of_scope IS NULL "
                        "ORDER BY ticker").fetchall()
    return [{"id": i, "ticker": t} for i, t in rows]


def _snapshot(conn, p: Portfolio, week_end: str) -> None:
    w = p.wealth
    conn.execute(
        "INSERT INTO snapshots (week_end, stock_value, put_in, got_back, return_pct, spy_shadow, gold_shadow, gold_value, "
        "bes_value, total_wealth, goal_share, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (week_end, p.stock_value, p.put_in, p.got_back, p.return_pct,
         p.shadows["SPY"].value if "SPY" in p.shadows else None, p.shadows["Gold"].value if "Gold" in p.shadows else None,
         w.gold_value, w.bes_value, w.total, w.share, clock.utc_iso()))


def weekly(conn, today: str | None = None) -> str:
    week_end = watch.week_end_for(today or clock.today_local())
    title = f"PORTFOLIO — week ending {week_end}"
    if conn.execute("SELECT 1 FROM snapshots WHERE week_end=?", (week_end,)).fetchone():
        return render(compute(conn, week_end), watch.week_signals(conn, week_end), title, _prev(conn, week_end), "week",
                      ["(This week is already recorded; snapshots are frozen.)"])
    conn.execute("BEGIN IMMEDIATE")  # one writer: a /bought meanwhile waits, so the snapshot and the ledger agree
    try:
        p = compute(conn, week_end)
        changes = ledgermod.sync(conn, p.ledger)
        skipped = watch.drop_alerts(conn, p, week_end)
        green = _green(conn)
        held = [{"id": h.stock_id, "ticker": h.ticker} for h in p.holdings]
        watched = {s["id"]: s for s in held + green}
        vals = watch.valuations(conn, list(watched.values()), week_end)
        watch.new_money(conn, p, green, vals, week_end)
        _snapshot(conn, p, week_end)
        watch.write_notes(list(watched.values()), vals)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    extra = [f"Ledger: {c}" for c in changes] + skipped
    return render(p, watch.week_signals(conn, week_end), title, _prev(conn, week_end), "week", extra)


def on_demand(conn, today: str | None = None) -> str:
    """`/portfolio`: the latest closes; the alerts and the new-money list of the latest weekly run. Changes nothing."""
    day = today or clock.today_local()
    p = compute(conn, day)
    last = conn.execute("SELECT max(week_end) FROM snapshots").fetchone()[0]
    prev = _prev(conn, day)
    signals = watch.week_signals(conn, last) if last else None
    extra = [f"Alerts and new money: from the weekly run of {last}."] if last else []
    return render(p, signals, f"PORTFOLIO — latest closes, {day}", prev, f"since {prev['week_end']}" if prev else "week", extra)
