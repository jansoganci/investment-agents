"""Agent 3's numbers on saved SEC data (tests/fixtures/sec). Golden set: BAGLAM.md section 9."""

import copy

import pytest

from agents.analysis.measures import Market, analyse, verdicts
from shared.sec.facts import Facts
from tests.fixtures.loader import sec_facts, sec_submissions

GOLDEN = {  # ticker: (grade, lynch_type) — BAGLAM.md section 9, after the reviews (10/10)
    "KO": ("mid", "slow_grower"), "NVDA": ("solid", "cyclical"), "NKE": ("mid", "slow_grower"),
    "SBUX": ("mid", "slow_grower"), "PFE": ("weak", "slow_grower"), "INTC": ("weak", "cyclical"),
    "BA": ("weak", "cyclical"), "SNAP": ("weak", "unprofitable"), "DOW": ("weak", "cyclical"),
    "RIVN": ("weak", "unprofitable"),
}
# split history as Yahoo lists it (only the splits inside the years looked at matter)
SPLITS = {"NVDA": [("2021-07-20", 4.0), ("2024-06-10", 10.0)]}


def run(ticker, quarters=False, splits=None, **market):
    f = Facts(sec_facts(ticker), sec_submissions(ticker), quarters=quarters)
    return analyse(f, ticker, Market(splits=SPLITS.get(ticker, []) if splits is None else splits, **market))


@pytest.mark.parametrize("ticker", GOLDEN)
def test_golden_set_on_the_annual_reports(ticker):
    r = run(ticker)
    assert (r.grade, r.lynch_type) == GOLDEN[ticker]


# With the last 4 quarters in place of the last annual report (decision 2026-10-05). A grade that differs from the golden
# set must be explained by the new filing: Coca-Cola's TTM to 2026-04-03 leaves the 2025 fairlife one-off out, so free cash
# covers the dividends over 5 years again (BAGLAM.md section 9: "back to solid once the one-offs leave the window").
TTM_GRADE = {t: g for t, (g, _) in GOLDEN.items()} | {"KO": "solid"}


@pytest.mark.parametrize("ticker", GOLDEN)
def test_golden_set_with_the_last_four_quarters(ticker):
    r = run(ticker, quarters=True)
    assert r.grade == TTM_GRADE[ticker]


def test_ttm_replaces_the_overlapping_annual_report():
    r = run("KO", quarters=True)
    assert r.ends[-2:] == ["2024-12-31", "2026-04-03"]  # 2025 annual is not counted next to the TTM
    assert r.measures["dividend_cover"]["mark"] == "good"


def test_coca_cola_flags_and_borderline():
    r = run("KO")
    kinds = {f["flag"] for f in r.flags}
    assert {"one_off", "borderline"} <= kinds
    assert r.measures["capital_return"]["value"] == pytest.approx(0.1465, abs=0.001)  # with the marketable securities
    assert r.measures["dividend_cover"]["mark"] == "weak"  # the one-offs push dividend cover 2% short


def test_nvidia_liquid_drop_is_a_data_check():
    assert any(f["flag"] == "data_check" and "liquid" in f["detail"] for f in run("NVDA").flags)


def test_nvidia_split_adjusted_only_when_yahoo_confirms():
    ok = run("NVDA").measures["share_count"]
    assert ok["value"] == pytest.approx(-0.023, abs=0.001) and "×10 adjusted" in ok["note"]
    r = run("NVDA", splits=[])
    assert r.measures["share_count"]["value"] is None
    assert any(f["flag"] == "data_check" and "share-count" in f["detail"] for f in r.flags)
    assert run("NVDA", splits=None).measures["share_count"]["value"] is not None  # SPLITS default


def _reverse_split_ge():
    """GE's real figures, with the share counts before 2022 made 8 times larger: what SEC shows when a 1:8 reverse split
    is not restated (GE's own 2021 reverse split is already restated in SEC's data)."""
    raw = copy.deepcopy(sec_facts("GE"))
    for r in raw["facts"]["us-gaap"]["WeightedAverageNumberOfDilutedSharesOutstanding"]["units"]["shares"]:
        if r["end"] < "2021-06-30":
            r["val"] *= 8
    return Facts(raw, sec_submissions("GE"), quarters=False)


def test_a_reverse_split_is_adjusted_only_when_yahoo_confirms():
    f = _reverse_split_ge()
    ok = analyse(f, "GE", Market(splits=[("2021-08-02", 0.125)])).measures["share_count"]
    assert ok["value"] == pytest.approx(-0.025, abs=0.002) and "×0.125 adjusted" in ok["note"]
    bad = analyse(_reverse_split_ge(), "GE", Market(splits=[]))
    assert bad.measures["share_count"]["value"] is None


def test_spin_off_ratios_are_not_splits():
    # Yahoo lists spin-offs as odd ratios (Pfizer ×1.054); they never confirm a split
    f = _reverse_split_ge()
    assert analyse(f, "GE", Market(splits=[("2021-08-02", 1.054)])).measures["share_count"]["value"] is None


def test_the_ipo_year_is_skipped():
    assert run("RIVN").measures["share_count"]["note"].startswith("2022→")


def test_novo_nordisk_ifrs_annual():
    r = run("NVO")
    assert (r.taxonomy, r.currency, r.ttm) == ("ifrs-full", "DKK", False)
    assert (r.lynch_type, r.grade) == ("fast_grower", "mid")
    assert r.measures["margin_stability"]["mark"] == "weak"


def test_novo_nordisk_price_line_converts_dkk():
    fx, mv = 0.15, 300e9  # DKK → USD and a market value in USD
    r = run("NVO", market_value=mv, fx=fx)
    net = r.figures["net"][r.last].value
    assert r.price["pe"] == pytest.approx(mv / (net * fx))
    fcf3 = r.free_cash["average_3y"]
    assert r.price["fcf_yield"] == pytest.approx(fcf3 * fx / mv)


def test_no_market_value_means_no_price_line():
    p = run("KO").price
    assert p["pe"] is None and p["peg"] is None and p["fcf_yield"] is None


def test_peg_growth_is_capped_at_25_percent():
    r = run("NVDA", market_value=4.0e12)
    assert r.price["eps_growth_3y"] > 0.25
    assert r.price["peg"] == pytest.approx(r.price["pe"] / 25)
    assert verdicts(r.price)["fcf_yield"] in ("attractive", "fair", "expensive")


def test_a_bank_is_out_of_scope():
    r = run("JPM")
    assert (r.out_of_scope, r.grade, r.lynch_type, r.measures) == ("bank", "unclear", None, {})


def test_no_revenue_in_three_years_is_pre_revenue():
    raw = copy.deepcopy(sec_facts("RIVN"))
    for name in ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"):
        raw["facts"]["us-gaap"].pop(name, None)
    r = analyse(Facts(raw, sec_submissions("RIVN"), quarters=False), "RIVN", Market(splits=[]))
    assert (r.out_of_scope, r.grade) == ("pre_revenue", "unclear")
    assert {m["figure"] for m in r.missing} == {"revenue"}  # the ledger catches a missing name


def test_missing_is_not_zero():
    r = run("SNAP")
    assert r.measures["cash_conversion"]["value"] is None  # net profit ≤ 0: not computed, not 0
    assert run("RIVN").measures["dividend_cover"]["mark"] is None  # no dividend figure: not computed, not "weak"


def test_sector_from_the_sic_code():
    assert run("NKE").sector == "Consumer Discretionary"
    assert run("KO").sector == "Consumer Staples"
    assert run("DOW").sector == "Materials"
