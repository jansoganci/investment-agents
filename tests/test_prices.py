"""The one price job (shared/prices). Yahoo blocked this cloud machine while phase 1 was built, so these tests use a small
answer built by hand in Yahoo's chart format (v8); the real answer is checked on the Mac (python -m shared.prices --ticker KO)."""

from datetime import datetime, timezone

import pytest

from shared import prices
from shared.prices import yahoo


def ts(day, hour=13, minute=30):
    return int(datetime.fromisoformat(f"{day}T{hour:02d}:{minute:02d}:00+00:00").timestamp())


def chart(days, closes, splits=None, dividends=None, symbol="KO"):
    """A Yahoo chart answer (only the fields we read)."""
    return {"meta": {"symbol": symbol, "currency": "USD", "regularMarketPrice": closes[-1], "gmtoffset": -14400,
                     "exchangeTimezoneName": "America/New_York"},
            "timestamp": [ts(d) for d in days],
            "indicators": {"quote": [{"close": closes}], "adjclose": [{"adjclose": [c * 0.99 for c in closes]}]},
            "events": {"splits": {str(ts(d)): {"date": ts(d), "numerator": n, "denominator": m} for d, n, m in (splits or [])},
                       "dividends": {str(ts(d)): {"date": ts(d), "amount": a} for d, a in (dividends or [])}}}


AFTER_CLOSE = datetime(2026, 10, 2, 23, 0, tzinfo=timezone.utc)  # 19:00 in New York
MIDDAY = datetime(2026, 10, 2, 16, 0, tzinfo=timezone.utc)       # 12:00 in New York


def test_parse_chart():
    p = yahoo.parse_chart(chart(["2026-09-30", "2026-10-01"], [60.0, 61.0], splits=[("2026-09-30", 10, 1)],
                                dividends=[("2026-10-01", 0.51)]))
    assert p["rows"][0][:2] == ("2026-09-30", 60.0)
    assert p["splits"] == [("2026-09-30", 10.0)] and p["dividends"] == [("2026-10-01", 0.51)]


def test_closed_days_are_stored_with_their_events(db):
    raw = chart(["2026-09-30", "2026-10-01", "2026-10-02"], [60.0, 61.0, 62.0], dividends=[("2026-10-01", 0.51)],
                splits=[("2021-08-02", 1, 8)])
    assert prices.store(db, "KO", raw, now=AFTER_CLOSE) == 4  # 3 days + the old split on a day without a close
    rows = db.execute("SELECT date, close, dividend, split_ratio FROM prices ORDER BY date").fetchall()
    assert rows[0] == ("2021-08-02", None, None, 0.125)
    assert ("2026-10-01", 61.0, 0.51, None) in rows
    assert prices.latest_close(db, "KO") == ("2026-10-02", 62.0)
    assert prices.splits(db, "KO") == [("2021-08-02", 0.125)]


def test_a_day_that_has_not_closed_is_not_stored(db):
    raw = chart(["2026-10-01", "2026-10-02"], [61.0, 62.0])
    assert prices.store(db, "KO", raw, now=MIDDAY) == 1
    assert prices.latest_close(db, "KO") == ("2026-10-01", 61.0)


def test_history_is_kept_never_overwritten(db):
    prices.store(db, "KO", chart(["2026-10-01"], [61.0]), now=AFTER_CLOSE)
    assert prices.store(db, "KO", chart(["2026-10-01"], [99.0]), now=AFTER_CLOSE) == 0
    assert prices.latest_close(db, "KO") == ("2026-10-01", 61.0)


class FakeSource:
    def __init__(self, fail=()):
        self.calls, self.fail = [], set(fail)

    def chart(self, symbol, range_, interval):
        self.calls.append((symbol, range_))
        if symbol in self.fail:
            raise yahoo.YahooError("429")
        return chart(["2020-01-02"], [10.0], symbol=symbol)


def test_on_demand_fetches_10_years_first_then_recent_days(db):
    src = FakeSource()
    prices.ensure_history(db, "KO", src)
    prices.ensure_history(db, "KO", src)
    assert src.calls == [("KO", "10y"), ("KO", "1mo")]


def test_job_symbols(db):
    db.execute("INSERT INTO stocks (ticker, status, grade, created_at) VALUES ('NVDA', 'watching', 'solid', 'x')")
    db.execute("INSERT INTO stocks (ticker, status, grade, created_at) VALUES ('KO', 'watching', 'mid', 'x')")
    db.execute("INSERT INTO stocks (ticker, status, in_portfolio, created_at) VALUES ('V', 'watching', 'yes', 'x')")
    db.commit()
    symbols = prices.job_symbols(db)
    assert {"NVDA", "V", "SPY", "GC=F", "TRY=X", "XLK", "XLRE"} <= set(symbols) and "KO" not in symbols
    assert len(prices.SECTOR_FUNDS) == 11


def test_job_reports_failures_and_is_silent_when_fine(db):
    assert prices.run_job(db, FakeSource()) is None
    msg = prices.run_job(db, FakeSource(fail={"SPY"}))
    assert msg.startswith("PRICES") and "SPY" in msg


