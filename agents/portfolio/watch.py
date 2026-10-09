"""The weekly watches of agent 4 (rules 5–7). None of them is a trading signal; agent 4 never says "sell" (rule 9).

- **Drop alert (rule 6):** a stock I hold whose Friday close is 20% or more below its highest weekly close of the last 52 weeks →
  a `pending` `drop_alert` signal; agent 3's `--drop-alerts` checks the thesis. **None in a split week** (a split shows as a fake
  drop — "AI auditor" table). **Once per fall** (my decision, 2026-10-09): no new alert for a stock until it makes a new
  52-week high.
- **Valuation watch (rule 7):** the latest card entry's PEG and FCF yield, moved with the Friday close (PEG grows with the price,
  the FCF yield shrinks with it), are stored weekly in `valuations`. PEG > 3 or FCF yield < 1% for 4 weeks in a row → an
  `expensive` signal and one dated card note; the stock goes to the back of the new-money queue while it stays expensive.
- **New money (rule 5):** the green list ranked by 3 conditions (my decision, 2026-10-09) — below its 52-week high · latest
  thesis `intact` · the price line not `expensive` (PEG and FCF yield; at least one computed). More conditions first; on a tie the
  bigger fall from the high first; 4 weeks expensive last. A stock above 25% of the stock portfolio gets no new money and is
  listed under "Not suggested (25% rule)" with the rank it would have had (`weight_cap`).
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from shared import clock, drive
from agents.analysis import card
from agents.analysis.measures import verdicts
from agents.portfolio.marketdata import Series
from agents.portfolio.value import PRICE_GAP_DAYS, Portfolio

DROP = 0.20
WEEKS = 52
PEG_MAX = 3.0
FCF_YIELD_MIN = 0.01
EXPENSIVE_WEEKS = 4
WEIGHT_CAP = 0.25


def week_end_for(today: str) -> str:
    """The Friday whose close the weekly run uses: the latest Friday before today (Sunday → the Friday just past)."""
    d = date.fromisoformat(today) - timedelta(days=1)
    return (d - timedelta(days=(d.weekday() - 4) % 7)).isoformat()


def _days(day: str, n: int) -> str:
    return (date.fromisoformat(day) + timedelta(days=n)).isoformat()


def high_and_drop(series: Series, week_end: str) -> dict | None:
    """This week's close against the highest weekly close of the last 52 weeks; None without a close this week."""
    start = _days(week_end, -7 * WEEKS)
    window = [(w, c) for w, c in series.weekly_closes() if start < w <= week_end]
    if not window or window[-1][0] != week_end:
        return None
    high_week, high = max(window, key=lambda x: (x[1], x[0]))
    close = window[-1][1]
    return {"close": close, "high": high, "high_week": high_week, "drop": 1 - close / high if high else 0.0}


def drop_alerts(conn, p: Portfolio, week_end: str) -> list[str]:
    """Writes the new `drop_alert` signals; returns lines for stocks skipped because of a split this week."""
    skipped = []
    for h in p.holdings:
        series = Series(conn, h.ticker, week_end)
        hd = high_and_drop(series, week_end)
        if hd is None or hd["drop"] < DROP - 1e-12:
            continue
        if any(_days(week_end, -6) <= d <= week_end for d, _ in series.splits):
            skipped.append(f"{h.ticker}: a split this week — no drop alert (a split looks like a drop)")
            continue
        if conn.execute("SELECT 1 FROM signals WHERE kind='drop_alert' AND stock_id=? AND date >= ?",
                        (h.stock_id, hd["high_week"])).fetchone():
            continue  # already alerted for this fall; a new alert only after a new 52-week high
        conn.execute("INSERT INTO signals (kind, stock_id, date, detail, status, created_at) VALUES "
                     "('drop_alert', ?, ?, ?, 'pending', ?)",
                     (h.stock_id, week_end, json.dumps({k: round(v, 4) if isinstance(v, float) else v for k, v in hd.items()}),
                      clock.utc_iso()))
    return skipped


def _card_price(ticker: str) -> tuple[str, dict] | None:
    path = drive.find_card(ticker)
    if path is None:
        return None
    got = card.last_fundamental(path.read_text(encoding="utf-8"))
    if not got:
        return None
    block = got[1].get("price") or {}
    return got[0], {k: _number(block.get(k)) for k in ("price", "peg", "fcf_yield")}


def _number(x) -> float | None:
    """A figure from the card's YAML: `not_computed` (or anything that is not a number) is None, never 0."""
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def _streak(conn, stock_id: int, week_end: str) -> int:
    rows = dict(conn.execute("SELECT week_end, expensive FROM valuations WHERE stock_id=? AND week_end <= ?",
                             (stock_id, week_end)))
    n, w = 0, week_end
    while rows.get(w) == 1:
        n += 1
        w = _days(w, -7)
    return n


