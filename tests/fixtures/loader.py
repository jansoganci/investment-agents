"""Read the saved sample data (tests/fixtures/). Each file carries `_meta` (source and date)."""

import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(*parts: str) -> dict:
    path = HERE.joinpath(*parts)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def sec_facts(ticker: str) -> dict:
    return load("sec", f"{ticker}_facts.json.gz")


def sec_submissions(ticker: str) -> dict:
    return load("sec", f"{ticker}_submissions.json.gz")


def filing_text(ticker: str) -> dict:
    """{"accession", "text"}: a real 10-Q as plain text (trimmed). NVDA, quarter to 2026-07-26."""
    return load("filings", f"{ticker}_10Q.json.gz")


TICKER_CIK = {"KO": 21344, "NVDA": 1045810, "NKE": 320187, "SBUX": 829224, "PFE": 78003, "INTC": 50863, "BA": 12927,
              "SNAP": 1564408, "DOW": 1751788, "RIVN": 1874178, "NVO": 353278, "GE": 40545, "JPM": 19617,
              "PLTR": 1321655}


class FixtureSources:
    """The saved sample data in place of SEC and Yahoo (agents/analysis/run.py `sources`)."""

    def __init__(self, market_values: dict | None = None):
        self.market_values = market_values or {}
        self.calls = []

    def _ticker(self, cik):
        for t, c in TICKER_CIK.items():
            if int(c) == int(cik):
                return t
        raise KeyError(cik)

    def lookup(self, ticker):
        t = ticker.upper()
        if t not in TICKER_CIK:
            return None
        return {"cik": str(TICKER_CIK[t]).zfill(10), "name": t, "ticker": t, "exchange": None, "all_tickers": [t]}

    def facts(self, cik):
        self.calls.append(("facts", cik))
        return sec_facts(self._ticker(cik))

    def submissions(self, cik):
        self.calls.append(("submissions", cik))
        return sec_submissions(self._ticker(cik))

    def filing_text(self, cik, accession, document):
        return filing_text(self._ticker(cik))["text"]  # a saved 10-Q (NVDA only)

    def chart(self, symbol, range_, interval):
        from shared.prices.yahoo import YahooError

        name = symbol.replace("=", "_")
        daily = HERE / "yahoo" / f"{name}_daily.json"
        if not daily.exists():
            raise YahooError(f"no saved Yahoo data for {symbol}")
        raw = load("yahoo", daily.name)
        monthly = HERE / "yahoo" / f"{name}_monthly.json"
        if range_ == "10y" and monthly.exists():  # the daily closes we saved + 10 years of split / dividend events
            raw["events"] = load("yahoo", monthly.name).get("events")
        return raw

    def market_value(self, symbol):
        if symbol in self.market_values:
            return self.market_values[symbol]
        quotes = HERE / "yahoo" / "quotes.json"  # saved from the Mac (tests/fixtures/fetch_yahoo.py), if present
        if quotes.exists():
            q = load("yahoo", "quotes.json")["quotes"].get(symbol) or {}
            return q.get("marketCap") if q.get("currency") == "USD" else None
        return None
