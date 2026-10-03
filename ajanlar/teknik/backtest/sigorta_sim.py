"""How much market-filter insurance? Simulation with monthly buying.

24 stocks equal weight. Start 13,000 USD, then 1,000 USD on the first Friday of every month (same ratio as 500k TL start /
~37.5k TL a month). Filter: SPY weekly close vs its 40-week average (red below, green above), acted on at that close.
  A none       — buy every month, never sell
  B new money  — red: holdings stay, monthly money waits in cash; green: all cash is invested
  C half       — turns red: sell half of every holding; green: buy the same stocks back in the same mix + invest waiting money
  D all        — turns red: sell everything; green: buy everything back in the same mix + invest waiting money
0.1% per trade side. Cash earns nothing; no tax; no TL/USD. Periods start from zero: 2006-2015 (incl. 2008), 2016-2026.
Run: uv run --with yfinance --with pandas python sigorta_sim.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yfinance as yf

from gunluk_5_8_13 import FALLEN, QUALITY
from haftalik import BENCH, END, PERIODS, START_DATA

START, MONTHLY, COST, MA = 13_000.0, 1_000.0, 0.001, 40


def xirr(flows: list[tuple[pd.Timestamp, float]]) -> float:
    t0 = flows[0][0]
    def npv(r):
        return sum(v / (1 + r) ** ((d - t0).days / 365.25) for d, v in flows)
    lo, hi = -0.99, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if npv(mid) > 0 else (lo, mid)
    return mid


def simulate(rets: pd.DataFrame, red: pd.Series, mode: str):
    names = list(rets.columns)
    hold = pd.Series(0.0, index=names)
    cash, units, nav = 0.0, 0.0, 1.0   # cash = waiting monthly money
    sold = pd.Series(0.0, index=names)   # money from sales, kept per stock so it goes back in the same mix
    navs, flows, trades, last_month, was_red = [], [], 0, None, False

    def buy(amount: float, avail: list[str]):
        nonlocal hold
        if amount <= 0 or not avail:
            return 0.0
        each = amount * (1 - COST) / len(avail)
        hold[avail] += each
        return amount

    for i, d in enumerate(rets.index):
        r = rets.iloc[i]
        hold = hold * (1 + r.fillna(0.0))
        avail = [t for t in names if not np.isnan(r[t])] if i else [t for t in names if not np.isnan(rets.iloc[1][t])]
        value = hold.sum() + cash + sold.sum()
        if units:
            nav = value / units
        is_red = bool(red.get(d, False))
        if mode != "none":
            if is_red and not was_red:          # turns red
                frac = {"half": 0.5, "all": 1.0}.get(mode, 0.0)
                if frac:
                    out = hold * frac
                    sold += out * (1 - COST)
                    hold -= out
                    trades += 1
            if not is_red and was_red:  # turns green: sales back in the same mix, waiting money split equally
                if sold.sum() > 0:
                    hold += sold * (1 - COST)
                    sold[:] = 0.0
                    trades += 1
                if cash > 0:
                    cash -= buy(cash, avail)
        was_red = is_red
        contrib = START if i == 0 else (MONTHLY if d.month != last_month else 0.0)
        last_month = d.month
        if contrib:
            units += contrib / nav if units else contrib  # nav = 1.0 at start
            flows.append((d, -contrib))
            if mode != "none" and is_red:
                cash += contrib
            else:
                buy(contrib, avail)
        navs.append((hold.sum() + cash + sold.sum()) / units)
    final = hold.sum() + cash + sold.sum()
    flows.append((rets.index[-1], final))
    nav_s = pd.Series(navs, index=rets.index)
    dd = (nav_s / nav_s.cummax() - 1).min()
    years = (rets.index[-1] - rets.index[0]).days / 365.25
    put_in = -sum(v for _, v in flows[:-1])
    return final, put_in, xirr(flows), dd, trades / years


def run() -> None:
    names = QUALITY + FALLEN
    raw = yf.download(names + [BENCH], start=START_DATA, end=END, auto_adjust=False, progress=False)
    close_w = raw["Close"].resample("W-FRI").last()
    total_w = raw["Adj Close"].resample("W-FRI").last()
    spy = close_w[BENCH].dropna()
    ma = spy.rolling(MA).mean()
    red = (spy < ma).where(ma.notna(), False)
    rets_all = total_w[names].pct_change()
    print(f"Start {START:,.0f} USD + {MONTHLY:,.0f} USD a month · SPY {MA}-week filter · 24 stocks\n")
    for label, (a, b) in PERIODS.items():
        rets = rets_all.loc[a:b]
        print(f"=== {label} ===")
        print(f"{'option':22s}{'put in':>12s}{'final':>14s}{'×':>6s}{'yearly':>9s}{'largest drop':>14s}{'sell+rebuy/yr':>14s}")
        for mode, name in (("none", "A none"), ("new", "B new money waits"), ("half", "C half"), ("all", "D all")):
            final, put_in, irr, dd, tpy = simulate(rets, red, mode)
            print(f"{name:22s}{put_in:12,.0f}{final:14,.0f}{final/put_in:6.2f}{irr*100:8.1f}%{dd*100:13.1f}%{tpy:11.1f}")
        print()


if __name__ == "__main__":
    run()
