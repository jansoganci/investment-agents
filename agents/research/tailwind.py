"""sector_tailwind (roadmap, "Score rules" 3): code, Yahoo prices from `prices`, no AI.

Item A (+1): the stock's sector fund is above its 40-week average (weekly closes).
Item B (+1): if a linked commodity has a price: a producer's commodity is above its 40-week average, a user's is below it (majority
of the linked commodities); otherwise the sector fund beat SPY over the last 13 weeks."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from shared import config
from shared.prices import SECTOR_FUNDS

WEEKS = 40
SHORT_WEEKS = 13


@dataclass
class Tailwind:
    points: int
    reason: str
    detail: dict = field(default_factory=dict)


def weekly_closes(conn, symbol: str) -> list[tuple[str, float]]:
    """The last stored close of each ISO week, oldest first."""
    weeks: dict = {}
    for day, close in conn.execute("SELECT date, COALESCE(adj_close, close) FROM prices WHERE symbol = ? "
                                   "AND COALESCE(adj_close, close) IS NOT NULL ORDER BY date", (symbol,)):
        y, w, _ = date.fromisoformat(day).isocalendar()
        weeks[(y, w)] = (day, close)
    return [weeks[k] for k in sorted(weeks)]


def above_average(conn, symbol: str, weeks: int = WEEKS) -> tuple[bool | None, str]:
    closes = weekly_closes(conn, symbol)
    if len(closes) < weeks:
        return None, f"{symbol}: only {len(closes)} weeks of prices, {weeks} needed"
    recent = [c for _, c in closes[-weeks:]]
    avg, last = sum(recent) / weeks, recent[-1]
    return last > avg, f"{symbol} {last:,.2f} is {'above' if last > avg else 'not above'} its {weeks}-week average {avg:,.2f}"


def beat_benchmark(conn, symbol: str, bench: str = "SPY", weeks: int = SHORT_WEEKS) -> tuple[bool | None, str]:
    a, b = weekly_closes(conn, symbol), weekly_closes(conn, bench)
    if len(a) <= weeks or len(b) <= weeks:
        return None, f"{symbol} or {bench}: not enough weeks of prices for {weeks} weeks"
    ra, rb = a[-1][1] / a[-1 - weeks][1] - 1, b[-1][1] / b[-1 - weeks][1] - 1
    return ra > rb, f"{symbol} {ra:+.1%} against {bench} {rb:+.1%} over {weeks} weeks"


def commodity_symbol(name: str) -> str | None:
    table = {k.lower(): v for k, v in (config.settings().get("commodity_symbols") or {}).items()}
    return table.get(name.lower())


def symbols_needed(sector: str | None, links: list[tuple[str, str]]) -> list[str]:
    out = ["SPY"]
    if sector in SECTOR_FUNDS:
        out.append(SECTOR_FUNDS[sector])
    out += [s for s in (commodity_symbol(c) for c, _ in links) if s]
    return list(dict.fromkeys(out))


def evaluate(conn, sector: str | None, links: list[tuple[str, str]]) -> Tailwind:
    """`links`: [(commodity name, role)] — role `producer` or `user`."""
    fund = SECTOR_FUNDS.get(sector or "")
    detail: dict = {"sector": sector, "fund": fund}
    if fund is None:
        return Tailwind(1, f"unclear — no sector fund: the stock's sector is {sector or 'unknown'}; neutral 1 point", detail)
    a, a_text = above_average(conn, fund)
    points, parts = 0, []
    if a:
        points += 1
    parts.append(("A: " + a_text) + ("" if a is not None else " (could not be judged)"))
    detail["item_a"] = a

    judged = []
    for commodity, role in links:
        symbol = commodity_symbol(commodity)
        if symbol is None:
            continue
        up, text = above_average(conn, symbol)
        if up is None:
            continue
        favorable = up if role == "producer" else not up
        judged.append((favorable, f"{commodity} ({role}): {text}"))
    if judged:
        good = sum(1 for f, _ in judged if f)
        b = good > len(judged) - good
        parts.append("B: linked commodity — " + "; ".join(t for _, t in judged) + (" → favorable" if b else " → not favorable"))
    else:
        b, b_text = beat_benchmark(conn, fund)
        parts.append("B: no linked commodity with a price; " + b_text + ("" if b is not None else " (could not be judged)"))
    if b:
        points += 1
    detail["item_b"] = b
    if a is None or b is None:
        # missing prices are `unclear` = 1 point, never 0 (audit 2026-10-14, #7; AGENTS.md "if the data is missing, unclear = 1")
        return Tailwind(1, "unclear — prices are missing; neutral 1 point · " + " · ".join(parts), detail)
    return Tailwind(points, " · ".join(parts), detail)
