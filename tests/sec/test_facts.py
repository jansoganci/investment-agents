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
    # Coca-Cola 2025: cash 10.270 + other short-term investments 3.602 = 13.872 bn (the old prototype missed the second part)
    liq = facts("KO", quarters=False).liquid()["2025-12-31"]
    assert liq.value == pytest.approx(13.872 * BN, rel=1e-4)
    assert set(liq.parts) == {"CashAndCashEquivalentsAtCarryingValue", "OtherShortTermInvestments"}


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
    assert f.ends[-1] == "2026-06-28" and f.ends[-2] == "2025-09-28"


def test_ttm_balance_sheet_comes_from_the_latest_quarter():
    f = facts("SBUX")
    assert f.instant("cash", "2026-06-28").form == "10-Q"


def test_annual_only_view_stops_at_the_last_annual_report():
    assert facts("SBUX", quarters=False).ends[-1] == "2025-09-28"


def test_first_year_for_the_ipo_rule():
    assert facts("RIVN").first_fy == 2021
