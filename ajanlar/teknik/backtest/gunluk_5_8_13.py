"""Selçuk Gönençler 5-8-13 SMA model — daily close backtest vs buy & hold and SPY."""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import yfinance as yf

QUALITY = [
    "AAPL", "MSFT", "GOOGL", "META", "NVDA", "V", "MA", "KO", "PEP", "PG",
    "COST", "HD", "JNJ", "UNH", "ADP", "SPGI", "ROP", "APH", "WM", "NET",
]
FALLEN = ["INTC", "NKE", "MMM", "VZ"]
BENCH = "SPY"
START_DATA, START_TEST, END = "2015-09-01", "2016-01-04", "2026-10-02"
COST_PER_SIDE = 0.001


def positions(
    close: pd.Series,
    *,
    require_stack: bool,
    partial_buy: float = 0.4,
    trim_sell: float = 0.4,
) -> pd.Series:
    """Act only when the state label changes; mixed patterns keep the previous state."""
    s5, s8, s13 = (close.rolling(n).mean() for n in (5, 8, 13))
    a5, a8, a13 = close > s5, close > s8, close > s13
    b5, b8, b13 = close < s5, close < s8, close < s13
    stacked = (s5 > s8) & (s8 > s13)

    pos, state, out = 0.0, None, []
    prev_all_below = False
    for i in range(len(close)):
        if np.isnan(s13.iat[i]):
            out.append(0.0)
            continue
        A5, A8, A13 = bool(a5.iat[i]), bool(a8.iat[i]), bool(a13.iat[i])
        B5, B8, B13 = bool(b5.iat[i]), bool(b8.iat[i]), bool(b13.iat[i])
        all_below = B5 and B8 and B13

        new = state
        if A5 and A8 and A13 and (stacked.iat[i] or not require_stack):
            new = "TEYITLI_AL"
        elif A5 and A8 and B13 and prev_all_below:
            new = "TEMKINLI_AL"
        elif B5 and A8 and A13:
            new = "TEMKINLI_SAT"
        elif B5 and B8 and A13:
            new = "RISK"
        elif all_below:
            new = "SAT"

        if new != state:
            if new == "TEYITLI_AL":
                pos = 1.0
            elif new == "TEMKINLI_AL":
                pos = max(pos, partial_buy)
            elif new == "TEMKINLI_SAT":
                pos = pos * (1 - trim_sell)
            elif new == "SAT":
                pos = 0.0
            state = new
        out.append(pos)
        prev_all_below = all_below
    return pd.Series(out, index=close.index)


def strat_returns(total_return_px: pd.Series, pos: pd.Series, lag: int) -> pd.Series:
    r = total_return_px.pct_change().fillna(0.0)
    held = pos.shift(1 + lag).fillna(0.0)
    cost = held.diff().abs().fillna(held.abs()) * COST_PER_SIDE
    return held * r - cost


def stats(daily: pd.Series) -> dict:
    daily = daily.loc[START_TEST:]
    eq = (1 + daily).cumprod()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iat[-1] ** (1 / years) - 1
    mdd = (eq / eq.cummax() - 1).min()
    return {"cagr": cagr, "maxdd": mdd, "x": eq.iat[-1]}


def run() -> None:
    tickers = QUALITY + FALLEN + [BENCH]
    raw = yf.download(tickers, start=START_DATA, end=END, auto_adjust=False, progress=False)
    chart_px, total_px = raw["Close"], raw["Adj Close"]
    px = total_px
    variants = {
        "base": dict(require_stack=False, lag=0),
        "stack": dict(require_stack=True, lag=0),
        "delay1d": dict(require_stack=False, lag=1),
    }
    rows, sleeves = [], {k: {} for k in ["bh", *variants]}
    for t in QUALITY + FALLEN:
        c = chart_px[t].dropna()
        tr = total_px[t].dropna()
        bh = tr.pct_change().fillna(0.0)
        sleeves["bh"][t] = bh
        row = {"ticker": t, "group": "fallen" if t in FALLEN else "quality"}
        s = stats(bh)
        row.update(bh_cagr=s["cagr"], bh_dd=s["maxdd"])
        for name, v in variants.items():
            p = positions(c, require_stack=v["require_stack"])
            sr = strat_returns(tr, p, v["lag"])
            sleeves[name][t] = sr
            if name == "base":
                st = stats(sr)
                pt = p.loc[START_TEST:]
                years = (pt.index[-1] - pt.index[0]).days / 365.25
                entries = int(((pt > 0) & (pt.shift(1).fillna(0) == 0)).sum())
                row.update(
                    ta_cagr=st["cagr"], ta_dd=st["maxdd"],
                    in_mkt=pt.mean(), entries_per_yr=entries / years,
                    changes_per_yr=int((pt.diff().abs() > 0).sum()) / years,
                )
        rows.append(row)

    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    fmt = df.copy()
    for col in ["bh_cagr", "bh_dd", "ta_cagr", "ta_dd", "in_mkt"]:
        fmt[col] = (fmt[col] * 100).round(1)
    for col in ["entries_per_yr", "changes_per_yr"]:
        fmt[col] = fmt[col].round(1)
    fmt["ta_beats_bh"] = df["ta_cagr"] > df["bh_cagr"]
    print("PER STOCK (base variant, %)")
    print(fmt.to_string(index=False))

    spy = stats(px[BENCH].pct_change().fillna(0.0))
    print(f"\nSPY buy&hold: CAGR {spy['cagr']*100:.1f}%  maxDD {spy['maxdd']*100:.1f}%  x{spy['x']:.2f}")
    for group, names in [("ALL 24", QUALITY + FALLEN), ("QUALITY 20", QUALITY), ("FALLEN 4", FALLEN)]:
        print(f"\nEqual-weight portfolio — {group}")
        for name in ["bh", *variants]:
            port = pd.DataFrame({t: sleeves[name][t] for t in names}).fillna(0.0).mean(axis=1)
            s = stats(port)
            print(f"  {name:10s} CAGR {s['cagr']*100:5.1f}%  maxDD {s['maxdd']*100:6.1f}%  x{s['x']:.2f}")
    print(f"\nTA beats B&H on {int(fmt['ta_beats_bh'].sum())}/{len(fmt)} stocks (base)")
    avg_exposure = df["in_mkt"].mean()
    bh_all = pd.DataFrame(sleeves["bh"]).fillna(0.0).mean(axis=1)
    s = stats(bh_all * avg_exposure)
    print(
        f"Static {avg_exposure*100:.0f}% invested, no timing: "
        f"CAGR {s['cagr']*100:.1f}%  maxDD {s['maxdd']*100:.1f}%"
    )
    print(f"Avg position changes per stock per year: {df['changes_per_yr'].mean():.1f}")


if __name__ == "__main__":
    sys.exit(run())
