"""shared/sec/facts.py on saved SEC data (tests/fixtures/sec)."""

import pytest

from shared.sec.facts import Facts
from tests.fixtures.loader import sec_facts, sec_submissions

BN = 1e9


def facts(ticker, **kw):
    return Facts(sec_facts(ticker), sec_submissions(ticker), **kw)


def test_taxonomy_currency_and_sic():
    ko, nvo = facts("KO"), facts("NVO")
    assert (ko.taxonomy, ko.currency, ko.sic) == ("us-gaap", "USD", 2080)
    assert (nvo.taxonomy, nvo.currency, nvo.sic) == ("ifrs-full", "DKK", 2834)
    assert nvo.annual_only  # a 20-F filer has no quarters


def test_year_ends_one_per_year_with_52_53_week_years():
    ends = facts("SBUX", quarters=False).ends
    years = [e[:4] for e in ends]
    assert len(years) == len(set(years)) and ends[-1] == "2025-09-28"


def test_ko_liquid_assets_add_the_parts():
    # Coca-Cola 2025: cash 10.270 + other short-term investments 3.602 + marketable securities 1.934 = 15.806 bn
    # (the old prototype missed the second part; the marketable securities line is named `MarketableSecurities` since 2021)
    liq = facts("KO", quarters=False).liquid()["2025-12-31"]
    assert liq.value == pytest.approx(15.806 * BN, rel=1e-4)
    assert set(liq.parts) == {"CashAndCashEquivalentsAtCarryingValue", "OtherShortTermInvestments", "MarketableSecurities"}


def test_marketable_securities_with_a_noncurrent_line_is_not_current():
    raw = sec_facts("KO")
    rows = raw["facts"]["us-gaap"]["MarketableSecurities"]["units"]["USD"]
    raw["facts"]["us-gaap"]["MarketableSecuritiesNoncurrent"] = {"units": {"USD": [dict(r) for r in rows]}}
    liq = Facts(raw, sec_submissions("KO"), quarters=False).liquid()["2025-12-31"]
    assert "MarketableSecurities" not in liq.parts


def test_a_liquid_part_that_disappears_is_noted():
    # a part reported the year before but missing now is noted for a data check and the ledger. Nvidia's July 2026 10-Q
    # moved its marketable securities to `DebtSecuritiesCurrent`; with that name taken out the gap shows
    raw = sec_facts("NVDA")
    del raw["facts"]["us-gaap"]["DebtSecuritiesCurrent"]
    f = Facts(raw, sec_submissions("NVDA"))
    f.liquid()
    assert "marketable_securities" in f.liquid_gaps.get(f.ttm_end, [])


def test_nvidia_marketable_securities_under_the_new_name():
    # July 2026: cash 22.443 + `DebtSecuritiesCurrent` 34.143 = 56.586 bn, the figure in the 10-Q (user check, 2026-10-06)
    f = facts("NVDA")
    liq = f.liquid()[f.ttm_end]
    assert liq.value == pytest.approx(56.586 * BN, rel=1e-4)
    assert "DebtSecuritiesCurrent" in liq.parts
    assert not f.liquid_gaps.get(f.ttm_end)


def test_palantir_has_no_debt_and_it_is_counted_as_zero():
    # Palantir repaid its 200 m $ loan in 2021 (`LongTermDebtNoncurrent` = 0, no current-portion line); after that no debt name
    # is reported, only a small fee on an unused credit line (interest expense 3.5 m $ in 2023, 0.2% of revenue)
    f = facts("PLTR")
    d = f.debt()
    assert d["2021-12-31"].value == 0 and not d["2021-12-31"].assumed  # an explicit zero
    for e in ("2022-12-31", "2023-12-31", "2024-12-31", f.ttm_end):
        assert d[e].value == 0 and d[e].assumed
    assert f.debt_assumed == ["2022-12-31", "2023-12-31", "2024-12-31", f.ttm_end]
    assert not [m for m in f.misses if m["figure"] == "debt" and m["end"] > "2021"]


