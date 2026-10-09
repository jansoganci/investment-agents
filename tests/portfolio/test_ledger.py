"""The hand-checked ledger (plan, phase 3): two buys, a sale, a dividend, a split — against a spreadsheet worked out by hand.

    2026-01-05  buy  10 KO at $100.00 + $1 fee                  put in $1,001.00
    2026-02-02  buy   5 V  at $300.00 + $1 fee                  put in $1,501.00
    2026-03-02  KO dividend $0.50 × 10 shares × (1 − 20%)       got back $4.00
    2026-04-01  KO split 2:1 → 20 shares; cost $1,001 → average $50.05
    2026-05-04  sell  8 KO at $60.00 − $1 fee                   got back $479.00; cost out 8 × $50.05 = $400.40
    2026-06-05  Friday close: KO $65, V $330, SPY $550, gold $2,250 / oz

    KO 12 shares · cost $600.60 · value $780.00 · gain $179.40 (+29.87%) · weight 32.10%
    V   5 shares · cost $1,501.00 · value $1,650.00 · gain $149.00 (+9.93%) · weight 67.90%
    stock portfolio $2,430.00 · put in $2,502.00 · got back $483.00 · return (2,430 + 483) ÷ 2,502 − 1 = +16.43%

    SPY total-return level (dividend $5 on 03-20 reinvested): 500 · 520 · 510 · 505 · 545.40 · 555.50
    SPY shadow units = 1001/500 + 1501/520 − 4/510 − 479/545.40 = 4.002441 → × 555.50 = $2,223.36 (+8.17%)
    gold shadow units = 1001/2000 + 1501/2100 − 4/2050 − 479/2200 = 0.995583 → × 2,250 = $2,240.06 (+8.84%)
    gold 10 g × 2,250 / 31.1035 = $723.39 · BES 100,000 TL / 40 = $2,500.00
    total wealth $5,653.39 = 0.7067% of $800,000
"""

import pytest

from agents.portfolio import run, value
from tests.portfolio.helpers import do, freeze, price, prices, stock


@pytest.fixture
def ledger(db, monkeypatch):
    ko, v = stock(db, "KO"), stock(db, "V")
    prices(db, "KO", [("2026-01-05", 100.0), ("2026-02-02", 102.0), ("2026-03-02", 105.0, 0.50),
                      ("2026-03-31", 120.0),            # stored the night before the split: still in the old shares
                      ("2026-04-01", 60.0, None, 2.0), ("2026-05-04", 60.0), ("2026-06-05", 65.0)])
    prices(db, "V", [("2026-02-02", 300.0), ("2026-05-04", 310.0), ("2026-06-05", 330.0)])
    prices(db, "SPY", [("2026-01-05", 500.0), ("2026-02-02", 520.0), ("2026-03-02", 510.0), ("2026-03-20", 500.0, 5.0),
                       ("2026-05-04", 540.0), ("2026-06-05", 550.0)])
    prices(db, "GC=F", [("2026-01-05", 2000.0), ("2026-02-02", 2100.0), ("2026-03-02", 2050.0), ("2026-05-04", 2200.0),
                        ("2026-06-05", 2250.0)])
    price(db, "TRY=X", "2026-06-04", 40.0)
    freeze(monkeypatch, "2026-06-05")
    assert do("bought", "10", "KO", "100", "2026-01-05", "1")[0] == 0
    assert do("bought", "5", "V", "300", "2026-02-02", "1")[0] == 0
    assert do("sold", "8", "KO", "60", "2026-05-04", "1")[0] == 0
    assert do("gold", "10", "3000")[0] == 0
    assert do("bes", "5000", "100000")[0] == 0
    return {"KO": ko, "V": v}


def test_the_hand_checked_ledger_equals_the_spreadsheet(db, ledger):
    p = value.compute(db, "2026-06-05")
    ko, v = p.holdings
    assert (ko.ticker, ko.quantity) == ("KO", 12)
    assert ko.average_cost == pytest.approx(50.05) and ko.cost == pytest.approx(600.60)
    assert ko.value == pytest.approx(780.00) and ko.gain == pytest.approx(179.40) and ko.gain_pct == pytest.approx(0.298701, abs=1e-6)
    assert (v.ticker, v.quantity) == ("V", 5)
    assert v.average_cost == pytest.approx(300.20) and v.value == pytest.approx(1650.00) and v.gain == pytest.approx(149.00)
    assert ko.weight == pytest.approx(0.320988, abs=1e-6) and v.weight == pytest.approx(0.679012, abs=1e-6)
    assert p.stock_value == pytest.approx(2430.00)
    assert p.put_in == pytest.approx(2502.00) and p.got_back == pytest.approx(483.00)
    assert p.return_pct == pytest.approx(0.164269, abs=1e-6)
    assert p.shadows["SPY"].value == pytest.approx(2223.36, abs=0.01)
    assert p.shadows["SPY"].return_pct == pytest.approx(0.081677, abs=1e-6)
    assert p.shadows["Gold"].value == pytest.approx(2240.06, abs=0.01)
    assert p.shadows["Gold"].return_pct == pytest.approx(0.088354, abs=1e-6)
    assert p.wealth.gold_grams == 10 and p.wealth.gold_value == pytest.approx(723.39, abs=0.01)
    assert p.wealth.bes_value == pytest.approx(2500.00)
    assert p.wealth.total == pytest.approx(5653.39, abs=0.01) and p.wealth.share == pytest.approx(0.0070667, abs=1e-7)


