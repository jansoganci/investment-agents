"""Weekly rule candidates vs buy & hold — 2006-2015 and 2016-2026 split, incl. 2008."""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from gunluk_5_8_13 import FALLEN, QUALITY, positions

BENCH = "SPY"
START_DATA, END = "2004-06-01", "2026-10-02"
PERIODS = {"2006-2015": ("2006-01-01", "2015-12-31"), "2016-2026": ("2016-01-01", END)}
COST_PER_SIDE = 0.001


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def ma8_rsi(close: pd.Series, *, patient_exit: bool) -> pd.Series:
    ma8, r = close.rolling(8).mean(), rsi(close)
    pos, out = 0.0, []
    for i in range(len(close)):
        if np.isnan(ma8.iat[i]):
            out.append(0.0)
            continue
        above, strong = close.iat[i] > ma8.iat[i], r.iat[i] > 50
        if pos == 0.0 and above and strong:
            pos = 1.0
        elif pos == 1.0 and (not above and (not strong or not patient_exit)):
            pos = 0.0
        out.append(pos)
    return pd.Series(out, index=close.index)


def above_ma(close: pd.Series, n: int = 40) -> pd.Series:
    ma = close.rolling(n).mean()
    return (close > ma).astype(float).where(ma.notna(), 0.0)


def sleeve(total_px: pd.Series, pos: pd.Series, lag: int = 0) -> pd.Series:
    r = total_px.pct_change()
    held = pos.reindex(r.index).shift(1 + lag).fillna(0.0)
    cost = held.diff().abs().fillna(held.abs()) * COST_PER_SIDE
    return (held * r - cost).where(r.notna())


def stats(weekly: pd.Series, start: str, end: str) -> tuple[float, float]:
    w = weekly.loc[start:end].dropna()
    eq = (1 + w).cumprod()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    return eq.iat[-1] ** (1 / years) - 1, (eq / eq.cummax() - 1).min()


def run() -> None:
    names = QUALITY + FALLEN
    raw = yf.download(names + [BENCH], start=START_DATA, end=END, auto_adjust=False, progress=False)
    chart_w = raw["Close"].resample("W-FRI").last()
    total_w = raw["Adj Close"].resample("W-FRI").last()

    spy_on = above_ma(chart_w[BENCH].dropna())
    rules = {
        "1 weekly 5-8-13 (40%)": lambda c: positions(c, require_stack=False),
        "2a MA8+RSI, exit <MA8": lambda c: ma8_rsi(c, patient_exit=False),
        "2b MA8+RSI, exit both": lambda c: ma8_rsi(c, patient_exit=True),
        "3 above 40w MA": above_ma,
        "4 SPY>40w filter": lambda c: spy_on.reindex(c.index).fillna(0.0),
    }

    sleeves: dict[str, dict[str, pd.Series]] = {"buy & hold": {}, **{k: {} for k in rules}}
    delayed: dict[str, dict[str, pd.Series]] = {k: {} for k in rules}
    churn: dict[str, list[float]] = {k: [] for k in rules}
    exposure: dict[str, list[float]] = {k: [] for k in rules}
    for t in names:
        c, tr = chart_w[t].dropna(), total_w[t].dropna()
        sleeves["buy & hold"][t] = tr.pct_change()
        for k, fn in rules.items():
            p = fn(c)
            sleeves[k][t] = sleeve(tr, p)
            delayed[k][t] = sleeve(tr, p, lag=1)
            pt = p.loc["2006-01-01":]
            yrs = (pt.index[-1] - pt.index[0]).days / 365.25
            churn[k].append(float((pt.diff().abs() > 0).sum()) / yrs)
            exposure[k].append(float(pt.mean()))

    def port(d: dict[str, pd.Series], group: list[str]) -> pd.Series:
        return pd.DataFrame({t: d[t] for t in group}).mean(axis=1, skipna=True)

    spy_bh = total_w[BENCH].pct_change()
    for label, group in [("ALL 24", names), ("QUALITY 20", QUALITY), ("FALLEN 4", FALLEN)]:
        print(f"\n=== {label} — equal weight, CAGR / maxDD (%) ===")
        hdr = f"{'rule':24s}" + "".join(f"{p:>22s}" for p in PERIODS) + f"{'trades/yr':>11s}{'in mkt':>8s}"
        print(hdr)
        rows = [("SPY buy & hold", spy_bh, None)] if label == "ALL 24" else []
        rows += [(k, port(v, group), k) for k, v in sleeves.items()]
        for k, series, rk in rows:
            cells = ""
            for s, e in PERIODS.values():
                cg, dd = stats(series, s, e)
                cells += f"{cg*100:9.1f} / {dd*100:7.1f}  "
            extra = ""
            if rk in churn:
                extra = f"{np.mean(churn[rk]):11.1f}{np.mean(exposure[rk])*100:7.0f}%"
            print(f"{k:24s}{cells}{extra}")
        if label == "ALL 24":
            print("  -- same rules, executed one week late --")
            for k, v in delayed.items():
                cells = ""
                for s, e in PERIODS.values():
                    cg, dd = stats(port(v, group), s, e)
                    cells += f"{cg*100:9.1f} / {dd*100:7.1f}  "
                print(f"{k:24s}{cells}")

    print("\n=== Per-stock: rules beating buy & hold on CAGR (2006-2026 where listed) ===")
    for k in rules:
        wins = 0
        for t in names:
            a, _ = stats(sleeves[k][t], "2006-01-01", END)
            b, _ = stats(sleeves["buy & hold"][t], "2006-01-01", END)
            wins += a > b
        print(f"  {k:24s} {wins}/{len(names)}")


if __name__ == "__main__":
    run()