def valuations(conn, stocks: list[dict], week_end: str) -> dict[int, dict]:
    """The weekly price line of each stock (held or green): stored in `valuations`; the streak of expensive weeks."""
    out = {}
    for s in stocks:
        series = Series(conn, s["ticker"], week_end)
        got = series.close_on(week_end, PRICE_GAP_DAYS)
        cp = _card_price(s["ticker"])
        peg = fcf = None
        card_date = cp[0] if cp else None
        if got and cp and cp[1].get("price"):
            then = cp[1]["price"] / series.day_factor(card_date)  # the card's price in today's shares
            move = got[1] / then
            peg = cp[1]["peg"] * move if cp[1]["peg"] is not None else None
            fcf = cp[1]["fcf_yield"] / move if cp[1]["fcf_yield"] is not None else None
        expensive = int((peg is not None and peg > PEG_MAX) or (fcf is not None and fcf < FCF_YIELD_MIN))
        conn.execute("INSERT OR IGNORE INTO valuations (stock_id, week_end, close, peg, fcf_yield, expensive, card_date, "
                     "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (s["id"], week_end, got[1] if got else None, peg, fcf, expensive, card_date, clock.utc_iso()))
        streak = _streak(conn, s["id"], week_end)
        out[s["id"]] = {"peg": peg, "fcf_yield": fcf, "expensive": expensive, "streak": streak}
        if streak == EXPENSIVE_WEEKS:
            detail = {"week_end": week_end, "peg": _r(peg), "fcf_yield": _r(fcf), "weeks": streak}
            conn.execute("INSERT INTO signals (kind, stock_id, date, detail, status, created_at) VALUES "
                         "('expensive', ?, ?, ?, 'done', ?)", (s["id"], week_end, json.dumps(detail), clock.utc_iso()))
            out[s["id"]]["note"] = (f"Expensive for {EXPENSIVE_WEEKS} weeks in a row ({price_text(peg, fcf)} at the close of "
                                    f"{week_end}) — information only, not a sell suggestion; it goes to the back of the "
                                    "new-money queue.")
    return out


def write_notes(stocks: list[dict], vals: dict[int, dict]) -> None:
    """The dated card note of a valuation alert (agent 4's only card note). Written last, inside the database lock."""
    for s in stocks:
        note = (vals.get(s["id"]) or {}).get("note")
        path = drive.find_card(s["ticker"]) if note else None
        if path is not None:
            card.append(path, card.note_entry(clock.today_local(), note, who="agent_4"), {})


def _r(x):
    return None if x is None else round(x, 4)


def price_text(peg, fcf) -> str:
    bits = []
    if peg is not None:
        bits.append(f"PEG {peg:.1f}")
    if fcf is not None:
        bits.append(f"FCF yield {fcf:.1%}")
    return " · ".join(bits) or "no price line"


def _thesis(conn, stock_id: int) -> str | None:
    row = conn.execute("SELECT thesis_status FROM card_entries WHERE stock_id=? AND thesis_status IS NOT NULL "
                       "ORDER BY date DESC, id DESC LIMIT 1", (stock_id,)).fetchone()
    return row[0] if row else None


def new_money(conn, p: Portfolio, green: list[dict], vals: dict[int, dict], week_end: str) -> None:
    """Writes this week's `new_money_rank` and `weight_cap` signals."""
    weights = {h.stock_id: h.weight for h in p.holdings}
    ranked = []
    for s in green:
        hd = high_and_drop(Series(conn, s["ticker"], week_end), week_end)
        v = vals.get(s["id"]) or {}
        verdict = verdicts({"peg": v.get("peg"), "fcf_yield": v.get("fcf_yield")})
        computed = [x for x in (verdict["peg"], verdict["fcf_yield"]) if x is not None]
        cond = {"below_high": bool(hd and hd["close"] < hd["high"]),
                "thesis_intact": _thesis(conn, s["id"]) == "intact",
                "price_fair": bool(computed) and "expensive" not in computed}
        back = (v.get("streak") or 0) >= EXPENSIVE_WEEKS
        ranked.append({"stock": s, "cond": cond, "score": sum(cond.values()), "drop": hd["drop"] if hd else None,
                       "back": back})
    ranked.sort(key=lambda x: (x["back"], -x["score"], -(x["drop"] or 0.0), x["stock"]["ticker"]))
    rank = 0
    for would, x in enumerate(ranked, 1):
        sid = x["stock"]["id"]
        weight = weights.get(sid)
        detail = {"would_rank": would, "score": x["score"], "conditions": x["cond"], "drop": _r(x["drop"]),
                  "weight": _r(weight), "expensive_4_weeks": x["back"]}
        if weight is not None and weight > WEIGHT_CAP:
            kind = "weight_cap"
        else:
            rank += 1
            kind, detail["rank"] = "new_money_rank", rank
        conn.execute("INSERT INTO signals (kind, stock_id, date, detail, status, created_at) VALUES (?, ?, ?, ?, 'done', ?)",
                     (kind, sid, week_end, json.dumps(detail), clock.utc_iso()))


def week_signals(conn, week_end: str) -> dict[str, list[dict]]:
    """The signals of one weekly run, for the block: {kind: [{ticker, detail}]}."""
    out: dict[str, list[dict]] = {"drop_alert": [], "expensive": [], "new_money_rank": [], "weight_cap": []}
    for kind, ticker, detail in conn.execute(
            "SELECT g.kind, s.ticker, g.detail FROM signals g JOIN stocks s ON s.id = g.stock_id WHERE g.date = ? "
            "ORDER BY g.id", (week_end,)):
        out[kind].append({"ticker": ticker, **json.loads(detail or "{}")})
    out["new_money_rank"].sort(key=lambda d: d["rank"])
    # the stocks expensive 4+ weeks this week (the signal is written only in the 4th week)
    out["expensive_now"] = [{"ticker": t, "peg": peg, "fcf_yield": fcf} for sid, t, peg, fcf in conn.execute(
        "SELECT v.stock_id, s.ticker, v.peg, v.fcf_yield FROM valuations v JOIN stocks s ON s.id = v.stock_id "
        "WHERE v.week_end = ? AND v.expensive = 1 ORDER BY s.ticker", (week_end,))
        if _streak(conn, sid, week_end) >= EXPENSIVE_WEEKS]
    return out
