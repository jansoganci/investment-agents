from datetime import date, timedelta

import pytest

from agents.analysis.measures import Market, analyse
from agents.research import health, score, tailwind
from shared.sec.facts import Facts
from tests.fixtures.loader import sec_facts, sec_submissions

ENDS = ["2022-12-31", "2023-12-31", "2024-12-31", "2025-12-31"]
GOOD = dict(revenue=[100, 110, 120, 130], operating=[10, 11, 12, 13], fcf=[5, 6, 7, 8], shares=[100, 100, 99, 98],
            debt=[50, 50, 50, 50], liquid=[60, 60, 60, 60])


def series(**kw):
    s = {"ends": ENDS, "revenue": {}, "operating": {}, "fcf": {}, "shares": {}, "debt": {}, "liquid": {}}
    for name, values in kw.items():
        s[name] = {e: v for e, v in zip(ENDS, values) if v is not None}
    return s


def statuses(s):
    return {c["name"]: c["status"] for c in health.run_checks(s)}


# --- quick health -------------------------------------------------------------------------------------------------------------

def test_a_healthy_company_passes_all_five_and_gets_two_points():
    checks = health.run_checks(series(**GOOD))
    assert {c["status"] for c in checks} == {"pass"} and health.points_for(checks) == 2


def test_each_check_fails_on_its_own_threshold():
    bad = dict(GOOD, operating=[10, 11, 12, -1], fcf=[5, -6, -7, 8], revenue=[130, 120, 110, 100],
               shares=[100, 100, 105, 115], debt=[500] * 4, liquid=[10] * 4)
    assert statuses(series(**bad)) == {"profit": "fail", "cash": "fail", "shrink": "fail", "debt": "fail", "dilution": "fail"}
    assert health.points_for(health.run_checks(series(**bad))) == 0


def test_cash_needs_two_positive_years_of_the_last_three_and_a_missing_year_can_leave_it_unclear():
    assert statuses(series(**dict(GOOD, fcf=[5, -1, 7, 8])))["cash"] == "pass"          # -1, 7, 8 → 2 positive
    assert statuses(series(**dict(GOOD, fcf=[5, None, -7, 8])))["cash"] == "unclear"    # -7, 8 and one unknown: could be 2
    assert statuses(series(**dict(GOOD, fcf=[5, None, -7, -8])))["cash"] == "fail"       # at most 1 positive even if the unknown is
    assert statuses(series(**dict(GOOD, fcf=[None] * 4)))["cash"] == "unclear"


def test_debt_passes_when_there_is_none_or_cash_is_larger_or_it_is_paid_in_under_four_years():
    assert statuses(series(**dict(GOOD, debt=[0] * 4)))["debt"] == "pass"
    assert statuses(series(**dict(GOOD, debt=[50] * 4, liquid=[60] * 4)))["debt"] == "pass"
    owed = dict(GOOD, debt=[100] * 4, liquid=[20] * 4, fcf=[25] * 4)                 # 80 / 25 = 3.2 years
    assert statuses(series(**owed))["debt"] == "pass"
    assert statuses(series(**dict(owed, fcf=[16] * 4)))["debt"] == "fail"            # 80 / 16 = 5 years
    assert statuses(series(**dict(owed, fcf=[-3] * 4)))["debt"] == "fail"
    assert statuses(series(**dict(owed, debt=[None] * 4)))["debt"] == "unclear"
    assert statuses(series(**dict(owed, liquid=[None] * 4)))["debt"] == "unclear"


def test_a_share_count_that_jumps_like_a_split_is_not_dilution():
    assert statuses(series(**dict(GOOD, shares=[100, 100, 100, 400])))["dilution"] == "unclear"
    assert statuses(series(**dict(GOOD, shares=[400, 100, 100, 100])))["dilution"] == "unclear"      # a reverse split
    assert statuses(series(**dict(GOOD, shares=[100, 103, 106, 109])))["dilution"] == "pass"          # +9%
    assert statuses(series(**dict(GOOD, shares=[100, 103, 106, 111])))["dilution"] == "fail"          # +11%


def test_fewer_than_four_years_means_the_three_year_checks_are_unclear():
    s = {"ends": ENDS[:3], "revenue": dict(zip(ENDS, GOOD["revenue"][:3])), "operating": {ENDS[2]: 1}, "fcf": {}, "shares": {},
         "debt": {}, "liquid": {}}
    assert statuses(s)["shrink"] == "unclear" and statuses(s)["dilution"] == "unclear" and statuses(s)["profit"] == "pass"


