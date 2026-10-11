"""The text the Counter prints (and the Sunday summary will take its lines from)."""

from __future__ import annotations

from agents.counter.count import Result, cfg
from shared import notify


def _plural(n: int) -> str:
    return f"{n} post" + ("" if n == 1 else "s")


def render(r: Result, title: str | None = None) -> str:
    c = cfg()
    top = c["top"]
    head = title or f"COUNTER · last {c['window_days']} days (to {r.to_day})"
    lines: list[str] = []

    stocks = [e for e in r.of("stock") if not e.has_card]
    if stocks:
        lines.append(f"US stocks to score (top {min(top, len(stocks))} of {len(stocks)}):")
        for e in stocks[:top]:
            lines.append(f"{e.rank}. {e.key} {e.label} — {_plural(e.posts_7d)} (30 days: {e.posts_30d}) · mentions {e.points}/2")
    else:
        lines.append("No US stock without a card was mentioned.")

    carded = [e for e in r.of("stock") if e.has_card and e.posts_7d >= c["card_mention_bar"]]
    if carded:
        lines.append("Stocks with a card mentioned a lot: " + ", ".join(
            f"{e.key} ({e.posts_7d})" for e in sorted(carded, key=lambda e: (-e.posts_7d, e.key))))

    non_us = r.of("non_us")
    if non_us:
        lines.append("Non-US names mentioned a lot: " + ", ".join(f"{e.label} ({e.posts_7d})" for e in non_us[:5]))
    commodities = r.of("commodity")
    if commodities:
        lines.append("Commodities: " + " · ".join(f"{e.label} {e.posts_7d}" for e in commodities[:5]))
    sectors = r.of("sector")
    if sectors:
        lines.append("Sectors: " + " · ".join(f"{e.key} {e.posts_7d}" for e in sectors[:5]))

    if r.waiting_tags:
        lines.append(f"{r.waiting_tags} US-looking tag(s) wait for you and are not counted: send /tag.")
    if r.unclassified_tags:
        lines.append(f"{r.unclassified_tags} tag(s) are not classified yet and are not counted.")
    if r.posts_in_window == 0 and not r.entries:
        lines.append("No post was read in this window yet.")
    return notify.message(head, lines)
