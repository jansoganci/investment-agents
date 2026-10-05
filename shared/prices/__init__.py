"""The one price job (roadmap section 5): every price any agent needs, from Yahoo, into `prices`. No agent fetches prices on
its own.

    uv run python -m shared.prices               the nightly job (03:00 Turkey time on the Air; scheduled in phase 6)
    uv run python -m shared.prices --ticker KO   one ticker on demand: 10 years of daily closes with splits and dividends

What the nightly job fetches: the stocks I hold, the green list (watching + solid), SPY, gold (GC=F, USD per troy ounce),
USD/TRY and the 11 sector funds. Linked commodities come with agent 2 (phase 5; `commodity_links` has no Yahoo symbols yet).
History is kept: a day that is already stored is skipped, never overwritten (the database refuses it too). A day that has
not closed yet is not stored.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from shared import clock
from shared.prices import yahoo

BENCHMARKS = ["SPY", "GC=F", "TRY=X"]
SECTOR_FUNDS = {"Energy": "XLE", "Materials": "XLB", "Industrials": "XLI", "Consumer Discretionary": "XLY",
                "Consumer Staples": "XLP", "Health Care": "XLV", "Financials": "XLF", "Information Technology": "XLK",
                "Communication Services": "XLC", "Utilities": "XLU", "Real Estate": "XLRE"}
CLOSE_HOUR = 17  # a day is stored once it is past 17:00 where the exchange is (the US close is 16:00)


def job_symbols(conn) -> list[str]:
    rows = conn.execute(
        "SELECT ticker FROM stocks WHERE in_portfolio = 'yes' OR (status = 'watching' AND grade = 'solid') ORDER BY ticker"
    ).fetchall()
    return [r[0] for r in rows] + BENCHMARKS + list(SECTOR_FUNDS.values())


def _closed(day: str, tz: str | None, now: datetime | None = None) -> bool:
    zone = ZoneInfo(tz or "America/New_York")
    local = (now or clock.now_utc()).astimezone(zone)
    today = local.date().isoformat()
    return day < today or (day == today and local.hour >= CLOSE_HOUR)


def store(conn, symbol: str, raw_chart: dict, now: datetime | None = None) -> int:
    """Insert the closed days that are not stored yet; returns how many were new. Never overwrites a stored day."""
    parsed = yahoo.parse_chart(raw_chart)
    tz = (raw_chart.get("meta") or {}).get("exchangeTimezoneName")
    divs, splits = dict(parsed["dividends"]), dict(parsed["splits"])
    new = 0
    created = clock.utc_iso(now)
    rows = {day: (close, adj) for day, close, adj in parsed["rows"]}
    for day in set(divs) | set(splits):  # an event on a day without a close in this answer keeps its own row
        rows.setdefault(day, (None, None))
    for day in sorted(rows):
        close, adj = rows[day]
        if not _closed(day, tz, now):
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO prices (symbol, date, close, adj_close, currency, source, dividend, split_ratio, "
            "created_at) VALUES (?, ?, ?, ?, ?, 'yahoo', ?, ?, ?)",
            (symbol, day, close, adj, parsed["currency"], divs.get(day), splits.get(day), created))
        new += cur.rowcount
    conn.commit()
    return new


def fetch(conn, symbol: str, range_: str = "5d", source=None) -> int:
    """`source` is anything with `.chart(symbol, range_, interval)` (Yahoo by default; saved data in tests)."""
    return store(conn, symbol, (source or yahoo).chart(symbol, range_, "1d"))


def ensure_history(conn, symbol: str, source=None) -> int:
    """For one ticker on demand: 10 years the first time (splits and dividends included), then the recent days."""
    # "known" = we already have the long history (a row older than a year), not just the nightly rows
    since = date.fromordinal(date.fromisoformat(clock.today_local()).toordinal() - 365).isoformat()
    known = conn.execute("SELECT 1 FROM prices WHERE symbol = ? AND date < ? LIMIT 1", (symbol, since)).fetchone()
    return fetch(conn, symbol, "1mo" if known else "10y", source)


def latest_close(conn, symbol: str) -> tuple[str, float] | None:
    row = conn.execute("SELECT date, close FROM prices WHERE symbol = ? AND close IS NOT NULL ORDER BY date DESC LIMIT 1",
                       (symbol,)).fetchone()
    return (row[0], row[1]) if row else None


def splits(conn, symbol: str) -> list[tuple[str, float]]:
    return [(d, r) for d, r in conn.execute(
        "SELECT date, split_ratio FROM prices WHERE symbol = ? AND split_ratio IS NOT NULL ORDER BY date", (symbol,))]


def fx_symbol(currency: str) -> str | None:
    """Yahoo's symbol for 1 unit of `currency` in USD (DKKUSD=X); None for USD."""
    return None if currency in (None, "USD") else f"{currency}USD=X"


def run_job(conn, source=None) -> str | None:
    """The nightly job. Returns an error message for Telegram, or None when all is well (no message)."""
    failed = []
    for symbol in job_symbols(conn):
        try:
            fetch(conn, symbol, "5d", source)
        except yahoo.YahooError as exc:
            failed.append(f"{symbol}: {exc}")
    if failed:
        from shared import notify
        return notify.message("PRICES — some symbols failed", failed)
    return None
