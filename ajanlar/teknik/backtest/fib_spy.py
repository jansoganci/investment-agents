"""S&P 500 (SPY) market filter with Fibonacci averages (3 … 144), daily and weekly.

Rule: if SPY closes above its N-period simple average, hold all 24 stocks (equal weight); below → all cash (earns nothing).
Trades the next period. 0.1% cost per side. Also run one period late (robustness). Periods: 2006-2015 (incl. 2008), 2016-2026.
Run: uv run --with yfinance --with pandas python fib_spy.py
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from gunluk_5_8_13 import FALLEN, QUALITY
from haftalik import BENCH, END, PERIODS, START_DATA, above_ma, sleeve, stats

FIB = (3, 5, 8, 13, 21, 34, 55, 89, 144)


def table(close: pd.DataFrame, total: pd.DataFrame, names: list[str], label: str) -> None:
    spy = close[BENCH].dropna()
    port = lambda d: pd.DataFrame(d).mean(axis=1, skipna=True)
    bh = port({t: total[t].dropna().pct_change() for t in names})
    print(f"\n=== {label} — 24 stocks, yearly return / largest drop (%) · switches/year · invested ===")
    print(f"{'rule':14s}" + "".join(f"{p:>18s}" for p in PERIODS) + f"{'1 late 06-15':>18s}{'1 late 16-26':>18s}{'sw/yr':>7s}{'inv':>6s}")
    def cells(s):
        return "".join(f"{stats(s, a, b)[0]*100:7.1f} / {stats(s, a, b)[1]*100:6.1f}  " for a, b in PERIODS.values())
    print(f"{'buy & hold':14s}{cells(bh)}")
    for n in FIB:
        on = above_ma(spy, n)
        now = port({t: sleeve(total[t].dropna(), on.reindex(total[t].dropna().index).fillna(0.0)) for t in names})
        late = port({t: sleeve(total[t].dropna(), on.reindex(total[t].dropna().index).fillna(0.0), lag=1) for t in names})
        pt = on.loc["2006-01-01":]
        yrs = (pt.index[-1] - pt.index[0]).days / 365.25
        sw = float((pt.diff().abs() > 0).sum()) / yrs
        print(f"{'SPY > ' + str(n):14s}{cells(now)}{cells(late)}{sw:7.1f}{pt.mean()*100:5.0f}%")


def run() -> None:
    names = QUALITY + FALLEN
    raw = yf.download(names + [BENCH], start=START_DATA, end=END, auto_adjust=False, progress=False)
    table(raw["Close"], raw["Adj Close"], names, "DAILY (N trading days)")
    table(raw["Close"].resample("W-FRI").last(), raw["Adj Close"].resample("W-FRI").last(), names, "WEEKLY (N weeks)")


if __name__ == "__main__":
    run()
