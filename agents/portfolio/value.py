"""Value, weights, the SPY and gold shadows, the return and total wealth (agent 4 rules 2–4). All figures in USD.

- **Return:** (value now + got back) ÷ put in − 1. For the first 12 months only this total; after 12 months also the yearly
  return that counts every buy (`xirr`).
- **Shadows:** every money movement is copied on the same day for the same dollars: a buy puts money into the shadow, a sale or
  a dividend takes money out. Cash waiting at the broker is not counted. A shadow may go below zero when a sale takes out more
  than it holds (my decision, 2026-10-09: the arithmetic stays honest — same money, same days).
- **Total wealth:** stocks + gold + BES against the goal in `settings.yaml`. Gold = my grams × the world gold price per gram
  (Yahoo's ounce price ÷ 31.1035); BES = the latest total I entered, at that entry's USD/TRY rate. Emergency cash is not counted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from shared import config
from agents.portfolio import ledger as ledgermod
from agents.portfolio.marketdata import GOLD, SPY, Series, gold_gram_usd, level_on

PRICE_GAP_DAYS = 10  # a close older than this is not used as "now"


@dataclass
class Holding:
    stock_id: int
    ticker: str
    quantity: float
    cost: float
    average_cost: float | None
    close_day: str | None = None
    close: float | None = None
    value: float | None = None
    weight: float | None = None
    gain: float | None = None
    gain_pct: float | None = None


@dataclass
class Shadow:
    name: str
    value: float | None
    return_pct: float | None
    xirr: float | None = None


@dataclass
class Wealth:
    gold_grams: float = 0.0
    gold_value: float | None = 0.0
    bes_value: float | None = 0.0
    total: float | None = None
    goal: float = 0.0
    share: float | None = None


@dataclass
class Portfolio:
    as_of: str
    holdings: list[Holding] = field(default_factory=list)
    stock_value: float = 0.0
    put_in: float = 0.0
    got_back: float = 0.0
    return_pct: float | None = None
    xirr: float | None = None
    yearly: bool = False                    # 12 months since the first buy
    shadows: dict[str, Shadow] = field(default_factory=dict)
    wealth: Wealth = field(default_factory=Wealth)
    no_price: list[str] = field(default_factory=list)
    first_buy: str | None = None
    ledger: ledgermod.Ledger | None = None


def one_year_after(day: str) -> str:
    d = date.fromisoformat(day)
    try:
        return d.replace(year=d.year + 1).isoformat()
    except ValueError:  # 29 February
        return d.replace(year=d.year + 1, day=28).isoformat()


def xirr(flows: list[tuple[str, float]]) -> float | None:
    """The yearly rate r with Σ amount ÷ (1 + r)^(years since the first flow) = 0 (bisection). None when it has no answer."""
    if not flows or not any(a < 0 for _, a in flows) or not any(a > 0 for _, a in flows):
        return None
    t0 = min(date.fromisoformat(d) for d, _ in flows)
    pts = [((date.fromisoformat(d) - t0).days / 365.0, a) for d, a in flows]

    def npv(r: float) -> float:
        return sum(a / (1 + r) ** t for t, a in pts)

    lo, hi = -0.9999, 100.0
    f_lo, f_hi = npv(lo), npv(hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = npv(mid)
        if f_lo * f_mid <= 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def _total(value: float, put_in: float, got_back: float) -> float | None:
    return (value + got_back) / put_in - 1 if put_in > 0 else None


def _shadow(name: str, levels: list[tuple[str, float]], flows: list[tuple[str, float]], as_of: str, put_in: float,
            got_back: float, yearly: bool) -> Shadow:
    units = 0.0
    for day, amount in flows:
        level = level_on(levels, day)
        if level is None:
            return Shadow(name, None, None)
        units -= amount / level
    now = level_on(levels, as_of)
    if now is None:
        return Shadow(name, None, None)
    value = units * now
    return Shadow(name, value, _total(value, put_in, got_back), xirr(flows + [(as_of, value)]) if yearly else None)


def other_assets(conn, as_of: str) -> Wealth:
    w = Wealth()
    w.gold_grams = conn.execute("SELECT coalesce(sum(grams), 0) FROM other_assets WHERE kind='gold' AND void=0 AND date <= ?",
                                (as_of,)).fetchone()[0]
    if abs(w.gold_grams) > 1e-9:
        gram = gold_gram_usd(conn, as_of)
        w.gold_value = w.gold_grams * gram[1] if gram else None
    bes = conn.execute("SELECT total_try, usdtry FROM other_assets WHERE kind='bes' AND void=0 AND date <= ? "
                       "ORDER BY date DESC, id DESC LIMIT 1", (as_of,)).fetchone()
    w.bes_value = bes[0] / bes[1] if bes else 0.0
    return w


def compute(conn, as_of: str) -> Portfolio:
    led = ledgermod.replay(conn, as_of)
    p = Portfolio(as_of, put_in=led.put_in, got_back=led.got_back, first_buy=led.first_buy, ledger=led)
    for pos in led.held():
        h = Holding(pos.stock_id, pos.ticker, pos.quantity, pos.cost, pos.average_cost)
        got = Series(conn, pos.ticker, as_of).close_on(as_of, PRICE_GAP_DAYS)
        if got is None:
            p.no_price.append(pos.ticker)
        else:
            h.close_day, h.close = got
            h.value = pos.quantity * h.close
            h.gain = h.value - pos.cost
            h.gain_pct = h.gain / pos.cost if pos.cost > 0 else None
        p.holdings.append(h)
    p.stock_value = sum(h.value for h in p.holdings if h.value is not None)
    for h in p.holdings:
        if h.value is not None and p.stock_value > 0:
            h.weight = h.value / p.stock_value
    p.return_pct = _total(p.stock_value, p.put_in, p.got_back)
    p.yearly = bool(led.first_buy) and one_year_after(led.first_buy) <= as_of
    flows = [(d, a) for d, a, _, _ in led.flows]
    if p.yearly and not p.no_price:
        p.xirr = xirr(flows + [(as_of, p.stock_value)])
    if flows:
        p.shadows["SPY"] = _shadow("SPY", Series(conn, SPY, as_of).total_return(), flows, as_of, p.put_in, p.got_back,
                                   p.yearly)
        p.shadows["Gold"] = _shadow("Gold", Series(conn, GOLD, as_of).closes(), flows, as_of, p.put_in, p.got_back,
                                    p.yearly)
    w = other_assets(conn, as_of)
    w.goal = float(config.settings()["portfolio"]["goal_usd"])
    if w.gold_value is not None and w.bes_value is not None and not p.no_price:
        w.total = p.stock_value + w.gold_value + w.bes_value
        w.share = w.total / w.goal if w.goal else None
    p.wealth = w
    return p
