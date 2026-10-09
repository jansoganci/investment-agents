"""Prices as agent 4 reads them from `prices` (filled only by the one nightly price job, roadmap section 5).

Two things make the stored rows need care:
- **Splits.** Yahoo's closes are split-adjusted at the time they are fetched, and a stored row is never overwritten. So a row for a
  day before a split is in the old share basis if it was stored before the split, and in the new basis if it was fetched later
  (the 10-year history). A row stored on or before the split day (UTC date of `created_at` ≤ split day) is taken as the old basis.
  Everything here is turned into **today's basis** (the shares as they are now); `day_basis` turns a figure back into the
  shares of that day (for a buy price check or a dividend per share).
- **Dividends for SPY.** The adjusted close of rows stored on different nights has different bases, so the SPY shadow uses a
  total-return index built from the close and the dividend of each stored day (dividends reinvested on the ex-date) — the same
  thing the adjusted close means, without mixing bases.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

SPY = "SPY"
GOLD = "GC=F"        # USD per troy ounce
USDTRY = "TRY=X"     # TL per USD
OUNCE_GRAMS = 31.1035


@dataclass
class Row:
    day: str
    close: float | None
    dividend: float | None
    split_ratio: float | None
    created: str  # UTC date the row was stored


def rows(conn, symbol: str, upto: str | None = None) -> list[Row]:
    sql = "SELECT date, close, dividend, split_ratio, created_at FROM prices WHERE symbol=?"
    args: list = [symbol]
    if upto:
        sql += " AND date <= ?"
        args.append(upto)
    return [Row(d, c, dv, s, (ca or "")[:10]) for d, c, dv, s, ca in conn.execute(sql + " ORDER BY date", args)]


class Series:
    """One symbol's stored rows, in today's share basis (up to `upto`)."""

    def __init__(self, conn, symbol: str, upto: str | None = None):
        self.symbol = symbol
        self.raw = rows(conn, symbol, upto)
        self.splits = [(r.day, r.split_ratio) for r in self.raw if r.split_ratio]

    def _stored_factor(self, r: Row) -> float:
        """How many of today's shares one share of the row's own basis is (1 when the row is already in today's basis)."""
        f = 1.0
        for day, ratio in self.splits:
            if r.day < day and r.created <= day:
                f *= ratio
        return f

    def day_factor(self, day: str) -> float:
        """Today's shares per share held on `day` (the splits after that day)."""
        f = 1.0
        for d, ratio in self.splits:
            if d > day:
                f *= ratio
        return f

    def closes(self) -> list[tuple[str, float]]:
        return [(r.day, r.close / self._stored_factor(r)) for r in self.raw if r.close is not None]

    def dividends(self) -> list[tuple[str, float]]:
        """(ex-date, dividend per share in that day's shares)."""
        return [(r.day, r.dividend / self._stored_factor(r) * self.day_factor(r.day)) for r in self.raw if r.dividend]

    def close_on(self, day: str, max_gap_days: int | None = None) -> tuple[str, float] | None:
        """The latest close on or before `day`, in today's basis; with `max_gap_days`, None when it is older than that."""
        found = None
        for d, c in self.closes():
            if d > day:
                break
            found = (d, c)
        if found and max_gap_days is not None and date.fromisoformat(day) - date.fromisoformat(found[0]) > timedelta(days=max_gap_days):
            return None
        return found

    def total_return(self) -> list[tuple[str, float]]:
        """A total-return index: dividends reinvested at the ex-date (a dividend on a day without a close waits for the next close)."""
        out, prev, pending, level = [], None, 0.0, None
        divs = dict(self.dividends())
        closes = self.closes()
        close_days = {d for d, _ in closes}
        events = sorted(set(close_days) | set(divs))
        cmap = dict(closes)
        for d in events:
            # dividend in today's basis on its ex-date (closes are in today's basis too)
            pending += divs.get(d, 0.0) / self.day_factor(d)
            if d not in cmap:
                continue
            c = cmap[d]
            level = c if prev is None else level * (c + pending) / prev
            pending = 0.0
            prev = c
            out.append((d, level))
        return out

    def weekly_closes(self) -> list[tuple[str, float]]:
        """The last close of each Monday–Friday week, keyed by that week's Friday."""
        weeks: dict[str, float] = {}
        for d, c in self.closes():
            day = date.fromisoformat(d)
            friday = day + timedelta(days=4 - day.weekday())  # a weekend day belongs to the Friday before
            weeks[friday.isoformat()] = c
        return sorted(weeks.items())


def level_on(series: list[tuple[str, float]], day: str) -> float | None:
    found = None
    for d, v in series:
        if d > day:
            break
        found = v
    return found


def usdtry_on(conn, day: str) -> tuple[str, float] | None:
    return Series(conn, USDTRY, day).close_on(day)


def gold_gram_usd(conn, day: str) -> tuple[str, float] | None:
    got = Series(conn, GOLD, day).close_on(day)
    return (got[0], got[1] / OUNCE_GRAMS) if got else None
