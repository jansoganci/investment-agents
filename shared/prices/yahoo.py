"""Yahoo Finance (free, no key): daily closes, split and dividend history, the ready-made market value, FX.

    chart(symbol, range_, interval)  → the raw chart answer (closes, adjusted closes, dividends, splits)
    parse_chart(raw)                 → {currency, price, rows, dividends, splits}
    market_values(symbols)           → {symbol: market value in USD or None} (Yahoo's own figure; decision 2026-10-05)

Yahoo has no official API; requests are spaced and a "too many requests" answer is retried a few times, then given up.
"""

from __future__ import annotations

import http.cookiejar
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
SPACING = 1.0  # seconds between requests

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last = 0.0
_crumb: str | None = None


class YahooError(RuntimeError):
    pass


def _get(url: str, tries: int = 3, raw: bool = False):
    global _last
    for attempt in range(tries):
        wait = SPACING - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
        try:
            with _opener.open(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return body if raw else json.loads(body)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < tries - 1:
                time.sleep(5 * 2 ** attempt)
                continue
            if exc.code == 404 and raw:
                return ""  # fc.yahoo.com answers 404 but sets the cookie
            raise YahooError(f"Yahoo answered {exc.code} for {url.split('?')[0]}") from exc
        except urllib.error.URLError as exc:
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            raise YahooError(f"Yahoo could not be reached ({exc.reason})") from exc
    raise YahooError("Yahoo could not be reached")


def chart(symbol: str, range_: str = "10y", interval: str = "1d") -> dict:
    q = urllib.parse.urlencode({"range": range_, "interval": interval, "events": "div,split"})
    data = _get(f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{q}")
    result = (data.get("chart") or {}).get("result") or []
    if not result:
        raise YahooError(f"Yahoo has no chart for {symbol}")
    return result[0]


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


def _get_crumb() -> str:
    global _crumb
    if _crumb is None:
        _get("https://fc.yahoo.com/", raw=True)  # sets the session cookie
        crumb = _get("https://query2.finance.yahoo.com/v1/test/getcrumb", raw=True).strip()
        if not crumb or " " in crumb or len(crumb) > 40:
            raise YahooError(f"Yahoo gave no session key ({crumb[:40]!r})")
        _crumb = crumb
    return _crumb


def quotes(symbols: list[str]) -> dict[str, dict]:
    q = urllib.parse.urlencode({"symbols": ",".join(symbols), "crumb": _get_crumb()})
    data = _get(f"https://query2.finance.yahoo.com/v7/finance/quote?{q}")
    return {r["symbol"]: r for r in (data.get("quoteResponse") or {}).get("result") or []}


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