def test_no_debt_is_not_assumed_when_a_balance_is_reported():
    raw = sec_facts("PLTR")
    raw["facts"]["us-gaap"]["NotesPayable"] = {"units": {"USD": [
        {"end": "2024-06-30", "val": 5e7, "form": "10-Q", "filed": "2024-08-01", "accn": "x", "fy": 2024, "fp": "Q2"}]}}
    f = Facts(raw, sec_submissions("PLTR"))
    d = f.debt()
    assert "2024-12-31" not in d and "2023-12-31" in d  # the 12 months up to 2024-12-31 hold a balance
    assert [m["end"] for m in f.misses if m["figure"] == "debt" and m["end"] > "2021"] == ["2024-12-31"]


def test_no_debt_is_not_assumed_when_interest_is_a_real_bill():
    raw = sec_facts("PLTR")
    rows = raw["facts"]["us-gaap"]["InterestExpense"]["units"]["USD"]
    for r in rows:
        if r["end"] == "2023-12-31" and r.get("form") == "10-K":
            r["val"] = 3e7  # 1.6% of revenue
    f = Facts(raw, sec_submissions("PLTR"))
    assert "2023-12-31" not in f.debt()


def test_no_debt_is_not_assumed_without_cash_or_revenue():
    raw = sec_facts("PLTR")
    for name in ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"):
        raw["facts"]["us-gaap"].pop(name, None)
    f = Facts(raw, sec_submissions("PLTR"))
    assert not any(d.assumed for d in f.debt().values())


def test_boeing_debt_group_needs_all_parts():
    # a group counts only if all its parts are found: the current part alone (8.46 bn) must not be taken
    d = facts("BA", quarters=False).debt()["2025-12-31"]
    assert d.value == pytest.approx(53.848 * BN, rel=1e-4)
    assert d.tags == ["LongTermDebt"]


def test_pfizer_2020_debt_is_the_noncurrent_group_not_the_single_item():
    # Pfizer 2020: `LongTermDebt` held a single 4 bn item; the true total is about 40 bn
    d = facts("PFE", quarters=False).debt()["2020-12-31"]
    assert d.value == pytest.approx((37.133 + 2.002 + 0.556) * BN, rel=1e-4)
    assert d.tags[:2] == ["LongTermDebtNoncurrent", "LongTermDebtCurrent"]


def test_ge_debt_long_term_under_the_lease_name_plus_debt_current():
    # GE's 10-Q (2026-06-30): 17.157 bn under `LongTermDebtAndCapitalLeaseObligations` + 2.000 bn `DebtCurrent` = the
    # filing's 19.157 bn of borrowings; before, no group was complete and the debt was asked for
    f = facts("GE")
    d = f.debt()[f.ttm_end]
    assert f.ttm_end == "2026-06-30" and d.value == pytest.approx(19.157 * BN, rel=1e-4)
    assert d.tags == ["LongTermDebtAndCapitalLeaseObligations", "DebtCurrent"]  # short-term debt is in `DebtCurrent`
    assert ("debt", "TTM 2026-06-30") not in {(m["figure"], m["year"]) for m in f.misses}
    # where an older group is complete it still wins, and the new group agrees with it
    d24 = f.debt()["2024-12-31"]
    assert d24.tags[0] == "LongTermDebt" and not d24.disagree and d24.candidates[1] == pytest.approx(d24.candidates[0], rel=0.01)


def test_the_new_debt_group_changes_no_other_company():
    # Boeing has both names too: its `LongTermDebt` stays the total, the new group is only a check within 1%
    for e, d in facts("BA").debt().items():
        assert d.tags == ["LongTermDebt"] and not d.disagree
        assert all(c == pytest.approx(d.candidates[0], rel=0.01) for c in d.candidates)


def test_missing_is_none_and_the_names_tried_are_kept():
    f = facts("RIVN", quarters=False)
    assert f.annual("dividends") == {}
    miss = [m for m in f.misses if m["figure"] == "dividends"]
    assert miss and miss[0]["names_tried"][0] == "PaymentsOfDividends"


