"""Agent 3's rules one by one, on small companies built by hand (roadmap section 3, "Agent 3 rules"). Each company is
SEC-shaped (companyfacts, us-gaap, 10-K rows) so the whole path — synonyms, years, measures, type, grade, flags — runs."""

import copy

import pytest

from agents.analysis.measures import Market, analyse
from shared import sectors
from shared.sec.facts import Facts
from tests.fixtures.loader import sec_facts, sec_submissions

TAG = {"revenue": "Revenues", "cost": "CostOfRevenue", "gross": "GrossProfit", "operating": "OperatingIncomeLoss",
       "pretax": "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
       "tax": "IncomeTaxExpenseBenefit", "net": "NetIncomeLoss", "interest": "InterestExpense",
       "op_cash": "NetCashProvidedByUsedInOperatingActivities", "capex": "PaymentsToAcquirePropertyPlantAndEquipment",
       "stock_comp": "ShareBasedCompensation", "dividends": "PaymentsOfDividends", "eps": "EarningsPerShareDiluted",
       "shares": "WeightedAverageNumberOfDilutedSharesOutstanding", "cash": "CashAndCashEquivalentsAtCarryingValue",
       "sti": "ShortTermInvestments", "assets": "Assets", "current_liabilities": "LiabilitiesCurrent",
       "liabilities": "Liabilities", "ltd": "LongTermDebt", "ltd_nc": "LongTermDebtNoncurrent",
       "ltd_c": "LongTermDebtCurrent", "debt_current": "DebtCurrent", "stb": "ShortTermBorrowings",
       "cp": "CommercialPaper", "gain": "GainLossOnSaleOfBusiness"}
INSTANT = {"cash", "sti", "assets", "current_liabilities", "liabilities", "ltd", "ltd_nc", "ltd_c", "debt_current", "stb",
           "cp"}
B = 1e9


def year(r, margin=0.25, **over):
    """One healthy year with revenue r (bn): everything in proportion; `over` replaces or removes (None) a figure."""
    op = r * margin
    figs = {"revenue": r, "cost": r * 0.4, "gross": r * 0.6, "operating": op, "pretax": op, "tax": op * 0.2,
            "net": op * 0.8, "interest": 1.0, "op_cash": op * 0.8 * 1.1, "capex": r * 0.05, "stock_comp": r * 0.01,
            "dividends": op * 0.8 * 0.3, "eps": op * 0.8, "shares": 1.0, "cash": 20.0, "assets": 200.0,
            "current_liabilities": 30.0, "liabilities": 100.0, "ltd": 10.0}
    figs.update(over)
    return {k: v for k, v in figs.items() if v is not None}


def company(years: dict, sic=2000, quarters=False) -> Facts:
    facts = {"Assets": {"units": {"USD": [{"end": "2010-12-31", "val": 1, "accn": "old", "fy": 2010, "form": "10-K",
                                          "filed": "2011-02-01"}]}}}  # an early filing: no IPO year in the window
    for y, figs in years.items():
        for fig, val in figs.items():
            unit = "shares" if fig == "shares" else ("USD/shares" if fig == "eps" else "USD")
            row = {"end": f"{y}-12-31", "val": val * (1 if fig == "eps" else B), "accn": f"acc-{y}", "fy": y,
                   "form": "10-K", "filed": f"{y + 1}-02-01"}
            if fig not in INSTANT:
                row["start"] = f"{y}-01-01"
            facts.setdefault(TAG[fig], {"units": {}})["units"].setdefault(unit, []).append(row)
    return Facts({"facts": {"us-gaap": facts}}, {"sic": str(sic), "name": "TEST CO"}, quarters=quarters)


def grow(g, n=6, start=100.0, first=2020, **per_year):
    return {first + i: year(start * (1 + g) ** i, **per_year) for i in range(n)}


def run(years, sic=2000, **market):
    return analyse(company(years, sic), "TEST", Market(splits=[], **market))


# --- type rules ------------------------------------------------------------------------------------------------------

def test_stalwart_solid():
    r = run(grow(0.10))
    assert (r.lynch_type, r.grade) == ("stalwart", "solid")


