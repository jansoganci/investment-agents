"""Yahoo Finance through the `yfinance` library (decision 2026-10-06; roadmap, "After the first real-model run"): daily closes, split and
dividend history, the ready-made market value, FX.

    chart(symbol, range_, interval)  → the answer in Yahoo's chart format (closes, adjusted closes, dividends, splits)
    parse_chart(raw)                 → {currency, price, rows, dividends, splits}
    quotes(symbols)                  → {symbol: {marketCap, currency, regularMarketPrice}}
    market_values(symbols)           → {symbol: market value in USD or None} (Yahoo's own figure; decision 2026-10-05)

Yahoo has no official API and answers plain scripts with HTTP 429; `yfinance` behaves like a browser. Requests are spaced and a
"too many requests" answer is retried a few times, then given up. Tests put a stand-in for `_yf()`.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone

SPACING = 1.0  # seconds between requests
RETRIES = 3

_last = 0.0


class YahooError(RuntimeError):
    pass


def _yf():
    import yfinance

    return yfinance


def _space() -> None:
    global _last
    wait = SPACING - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.monotonic()


def _call(what: str, fn):
    """Run one yfinance call with spacing and a few retries when Yahoo says "too many requests"."""
    for attempt in range(RETRIES):
        _space()
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — yfinance raises its own types; all become YahooError
            limited = "429" in str(exc) or "too many" in str(exc).lower() or type(exc).__name__ == "YFRateLimitError"
            if limited and attempt < RETRIES - 1:
                time.sleep(5 * 2 ** attempt)
                continue
            raise YahooError(f"Yahoo did not answer for {what} ({type(exc).__name__}: {exc})") from exc
    raise YahooError(f"Yahoo could not be reached for {what}")


def _num(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def chart(symbol: str, range_: str = "10y", interval: str = "1d") -> dict:
    """Closes, adjusted closes, dividends and splits for `symbol`, in the shape of Yahoo's chart answer (`parse_chart` reads it)."""
    ticker = _yf().Ticker(symbol)
    df = _call(symbol, lambda: ticker.history(period=range_, interval=interval, auto_adjust=False, actions=True))
    if df is None or len(df) == 0:
        raise YahooError(f"Yahoo has no chart for {symbol}")
    try:
        info = _call(symbol, lambda: ticker.fast_info)
        currency, tz_name = info["currency"], info["timezone"]
    except (YahooError, KeyError, TypeError):
        currency, tz_name = None, None
    index = list(df.index)
    tz_name = tz_name or str(getattr(df.index, "tz", None) or "") or None
    offset = int(index[-1].utcoffset().total_seconds()) if getattr(index[-1], "utcoffset", None) and index[-1].utcoffset() else 0
    stamps = [int(ts.timestamp()) for ts in index]
    closes = [_num(v) for v in df["Close"]]
    adj = [_num(v) for v in (df["Adj Close"] if "Adj Close" in df else df["Close"])]
    dividends, splits = {}, {}
    if "Dividends" in df:
        for st, v in zip(stamps, df["Dividends"]):
            if _num(v):
                dividends[str(st)] = {"date": st, "amount": float(v)}
    if "Stock Splits" in df:
        for st, v in zip(stamps, df["Stock Splits"]):
            if _num(v):
                splits[str(st)] = {"date": st, "numerator": float(v), "denominator": 1.0}  # 10.0 = 10 for 1; 0.125 = 1 for 8
    last = next((c for c in reversed(closes) if c is not None), None)
    return {"meta": {"symbol": symbol, "currency": currency, "regularMarketPrice": last, "gmtoffset": offset,
                     "exchangeTimezoneName": tz_name, "instrumentType": None},
            "timestamp": stamps, "indicators": {"quote": [{"close": closes}], "adjclose": [{"adjclose": adj}]},
            "events": {"dividends": dividends, "splits": splits}}


def _day(ts: int, offset: int) -> str:
    return (datetime.fromtimestamp(ts, timezone.utc) + timedelta(seconds=offset)).date().isoformat()


def parse_chart(raw: dict) -> dict:
    meta = raw.get("meta", {})
    offset = int(meta.get("gmtoffset") or 0)
    stamps = raw.get("timestamp") or []
    quote = ((raw.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((raw.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose") or [None] * len(stamps)
    closes = quote.get("close") or [None] * len(stamps)
    rows = [(_day(ts, offset), c, a) for ts, c, a in zip(stamps, closes, adj) if c is not None]
    events = raw.get("events") or {}
    dividends = sorted((_day(int(v["date"]), offset), float(v["amount"])) for v in (events.get("dividends") or {}).values())
    splits = sorted((_day(int(v["date"]), offset), float(v["numerator"]) / float(v["denominator"]))
                    for v in (events.get("splits") or {}).values() if float(v.get("denominator") or 0))
    return {"symbol": meta.get("symbol"), "currency": meta.get("currency"), "price": meta.get("regularMarketPrice"),
            "rows": rows, "dividends": dividends, "splits": splits}


def quotes(symbols: list[str]) -> dict[str, dict]:
    """Yahoo's market value, currency and last price for each symbol it answers for."""
    out = {}
    for s in symbols:
        info = _call(s, lambda s=s: _yf().Ticker(s).fast_info)
        try:
            out[s] = {"symbol": s, "marketCap": _num(info["market_cap"]), "currency": info["currency"],
                      "regularMarketPrice": _num(info["last_price"])}
        except (KeyError, TypeError):
            continue
    return out


def market_values(symbols: list[str]) -> dict[str, float | None]:
    """Yahoo's ready-made market value in USD; None when Yahoo has none or does not answer (the price line then stays
    `not_computed` — roadmap section 3, "Valuation")."""
    try:
        got = quotes(symbols)
    except YahooError:
        return {s: None for s in symbols}
    out = {}
    for s in symbols:
        r = got.get(s) or {}
        mc, cur = r.get("marketCap"), r.get("currency")
        out[s] = float(mc) if mc and cur == "USD" else None
    return out