@pytest.mark.parametrize("computed, passed, points", [
    (5, 0, 0), (5, 2, 0), (5, 3, 1), (5, 4, 1), (5, 5, 2),
    (4, 4, 2), (4, 3, 1), (4, 2, 0), (3, 3, 2), (3, 2, 1), (3, 1, 0),
    (2, 2, 1), (1, 0, 1), (0, 0, 1),                                  # fewer than 3 computed: unclear = 1
])
def test_the_points_arithmetic(computed, passed, points):
    checks = [{"name": "x", "status": "pass"}] * passed + [{"name": "x", "status": "fail"}] * (computed - passed)
    checks += [{"name": "x", "status": "unclear"}] * (5 - computed)
    assert health.points_for(checks) == points


def test_the_reason_names_what_failed_and_what_was_not_computed():
    s = series(**dict(GOOD, operating=[10, 11, 12, -1], shares=[None] * 4))
    text = health.quick_health(type("R", (), {"series": s, "out_of_scope": None})()).reason
    assert "3 of 4 computed checks passed" in text and "failed: Profit (operating profit -0.00 bn in 2025)" in text
    assert "not computed: Dilution" in text
    unclear = health.quick_health(type("R", (), {"series": series(), "out_of_scope": None})()).reason
    assert unclear.startswith("unclear — only 0 of 5 checks could be computed")


# the same free-cash numbers as agent 3: the sample companies' grades line up with their quick-health points
SPLITS = {"NVDA": [("2021-07-20", 4.0), ("2024-06-10", 10.0)]}


def real(ticker):
    r = analyse(Facts(sec_facts(ticker), sec_submissions(ticker), quarters=False), ticker, Market(splits=SPLITS.get(ticker, [])))
    return health.quick_health(r)


@pytest.mark.parametrize("ticker, points", [("NVDA", 2), ("NVO", 2), ("KO", 1), ("NKE", 1), ("INTC", 0), ("DOW", 0), ("SNAP", 0)])
def test_sample_companies_on_saved_sec_data(ticker, points):
    assert real(ticker).points == points


def test_a_bank_is_unclear_because_it_is_out_of_scope():
    h = real("JPM")
    assert h.points == 1 and "out of scope for the analysis: bank" in h.reason


def test_the_numbers_are_the_same_as_agent_3s_free_cash():
    r = analyse(Facts(sec_facts("NVDA"), sec_submissions("NVDA"), quarters=False), "NVDA", Market(splits=SPLITS["NVDA"]))
    last = r.series["ends"][-1]
    assert r.series["fcf"][last] == pytest.approx(r.free_cash["value"])


# --- sector tailwind -----------------------------------------------------------------------------------------------------------

def add_prices(db, symbol, weekly_values, end=date(2026, 10, 9)):
    """One Friday close per week, oldest first, ending at `end` (a Friday)."""
    n = len(weekly_values)
    for i, value in enumerate(weekly_values):
        day = (end - timedelta(weeks=n - 1 - i)).isoformat()
        db.execute("INSERT INTO prices (symbol, date, close, adj_close, currency, source, created_at) VALUES (?, ?, ?, ?, 'USD', 'yahoo', 'x')",
                   (symbol, day, value, value))
    db.commit()


def rising(n=50, start=100.0, step=1.0):
    return [start + i * step for i in range(n)]


def test_the_weekly_close_is_the_last_stored_day_of_each_week(db):
    for day, close in (("2026-10-05", 1), ("2026-10-07", 2), ("2026-10-09", 3), ("2026-10-12", 4)):
        db.execute("INSERT INTO prices (symbol, date, close, adj_close, created_at) VALUES ('XLE', ?, ?, ?, 'x')", (day, close, close))
    assert tailwind.weekly_closes(db, "XLE") == [("2026-10-09", 3), ("2026-10-12", 4)]


def test_both_items_pass_when_the_fund_is_above_its_average_and_beat_the_market(db):
    add_prices(db, "XLE", rising(50, 100, 2.0))
    add_prices(db, "SPY", [400.0] * 50)
    t = tailwind.evaluate(db, "Energy", [])
    assert t.points == 2 and "A: XLE" in t.reason and "no linked commodity with a price" in t.reason


