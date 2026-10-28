"""The bulletin's figures table: last close, 1-month change, day change (roadmap "Morning bulletin" 5; plan slice 2).

All of it is code, no model: the numbers come from `prices` (filled by the nightly job) and the rows from `settings.yaml`
`bulletin.market`. A price changes in percent, a yield (`kind: yield`) in basis points. The text is Turkish (the one output that is).
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

from shared import config

TITLE = "📊 RAKAMLAR (son kapanış)"


@dataclass(frozen=True)
class Row:
    label: str
    kind: str                     # "price" or "yield"
    day: str | None               # date of the last close; None = nothing stored for this symbol
    last: float | None
    month: float | None           # change over 1 month: percent (price) or basis points (yield); None = no close that old
    daily: float | None           # change since the close before


def month_before(day: str) -> str:
    """The same date one month earlier (31 March → 28 February)."""
    d = date.fromisoformat(day)
    year, month = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1])).isoformat()


def _change(kind: str, now: float, then: float | None) -> float | None:
    if then is None or (kind == "price" and then == 0):
        return None
    return (now - then) * 100 if kind == "yield" else (now / then - 1) * 100


def row(conn, label: str, symbol: str, kind: str = "price") -> Row:
    closes = conn.execute("SELECT date, close FROM prices WHERE symbol = ? AND close IS NOT NULL ORDER BY date DESC LIMIT 70",
                          (symbol,)).fetchall()
    if not closes:
        return Row(label, kind, None, None, None, None)
    day, last = closes[0]
    ago = month_before(day)
    base = next((c for d, c in closes if d <= ago), None)   # the last close on or before the same date a month ago
    previous = closes[1][1] if len(closes) > 1 else None
    return Row(label, kind, day, last, _change(kind, last, base), _change(kind, last, previous))


def rows(conn) -> list[Row]:
    spec = (config.settings().get("bulletin") or {}).get("market") or []
    return [row(conn, r["label"], r["symbol"], r.get("kind", "price")) for r in spec]


# --- Turkish text ---------------------------------------------------------------------------------------------------------

def tr(value: float, digits: int = 2) -> str:
    """6,801.25 → 6.801,25"""
    return f"{value:,.{digits}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def _arrow(value: float, digits: int) -> str:
    rounded = round(value, digits)
    return "▲" if rounded > 0 else "▼" if rounded < 0 else "•"


def change_text(kind: str, value: float | None) -> str:
    if value is None:
        return "—"
    if kind == "yield":
        return f"{_arrow(value, 0)} {tr(abs(value), 0)} bp"
    return f"{_arrow(value, 1)} %{tr(abs(value), 1)}"


def line(r: Row, newest: str | None = None) -> str:
    if r.last is None:
        return f"{r.label} · veri yok"
    level = f"%{tr(r.last)}" if r.kind == "yield" else tr(r.last)
    # a figure whose last close is older than the others' is marked with its date (a holiday, a late file)
    old = f" ({date.fromisoformat(r.day).strftime('%d.%m')})" if newest and r.day < newest else ""
    return f"{r.label} · {level}{old} · 1 ay {change_text(r.kind, r.month)} · gün {change_text(r.kind, r.daily)}"


def render(table: list[Row]) -> str:
    dates = [r.day for r in table if r.day]
    newest = max(dates) if dates else None
    return "\n".join([TITLE] + [line(r, newest) for r in table])
