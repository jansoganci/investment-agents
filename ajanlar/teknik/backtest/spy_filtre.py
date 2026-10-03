"""S&P 500 (SPY) market filter with 34 / 40 / 55-week averages — same setup as haftalik.py.

Rule: on a Friday close, if SPY is above its N-week simple average, hold all stocks (equal weight); below → all cash
(cash earns nothing). Trades the next week. 0.1% cost per side. Periods: 2006-2015 (incl. 2008) and 2016-2026.
Run: uv run --with yfinance --with pandas python spy_filtre.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from gunluk_5_8_13 import FALLEN, QUALITY
from haftalik import BENCH, END, PERIODS, START_DATA, above_ma, sleeve, stats

WINDOWS = (34, 40, 55)


def run() -> None:
    names = QUALITY + FALLEN
    raw = yf.download(names + [BENCH], start=START_DATA, end=END, auto_adjust=False, progress=False)
    chart_w = raw["Close"].resample("W-FRI").last()
    total_w = raw["Adj Close"].resample("W-FRI").last()
    spy_c = chart_w[BENCH].dropna()

    def port(d: dict[str, pd.Series]) -> pd.Series:
        return pd.DataFrame(d).mean(axis=1, skipna=True)

    rows = {"Buy & hold (24 stocks)": port({t: total_w[t].dropna().pct_change() for t in names})}
    info = {}
    for n in WINDOWS:
        on = above_ma(spy_c, n)
        rows[f"SPY > {n}-week filter"] = port({t: sleeve(total_w[t].dropna(), on.reindex(total_w[t].dropna().index).fillna(0.0))
                                               for t in names})
        rows[f"  same, one week late"] = None
        rows[f"  same, one week late"] = port({t: sleeve(total_w[t].dropna(), on.reindex(total_w[t].dropna().index).fillna(0.0), lag=1)
                                               for t in names})
        rows[f"  {n}w one week late"] = rows.pop("  same, one week late")
        pt = on.loc["2006-01-01":]
        yrs = (pt.index[-1] - pt.index[0]).days / 365.25
        info[n] = (float((pt.diff().abs() > 0).sum()) / yrs, float(pt.mean()))

    spy_rows = {"SPY buy & hold": total_w[BENCH].pct_change()}
    for n in WINDOWS:
        on = above_ma(spy_c, n)
        spy_rows[f"SPY only, {n}-week filter"] = sleeve(total_w[BENCH].dropna(), on)

    for title, table in (("24 stocks, equal weight", rows), ("SPY itself (index fund)", spy_rows)):
        print(f"\n=== {title} — yearly return / largest drop (%) ===")
        print(f"{'rule':28s}" + "".join(f"{p:>22s}" for p in PERIODS))
        for k, s in table.items():
            cells = "".join(f"{stats(s, a, b)[0]*100:9.1f} / {stats(s, a, b)[1]*100:7.1f}  " for a, b in PERIODS.values())
            print(f"{k:28s}{cells}")
    print("\nFilter switches per year / share of time invested (2006-2026):")
    for n, (sw, inv) in info.items():
        print(f"  {n}-week: {sw:.1f} switches/year · invested {inv*100:.0f}% of the time")


if __name__ == "__main__":
    run()