def test_a_fund_below_its_average_scores_nothing_on_item_a(db):
    add_prices(db, "XLE", list(reversed(rising(50, 100, 2.0))))
    add_prices(db, "SPY", [400.0] * 50)
    t = tailwind.evaluate(db, "Energy", [])
    assert t.detail["item_a"] is False and t.detail["item_b"] is False and t.points == 0


def test_not_enough_history_counts_as_not_met_and_says_so(db):
    add_prices(db, "XLE", rising(20))
    add_prices(db, "SPY", rising(20))
    t = tailwind.evaluate(db, "Energy", [])
    assert t.points == 0 and "only 20 weeks of prices, 40 needed" in t.reason and "(counted as not met)" in t.reason


def test_an_unknown_sector_has_no_fund(db):
    t = tailwind.evaluate(db, None, [])
    assert t.points == 0 and "sector is unknown" in t.reason


def test_a_producer_likes_a_commodity_above_its_average_and_a_user_likes_it_below(db):
    add_prices(db, "XLB", rising(50))
    add_prices(db, "SPY", [400.0] * 50)
    add_prices(db, "HG=F", rising(50, 3.0, 0.02))                       # copper above its average
    producer = tailwind.evaluate(db, "Materials", [("copper", "producer")])
    user = tailwind.evaluate(db, "Materials", [("copper", "user")])
    assert producer.detail["item_b"] is True and "favorable" in producer.reason and producer.points == 2
    assert user.detail["item_b"] is False and "not favorable" in user.reason and user.points == 1


def test_several_commodities_are_decided_by_the_majority(db):
    add_prices(db, "XLB", rising(50))
    add_prices(db, "HG=F", rising(50, 3.0, 0.02))
    add_prices(db, "GC=F", list(reversed(rising(50, 3.0, 0.02))))
    t = tailwind.evaluate(db, "Materials", [("copper", "producer"), ("gold", "producer")])
    assert t.detail["item_b"] is False                                    # one for, one against: a tie is not a pass


def test_a_commodity_without_a_symbol_or_a_price_falls_back_to_the_market_comparison(db):
    add_prices(db, "XLB", rising(50, 100, 2.0))
    add_prices(db, "SPY", [400.0] * 50)
    t = tailwind.evaluate(db, "Materials", [("unobtainium", "producer"), ("copper", "producer")])
    assert "no linked commodity with a price" in t.reason and t.detail["item_b"] is True


def test_symbols_needed_lists_spy_the_fund_and_the_commodities():
    assert tailwind.symbols_needed("Energy", [("crude oil", "producer"), ("nothing", "user")]) == ["SPY", "XLE", "CL=F"]
    assert tailwind.symbols_needed(None, []) == ["SPY"]


def test_the_price_job_also_fetches_the_commodities_linked_to_stocks_with_a_card(db):
    from shared import prices
    db.execute("INSERT INTO stocks (id, ticker, status, created_at) VALUES (1, 'XOM', 'candidate', 'x'), (2, 'OLD', 'archived', 'x')")
    db.execute("INSERT INTO commodity_links (stock_id, commodity, role, created_at) VALUES (1, 'Crude Oil', 'producer', 'x'), (2, 'copper', 'user', 'x')")
    db.commit()
    symbols = prices.job_symbols(db)
    assert "CL=F" in symbols and "HG=F" not in symbols and len(symbols) == len(set(symbols))


# --- score ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("pos, neg, points", [(0, 0, 1), (2, 1, 1), (1, 2, 1), (3, 1, 2), (4, 0, 2), (0, 2, 0), (1, 4, 0)])
def test_tone_points(pos, neg, points):
    assert score.tone_points(pos, neg) == points


@pytest.mark.parametrize("serious, positive, unclear, points", [
    (True, True, False, 0), (True, False, False, 0), (False, True, False, 2), (False, False, False, 1), (False, True, True, 1)])
def test_news_points(serious, positive, unclear, points):
    assert score.news_points(serious, positive, unclear) == points


def test_total_needs_every_criterion():
    assert score.total(dict(mentions=2, tone=1, sector_tailwind=0, news_flow=2, quick_health=1)) == 6
    with pytest.raises(ValueError, match="news_flow"):
        score.total(dict(mentions=2, tone=1, sector_tailwind=0, quick_health=1))
