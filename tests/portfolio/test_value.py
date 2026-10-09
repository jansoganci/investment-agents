"""The shadows follow the same money on the same days; no yearly figure before 12 months; xirr."""

import pytest

from agents.portfolio import run, value
from tests.portfolio.helpers import do, freeze, prices, stock


def test_xirr():
    assert value.xirr([("2025-01-01", -1000.0), ("2026-01-01", 2000.0)]) == pytest.approx(1.0, abs=1e-6)
    assert value.xirr([("2025-01-01", -1000.0), ("2025-07-02", -1000.0), ("2026-01-01", 2100.0)]) == pytest.approx(
        0.0662, abs=1e-3)
    assert value.xirr([("2025-01-01", -1000.0)]) is None


@pytest.fixture
def one_buy(db, monkeypatch):
    stock(db, "X")
    prices(db, "X", [("2025-06-02", 50.0), ("2025-12-01", 60.0), ("2026-05-29", 70.0), ("2026-06-01", 70.0)])
    prices(db, "SPY", [("2025-06-02", 500.0), ("2025-12-01", 540.0), ("2026-05-29", 550.0), ("2026-06-01", 550.0)])
    prices(db, "GC=F", [("2025-06-02", 2000.0), ("2025-12-01", 1800.0), ("2026-05-29", 2400.0), ("2026-06-01", 2400.0)])
    freeze(monkeypatch, "2026-06-01")
    do("bought", "20", "X", "50", "2025-06-02")  # $1,000


def test_the_shadows_follow_the_same_money_on_the_same_days(db, one_buy):
    p = value.compute(db, "2026-05-29")
    assert p.shadows["SPY"].value == pytest.approx(1000 * 550 / 500)  # $1,000 into SPY on the buy day
    assert p.shadows["Gold"].value == pytest.approx(1000 * 2400 / 2000)
    do("sold", "10", "X", "60", "2025-12-01")  # $600 out of me, out of SPY at 540 and out of gold at 1,800 the same day
    p = value.compute(db, "2026-05-29")
    assert p.shadows["SPY"].value == pytest.approx((1000 / 500 - 600 / 540) * 550)
    assert p.shadows["Gold"].value == pytest.approx((1000 / 2000 - 600 / 1800) * 2400)
    assert p.put_in == 1000 and p.got_back == 600
    assert p.shadows["SPY"].return_pct == pytest.approx(((1000 / 500 - 600 / 540) * 550 + 600) / 1000 - 1)


def test_no_yearly_figure_before_12_months(db, one_buy, monkeypatch):
    p = value.compute(db, "2026-05-29")
    assert not p.yearly and p.xirr is None and p.shadows["SPY"].xirr is None
    freeze(monkeypatch, "2026-05-31")
    assert "Return so far: +40.0%   (yearly figure after 12 months)" in run.weekly(db)
    p = value.compute(db, "2026-06-02")  # 12 months after the buy of 2025-06-02
    assert p.yearly and p.xirr == pytest.approx(0.4, abs=1e-3)
    assert p.shadows["SPY"].xirr == pytest.approx(0.1, abs=1e-3)


def test_a_shadow_may_go_below_zero(db, monkeypatch):
    """My decision (2026-10-09): a sale that takes out more than the shadow holds makes it negative; the note says why."""
    stock(db, "X")
    prices(db, "X", [("2026-01-05", 10.0), ("2026-03-02", 50.0), ("2026-03-06", 50.0)])
    prices(db, "SPY", [("2026-01-05", 500.0), ("2026-03-02", 500.0), ("2026-03-06", 500.0)])
    prices(db, "GC=F", [("2026-01-05", 2000.0), ("2026-03-02", 2000.0), ("2026-03-06", 2000.0)])
    freeze(monkeypatch, "2026-03-02")
    do("bought", "100", "X", "10", "2026-01-05")   # $1,000
    do("sold", "50", "X", "50", "2026-03-02")      # $2,500 out
    freeze(monkeypatch, "2026-03-08")
    text = run.weekly(db)
    assert "SPY -$1,500 (+0.0%)" in text
    assert "A shadow is below zero" in text