def test_every_value_has_its_trace():
    v = facts("KO", quarters=False).annual("revenue")["2025-12-31"]
    assert v.tag == "Revenues" and v.accn and v.form == "10-K"


def _quarter_sum(raw, name, q_end):
    """The last 4 quarters summed by hand from cumulative 10-Q figures (Q4 = year − 9 months)."""
    rows = raw["facts"]["us-gaap"][name]["units"]["USD"]
    best = {}
    for r in rows:
        if "start" in r:
            k = (r["start"], r["end"])
            if k not in best or r["filed"] > best[k]["filed"]:
                best[k] = r
    return best


def test_ttm_is_the_last_four_quarters_from_cumulative_10q_figures():
    # Starbucks: fiscal 2025 ended 2025-09-28; the latest 10-Q is 2026-06-28 (nine months of fiscal 2026)
    f = facts("SBUX")
    assert f.ttm_end == "2026-06-28"
    best = _quarter_sum(sec_facts("SBUX"), "Revenues", "2026-06-28")
    fy = best[("2024-09-30", "2025-09-28")]["val"]
    ytd_9m_prev = best[("2024-09-30", "2025-06-29")]["val"]
    q4 = fy - ytd_9m_prev  # Q4 by subtraction
    q1 = best[("2025-09-29", "2025-12-28")]["val"]
    q2 = best[("2025-12-29", "2026-03-29")]["val"]
    q3 = best[("2026-03-30", "2026-06-28")]["val"]
    assert f.annual("revenue")["2026-06-28"].value == pytest.approx(q4 + q1 + q2 + q3, rel=1e-9)
    assert f.ends[-1] == "2026-06-28" and f.ends[-2] == "2024-09-29"  # the TTM takes the overlapping year's place


def test_ttm_balance_sheet_comes_from_the_latest_quarter():
    f = facts("SBUX")
    assert f.instant("cash", "2026-06-28").form == "10-Q"


def test_annual_only_view_stops_at_the_last_annual_report():
    assert facts("SBUX", quarters=False).ends[-1] == "2025-09-28"


def test_first_year_for_the_ipo_rule():
    assert facts("RIVN").first_fy == 2021


# --- acceptance test, round 1 (2026-10-09; roadmap rules 43–45) -------------------------------------------------------------

def test_a_newer_filing_missing_from_secs_data_is_named():
    ko = facts("KO")  # the July 10-Q was filed 2026-07-29; SEC's data still ends 2026-04-03
    assert ko.newer_filing == {"form": "10-Q", "accn": "0001628280-26-050503", "report_date": "2026-07-03",
                               "filed": "2026-07-29"}
    assert facts("NVDA").newer_filing is None
    from agents.analysis.measures import analyse
    assert [f for f in analyse(ko, "KO").flags if f["flag"] == "stale_data"] == [{"flag": "stale_data", "detail":
            "figures end 2026-04-03; the 10-Q to 2026-07-03 (filed 2026-07-29) is not in SEC's data yet"}]


def test_intels_short_term_investments_count_and_its_marketable_equity_does_not():
    f = facts("INTC")
    v = f.liquid()[f.ends[-1]]
    assert v.parts == {"CashAndCashEquivalentsAtCarryingValue": 12_874e6, "AvailableForSaleSecuritiesDebtSecuritiesCurrent": 16_853e6}
    k = facts("KO")  # a short-term investments line of its own: Coca-Cola's marketable securities still count
    assert "MarketableSecurities" in k.liquid()[k.ends[-1]].parts


def test_the_long_term_debt_line_alone_when_no_current_portion_is_reported():
    f = facts("RIVN")
    d = f.debt()[f.ends[-1]]
    assert d.parts == {"LongTermDebtNoncurrent": 4_444e6}
    n = facts("NVDA")  # a current portion reported: the full group as before
    assert set(n.debt()[n.ends[-1]].parts) == {"LongTermDebtNoncurrent", "LongTermDebtCurrent"}