def test_slow_and_fast_growers():
    assert run(grow(0.02)).lynch_type == "slow_grower"
    assert run(grow(0.20)).lynch_type == "fast_grower"


def test_three_profitable_years_are_not_unprofitable():
    # a missing year is not a loss (audit, phase 1): 3 years of profit is a slow grower, not `unprofitable`
    r = run(grow(0.02, n=3, first=2023))
    assert r.lynch_type == "slow_grower"


def test_loss_years_with_cash_are_unprofitable_rule_4():
    r = run(grow(0.05, margin=-0.05, op_cash=30.0, capex=1.0))
    assert r.lynch_type == "unprofitable"


def test_amazon_type_loss_with_cash_and_fast_growth_is_a_fast_grower():
    r = run(grow(0.20, margin=-0.02, op_cash=40.0, capex=2.0))
    assert r.lynch_type == "fast_grower"


def test_rivian_type_loss_and_cash_burn_is_unprofitable_rule_2():
    r = run(grow(0.30, margin=-0.5, op_cash=-20.0))
    assert r.lynch_type == "unprofitable"


def test_mixed_profit_and_loss_years_are_cyclical():
    years = grow(0.05)
    years[2022] = year(110, margin=-0.1)
    assert run(years).lynch_type == "cyclical"


def test_a_cyclical_sic_with_a_profit_year_is_cyclical():
    assert run(grow(0.10), sic=3674).lynch_type == "cyclical"


# --- grade rules -----------------------------------------------------------------------------------------------------

def test_shrink_rule():
    r = run(grow(-0.03))
    assert r.grade == "mid" and "shrink_rule" in r.rules


def test_fast_grower_safety():
    # growing fast, decisive measures fine, but a weak operating margin and burning cash → not solid
    years = {y: year(100 * 1.2 ** i, margin=0.03, capex=100 * 1.2 ** i * 0.3, cash=5000.0) for i, y in
             enumerate(range(2020, 2026))}
    r = run(years)
    assert r.lynch_type == "fast_grower" and r.grade == "mid" and "fast_grower_safety" in r.rules


def test_strict_cash_runway_for_a_fast_grower_burning_cash():
    # 10*: ≥ 5 years good, 3–5 mid; a normal company with 4 years would be good
    years = {y: year(100 * 1.2 ** i, margin=0.03, capex=100 * 1.2 ** i * 0.3) for i, y in enumerate(range(2020, 2026))}
    burn = -run(years).free_cash["average_3y"]
    for y in years:
        years[y]["cash"] = 4 * burn / B
    m = run(years).measures["cash_runway"]
    assert m["value"] == pytest.approx(4, rel=0.01) and m["mark"] == "mid"


def test_more_than_half_not_computed_is_unclear():
    years = grow(0.10, op_cash=None, assets=None, operating=None)
    r = run(years)
    assert r.lynch_type == "stalwart" and r.grade == "unclear"


def test_a_decisive_measure_not_computed_is_a_data_check_with_the_reason():
    r = run(grow(0.10, assets=None))
    detail = next(f["detail"] for f in r.flags if "decisive measure capital_return" in f["detail"])
    assert "total assets not found" in detail and "rests on 3 of 4" in detail


# --- price line ------------------------------------------------------------------------------------------------------

def test_lynch_dividend_ratio():
    r = run(grow(0.10), market_value=500 * B)
    p = r.price
    g = min(p["eps_growth_3y"], 0.25) * 100
    yld = r.figures["dividends"][r.last].value / (500 * B) * 100
    assert p["lynch_dividend_ratio"] == pytest.approx((g + yld) / p["pe"])


def test_no_peg_and_no_dividend_ratio_when_eps_falls():
    # decision 2026-10-05: with falling earnings the dividend ratio is not computed either
    r = run(grow(-0.05), market_value=500 * B)
    assert r.price["peg"] is None and r.price["lynch_dividend_ratio"] is None and r.price["pe"] is not None


# --- flags -----------------------------------------------------------------------------------------------------------

def flags(r, kind):
    return [f["detail"] for f in r.flags if f["flag"] == kind]


def test_fcf_falling():
    years = grow(0.05)
    for y, capex in ((2023, 10.0), (2024, 30.0), (2025, 60.0)):
        years[y]["capex"] = capex
    assert flags(run(years), "fcf_falling")


