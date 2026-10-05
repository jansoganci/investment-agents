"""Download the Yahoo sample data once, trimmed (phase 1 tests). Run: uv run python tests/fixtures/fetch_yahoo.py
Per stock: 10 years of monthly closes with every split and dividend, the last month of daily closes, and Yahoo's quote
(price, market value). Plus SPY, gold, USD/TRY and DKK/USD for the price job. Each file has `_meta` (source, date)."""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.prices import yahoo  # noqa: E402

OUT = Path(__file__).resolve().parent / "yahoo"
STOCKS = ["KO", "NVDA", "NKE", "SBUX", "PFE", "INTC", "BA", "SNAP", "DOW", "RIVN", "NVO", "GE", "JPM"]
OTHERS = ["SPY", "GC=F", "TRY=X", "DKKUSD=X"]


def trim(raw: dict) -> dict:
    keep_meta = ("symbol", "currency", "regularMarketPrice", "gmtoffset", "exchangeTimezoneName", "instrumentType")
    return {"meta": {k: raw["meta"].get(k) for k in keep_meta}, "timestamp": raw.get("timestamp"),
            "indicators": raw.get("indicators"), "events": raw.get("events")}


def save(name: str, data: dict, source: str) -> None:
    data["_meta"] = {"source": source, "fetched": date.today().isoformat()}
    (OUT / name).write_text(json.dumps(data, separators=(",", ":")))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    yahoo.SPACING = 3.0
    for s in (sys.argv[1:] or STOCKS + OTHERS):
        f = s.replace("=", "_")
        if not (OUT / f"{f}_daily.json").exists():
            save(f"{f}_daily.json", trim(yahoo.chart(s, "1mo", "1d")), f"query2.finance.yahoo.com/v8/finance/chart/{s}?range=1mo&interval=1d")
        if s in STOCKS and not (OUT / f"{f}_monthly.json").exists():
            save(f"{f}_monthly.json", trim(yahoo.chart(s, "10y", "1mo")), f"query2.finance.yahoo.com/v8/finance/chart/{s}?range=10y&interval=1mo")
        print(s, "chart ok", flush=True)
    if not (OUT / "quotes.json").exists():
        try:
            q = yahoo.quotes(STOCKS)
            keep = ("symbol", "currency", "regularMarketPrice", "marketCap", "regularMarketTime", "financialCurrency")
            save("quotes.json", {"quotes": {k: {f: v.get(f) for f in keep} for k, v in q.items()}},
                 "query2.finance.yahoo.com/v7/finance/quote")
            print("quotes ok")
        except yahoo.YahooError as exc:
            print("quotes failed:", exc)