def test_market_value_is_none_when_yahoo_has_none(monkeypatch):
    monkeypatch.setattr(yahoo, "quotes", lambda s: {"KO": {"marketCap": 2.9e11, "currency": "USD"}, "NVO": {"currency": "USD"}})
    assert yahoo.market_values(["KO", "NVO", "XYZ"]) == {"KO": 2.9e11, "NVO": None, "XYZ": None}

    def blocked(s):
        raise yahoo.YahooError("429")
    monkeypatch.setattr(yahoo, "quotes", blocked)
    assert yahoo.market_values(["KO"]) == {"KO": None}


def test_fx_symbol():
    assert prices.fx_symbol("USD") is None and prices.fx_symbol("DKK") == "DKKUSD=X"


def test_cli_ticker_writes_a_runs_row(db, monkeypatch, capsys):
    from shared.prices.__main__ import main

    monkeypatch.setattr(yahoo, "chart", lambda s, r, i: chart(["2026-09-30"], [60.0], symbol=s))
    assert main(["--ticker", "KO"]) == 0
    assert "PRICES · KO" in capsys.readouterr().out
    assert db.execute("SELECT job, status FROM runs").fetchall() == [("prices", "ok")]


# --- the yfinance backend, against a stand-in library ----------------------------------------------------------------------

def _frame():
    import pandas as pd
    idx = pd.DatetimeIndex(["2026-09-30", "2026-10-01", "2026-10-02"], tz="America/New_York")
    return pd.DataFrame({"Close": [60.0, float("nan"), 61.5], "Adj Close": [59.0, float("nan"), 60.5],
                         "Dividends": [0.0, 0.0, 0.5], "Stock Splits": [10.0, 0.0, 0.125]}, index=idx)


class _Ticker:
    def __init__(self, symbol, frame=None, fail=None):
        self.symbol, self.frame, self.fail = symbol, frame, fail
        self.fast_info = {"currency": "USD", "timezone": "America/New_York", "market_cap": 2.9e11, "last_price": 61.5}

    def history(self, **kw):
        self.seen = kw
        if self.fail:
            raise self.fail
        return self.frame


def test_chart_through_yfinance_is_read_by_parse_chart(monkeypatch):
    import types
    t = _Ticker("KO", _frame())
    monkeypatch.setattr(yahoo, "_yf", lambda: types.SimpleNamespace(Ticker=lambda s: t))
    monkeypatch.setattr(yahoo, "SPACING", 0)
    p = yahoo.parse_chart(yahoo.chart("KO", "10y", "1d"))
    assert t.seen == {"period": "10y", "interval": "1d", "auto_adjust": False, "actions": True}
    assert p["currency"] == "USD" and p["price"] == 61.5
    assert p["rows"] == [("2026-09-30", 60.0, 59.0), ("2026-10-02", 61.5, 60.5)]  # the day with no close is left out
    assert p["dividends"] == [("2026-10-02", 0.5)]
    assert p["splits"] == [("2026-09-30", 10.0), ("2026-10-02", 0.125)]  # 10 for 1, and a 1-for-8 reverse split


def test_chart_errors_become_yahoo_errors(monkeypatch):
    import types
    monkeypatch.setattr(yahoo, "SPACING", 0)
    monkeypatch.setattr(yahoo.time, "sleep", lambda s: None)
    monkeypatch.setattr(yahoo, "_yf", lambda: types.SimpleNamespace(Ticker=lambda s: _Ticker(s, None, RuntimeError("429 Too Many Requests"))))
    with pytest.raises(yahoo.YahooError, match="Yahoo did not answer for KO"):
        yahoo.chart("KO")
    import pandas as pd
    monkeypatch.setattr(yahoo, "_yf", lambda: types.SimpleNamespace(Ticker=lambda s: _Ticker(s, pd.DataFrame())))
    with pytest.raises(yahoo.YahooError, match="no chart for ZZZ"):
        yahoo.chart("ZZZ")


def test_a_rate_limit_is_retried_before_giving_up(monkeypatch):
    import types
    calls = []

    class Flaky(_Ticker):
        def history(self, **kw):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("429 Too Many Requests")
            return _frame()
    monkeypatch.setattr(yahoo, "SPACING", 0)
    monkeypatch.setattr(yahoo.time, "sleep", lambda s: None)
    monkeypatch.setattr(yahoo, "_yf", lambda: types.SimpleNamespace(Ticker=lambda s: Flaky(s)))
    assert yahoo.parse_chart(yahoo.chart("KO"))["rows"]
    assert len(calls) == 3


def test_quotes_and_market_values_through_yfinance(monkeypatch):
    import types

    class Q(_Ticker):
        def __init__(self, symbol):
            super().__init__(symbol)
            if symbol == "NVO":
                self.fast_info = {"currency": "DKK", "timezone": "x", "market_cap": 3e11, "last_price": 500}
            if symbol == "XYZ":
                self.fast_info = {}
    monkeypatch.setattr(yahoo, "SPACING", 0)
    monkeypatch.setattr(yahoo, "_yf", lambda: types.SimpleNamespace(Ticker=lambda s: Q(s)))
    assert yahoo.market_values(["KO", "NVO", "XYZ"]) == {"KO": 2.9e11, "NVO": None, "XYZ": None}