def test_debt_flags():
    years = grow(0.05)
    years[2025]["ltd"] = 150.0  # > total liabilities (100) and +1400%
    details = flags(run(years), "data_check")
    assert any("larger than total liabilities" in d for d in details)
    assert any("debt 10.0 → 150.0" in d for d in details)
    years[2025]["ltd"] = 0.0
    assert any("dropped to zero" in d for d in flags(run(years), "data_check"))


def test_debt_candidates_that_disagree_are_flagged():
    years = grow(0.05)
    for y in years:
        years[y].update({"ltd_nc": 9.0, "ltd_c": 1.0, "ltd": 30.0})
    assert any("candidates disagree" in d for d in flags(run(years), "data_check"))


def test_short_term_borrowings_are_added_once():
    years = grow(0.05)
    for y in years:
        years[y].update({"ltd_nc": 9.0, "ltd_c": 1.0, "stb": 2.0, "cp": 1.5})
    d = company(years).debt()["2025-12-31"]
    assert d.value == pytest.approx(12.0 * B) and "CommercialPaper" not in d.parts


def test_a_group_that_includes_short_term_debt_gets_nothing_added():
    years = grow(0.05)
    for y in years:
        years[y].pop("ltd")
        years[y].update({"ltd_nc": 9.0, "debt_current": 1.0, "stb": 2.0})
    assert company(years).debt()["2025-12-31"].value == pytest.approx(10.0 * B)


def test_gross_profit_must_equal_revenue_minus_cost():
    years = grow(0.05)
    years[2025]["gross"] = years[2025]["revenue"] * 0.9
    assert any("gross profit ≠ revenue − cost" in d for d in flags(run(years), "data_check"))


def test_a_ten_times_revenue_jump_is_flagged_and_kept():
    # decision 2026-10-05: no year is dropped
    years = grow(0.05)
    years[2021] = year(5)
    r = run(years)
    assert any("revenue 5.00 → 110.25" in d for d in flags(r, "data_check"))
    assert "2021-12-31" in r.figures["revenue"]


def test_a_liquid_part_that_disappears_is_flagged_and_asked():
    # decision 2026-10-05: counted as not held, with a data check and a ledger row
    years = grow(0.05)
    years[2024]["sti"] = 15.0
    r = run(years)
    assert any("short_term_investments reported the year before" in d for d in flags(r, "data_check"))
    assert any(m["figure"] == "short_term_investments" and m["year"] == "2025" for m in r.missing)


def test_a_gain_on_a_sale_explaining_most_of_profit_is_one_off():
    years = grow(0.05)
    years[2025]["gain"] = 30.0
    assert flags(run(years), "one_off")


def test_boeing_2025_gain_on_disposal_is_one_off():
    r = analyse(Facts(sec_facts("BA"), sec_submissions("BA"), quarters=False), "BA", Market(splits=[]))
    assert any("gain on a sale (9.7 bn)" in d for d in flags(r, "one_off"))


def test_small_info_lines_are_left_out():
    r = analyse(Facts(sec_facts("SNAP"), sec_submissions("SNAP"), quarters=False), "SNAP", Market(splits=[]))
    assert not any("0.0 bn" in n for n in r.notes)


# --- out of scope by SIC ---------------------------------------------------------------------------------------------

@pytest.mark.parametrize("sic,label", [(6022, "bank"), (6331, "insurance"), (6324, "insurance"), (6798, "reit"),
                                       (4911, "utility"), (4941, "utility"), (4922, None), (6411, None), (7389, None)])
def test_out_of_scope_sic_lists(sic, label):
    assert sectors.out_of_scope_for(sic) == label


def test_three_years_of_coca_cola_is_still_a_slow_grower():
    raw = copy.deepcopy(sec_facts("KO"))
    for body in raw["facts"]["us-gaap"].values():
        for unit, rows in body["units"].items():
            body["units"][unit] = [r for r in rows if r["end"] >= "2023-01-01" and r.get("fy", 0) >= 2023]
    r = analyse(Facts(raw, sec_submissions("KO"), quarters=False), "KO", Market(splits=[]))
    assert r.lynch_type == "slow_grower"
