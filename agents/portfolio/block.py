"""The portfolio block: the Sunday summary's part and the answer to `/portfolio` (roadmap section 3, "Agent 4 rules", Output)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from shared import notify
from agents.portfolio.ledger import qty_text
from agents.portfolio.value import Portfolio
from agents.portfolio.watch import price_text


def usd(x: float | None) -> str:
    if x is None:
        return "—"
    whole = int(Decimal(str(abs(x))).quantize(Decimal("1"), ROUND_HALF_UP))  # $856.50 → $857, not Python's $856
    return f"-${whole:,}" if x < 0 and whole else f"${whole:,}"


def usd2(x: float | None) -> str:
    return "—" if x is None else f"${x:,.2f}"


def k(x: float | None) -> str:
    return "—" if x is None else f"${x / 1000:,.1f}k"


def pct(x: float | None) -> str:
    return "—" if x is None else f"{x:+.1%}"


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def week_change(p: Portfolio, prev: dict | None) -> float | None:
    """The stock portfolio's move since the previous snapshot, without the money I put in or took out."""
    if not prev or not prev.get("stock_value"):
        return None
    moved = p.stock_value - prev["stock_value"] - (p.put_in - prev["put_in"]) + (p.got_back - prev["got_back"])
    return moved / prev["stock_value"]


def render(p: Portfolio, signals: dict | None, title: str, prev: dict | None, since_label: str, extra: list[str] = ()) -> str:
    divs = sum(a for _, a, kind, _ in (p.ledger.flows if p.ledger else []) if kind == "dividend")
    sales = p.got_back - divs
    lines = []
    if not p.holdings and not p.put_in:
        lines.append("No stocks in the ledger yet (/bought records a buy).")
    else:
        back = f"got back {usd(p.got_back)}"
        if p.got_back:
            back += f" (sales {usd(sales)} · dividends {usd2(divs)})" if sales and divs else (
                " (dividends)" if divs else " (sales)")
        wk = week_change(p, prev)
        lines.append(f"Value {usd(p.stock_value)}" + (f" · {since_label} {pct(wk)}" if wk is not None else "")
                     + f" · put in {usd(p.put_in)} · {back}")
        ret = f"Return so far: {pct(p.return_pct)}"
        lines.append(ret + (f" · yearly {pct(p.xirr)} (counts every buy)" if p.yearly else "   (yearly figure after 12 months)"))
        sh = [p.shadows.get("SPY"), p.shadows.get("Gold")]
        if all(s is not None for s in sh):
            parts = []
            for s in sh:
                y = f", yearly {pct(s.xirr)}" if p.yearly and s.xirr is not None else ""
                parts.append(f"{s.name} {usd(s.value)} ({pct(s.return_pct)}{y})" if s.value is not None else f"{s.name} — (no price)")
            lines.append("Same money, same days → " + " · ".join(parts))
            spy = sh[0]
            if spy.value is not None and not p.no_price:
                gap = p.stock_value - spy.value
                lines.append(f"You vs SPY: {'+' if gap >= 0 else '-'}{usd(abs(gap))}")
            if any(s.value is not None and s.value < 0 for s in sh):
                lines.append("(A shadow is below zero: a sale took out more than it held — same money, same days.)")
        for h in p.holdings:
            if h.value is None:
                lines.append(f"{h.ticker} {qty_text(h.quantity)} @ {usd2(h.average_cost)} · no close stored yet (not counted)")
            else:
                lines.append(f"{h.ticker} {qty_text(h.quantity)} @ {usd2(h.average_cost)} · {usd(h.value)} · {h.weight:.0%} · "
                             f"{'+' if h.gain >= 0 else '-'}{usd(abs(h.gain))} ({pct(h.gain_pct)})")
    if signals is None:  # no weekly run yet: no alerts or new-money list to show
        lines.append("No weekly run yet (alerts and new money come with it).")
    else:
        lines += _signal_lines(signals)
    w = p.wealth
    gold = f"gold {qty_text(w.gold_grams)} g {k(w.gold_value)}" if abs(w.gold_grams) > 1e-9 else "gold $0.0k"
    lines.append(f"Total wealth: stocks {k(p.stock_value)} + {gold} + BES {k(w.bes_value)} = {k(w.total)} · "
                 + (f"{w.share:.1%} of {k(w.goal).replace('.0k', 'k')}" if w.share is not None else "share of the goal —"))
    if p.no_price:
        lines.append(f"No recent close for {', '.join(p.no_price)}: run the price job (uv run python -m shared.prices).")
    lines += list(extra)
    return notify.message(title, lines)


def _signal_lines(signals: dict) -> list[str]:
    lines = []
    drops = signals.get("drop_alert") or []
    lines.append("Drop alerts: " + ("none" if not drops else " · ".join(
        f"{d['ticker']} {d['drop']:.0%} below its 52-week high ({usd2(d['high'])}, week of {d['high_week']}) → agent 3 "
        "checks the thesis" for d in drops)))
    exp = signals.get("expensive_now") or []
    if exp:
        lines.append("Expensive 4 weeks: " + " · ".join(f"{e['ticker']} ({price_text(e['peg'], e['fcf_yield'])})" for e in exp))
    nm = signals.get("new_money_rank") or []
    caps = signals.get("weight_cap") or []
    if nm or caps:
        lines.append("New money: " + ("  ".join(f"{d['rank']}) {d['ticker']}" for d in nm) if nm else "none"))
    else:
        lines.append("New money: none (the green list is empty)")
    for c in caps:
        lines.append(f"Not suggested (25% rule): {c['ticker']} — would rank {_ordinal(c['would_rank'])}, {c['weight']:.0%} of "
                     "the stock portfolio. Not a sell signal. Your call.")
    return lines