def test_the_weekly_run_records_the_dividend_the_split_and_the_snapshot(db, ledger, monkeypatch):
    freeze(monkeypatch, "2026-06-07")  # Sunday → the Friday close of 2026-06-05
    text = run.weekly(db)
    assert text.startswith("PORTFOLIO — week ending 2026-06-05")
    assert "Ledger: KO split 2:1 — your 10 shares are now 20; check it in Midas" in text
    assert "Ledger: KO dividend 2026-03-02: 10 shares × $0.5 − 20% withholding = $4.00" in text
    assert "Return so far: +16.4%   (yearly figure after 12 months)" in text
    assert "Same money, same days → SPY $2,223 (+8.2%) · Gold $2,240 (+8.8%)" in text
    assert "You vs SPY: +$207" in text
    assert "KO 12 @ $50.05 · $780 · 32% · +$179 (+29.9%)" in text
    assert "Total wealth: stocks $2.4k + gold 10 g $0.7k + BES $2.5k = $5.7k · 0.7% of $800k" in text
    rows = db.execute("SELECT kind, date, quantity, amount, split_ratio FROM holdings WHERE command_id IS NULL "
                      "AND void = 0 ORDER BY date").fetchall()
    assert rows == [("dividend", "2026-03-02", 10, 4.0, None), ("split", "2026-04-01", None, None, 2.0)]
    snap = db.execute("SELECT stock_value, put_in, got_back, return_pct, spy_shadow, gold_shadow, gold_value, bes_value, "
                      "total_wealth FROM snapshots WHERE week_end='2026-06-05'").fetchone()
    assert snap == pytest.approx((2430.0, 2502.0, 483.0, 0.164269, 2223.356, 2240.063, 723.391, 2500.0, 5653.391), abs=1e-3)


def test_a_second_run_of_the_same_week_writes_nothing(db, ledger, monkeypatch):
    freeze(monkeypatch, "2026-06-07")
    run.weekly(db)
    count = db.execute("SELECT (SELECT count(*) FROM holdings), (SELECT count(*) FROM signals), "
                       "(SELECT count(*) FROM snapshots)").fetchone()
    text = run.weekly(db)
    assert "already recorded" in text
    assert db.execute("SELECT (SELECT count(*) FROM holdings), (SELECT count(*) FROM signals), "
                      "(SELECT count(*) FROM snapshots)").fetchone() == count


def test_a_dividend_follows_a_cancelled_buy(db, ledger, monkeypatch):
    """The code's dividend rows are worked out again: a buy cancelled later voids its dividend and adds the right one."""
    freeze(monkeypatch, "2026-06-07")
    run.weekly(db)
    assert do("bought", "10", "KO", "101", "2026-02-02")[0] == 0  # a back-dated buy before the ex-date: 20 shares then
    freeze(monkeypatch, "2026-06-14")
    price(db, "KO", "2026-06-12", 66.0)
    text = run.weekly(db)
    assert "KO dividend 2026-03-02: 20 shares × $0.5 − 20% withholding = $8.00 (corrected)" in text
    rows = db.execute("SELECT amount, void FROM holdings WHERE kind='dividend' ORDER BY id").fetchall()
    assert rows == [(4.0, 1), (8.0, 0)]  # the old row is kept, marked void


def test_portfolio_command_reads_the_latest_closes(db, ledger, monkeypatch):
    from shared import commands

    freeze(monkeypatch, "2026-06-07")
    run.weekly(db)
    code, text = commands.run(["portfolio"])
    assert code == 0 and text.startswith("PORTFOLIO — latest closes, 2026-06-07")
    assert "V 5 @ $300.20 · $1,650 · 68% · +$149 (+9.9%)" in text
    assert "from the weekly run of 2026-06-05" in text
