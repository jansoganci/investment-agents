"""Agent 3's AI parts with a fake AI: quotes are checked by code, the thesis, the audits, the sell suggestion."""

import json
import random

import pytest

from agents.analysis import ai as parts
from agents.analysis import sell
from shared import ai, auditor
from shared.ai.fake import FakeAI
from shared.auditor import testset
from tests.analysis.test_measures import run as analyse_run
from tests.fixtures.loader import filing_text

pytestmark = pytest.mark.usefixtures("db")

TEXT = filing_text("NVDA")["text"]
NOTES = "As of July 26, 2026, we had $33.5 billion aggregate principal amount of senior notes outstanding."
R = analyse_run("NVDA", quarters=True)
THESIS = {"reasons": ["It sells the chips AI runs on.", "Cash flow pays for the growth."],
          "breaks": ["Revenue growth turns negative.", "Debt rises above free cash flow for years.", "A major customer leaves."]}


def ctx(**kw):
    base = dict(ticker="NVDA", company="Nvidia", rng=random.Random(1))
    base.update(kw)
    return parts.Context(**base)


def items_in(prompt):
    """The ITEMS list (strong calls) or {"items": [...]} (auditor calls) the code put in the prompt."""
    head = prompt.split("\n\nFILING ")[0]  # the items come before the filing rows and excerpts
    if '"items"' in head.split("\n")[0] + head[:20]:
        return json.loads(head[head.index("{"):])["items"]
    return json.loads(head[head.index("ITEMS:\n") + 7:])


def handler(why_quote=NOTES, verdict="pass", thesis=THESIS, check=None):
    def h(job, system, prompt):
        if job == "auditor":
            return [{"id": i["id"], "verdict": verdict if not isinstance(verdict, dict) else verdict.get(i["id"], "pass"),
                     "quote": NOTES, "reason": "ok"} for i in items_in(prompt)]
        if system.startswith("You help a long-term"):
            return [{"id": i["id"], "answer": f"because of {i['id']}", "quote": why_quote, "kind": "company_specific"}
                    for i in items_in(prompt)]
        if system.startswith("You write the investment thesis"):
            return thesis
        if system.startswith("You check whether"):
            return check or {"status": "intact", "point": None, "reason": "nothing changed", "quote": ""}
        raise AssertionError(system[:40])
    return h


def test_why_answers_are_shown_only_with_a_quote_found_in_the_filing(monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    why = parts.ask_why(R, TEXT, ctx())
    assert why and all(w.verified and w.kind == "company_specific" and w.quote == NOTES for w in why)
    FakeAI(handler(why_quote="NVIDIA settled a lawsuit for 4 billion dollars in July 2026.")).install(monkeypatch)
    why = parts.ask_why(R, TEXT, ctx())
    assert not any(w.verified for w in why) and all(w.answer.startswith("no verified quote") for w in why)
    assert all(w.quote == "" and w.kind is None for w in why)


def test_every_flag_and_every_weak_measure_gets_a_why_item():
    ids = [i["id"] for i in parts.why_items(R)]
    assert ids == [f"U{n}" for n in range(1, len(R.flags) + 1)]  # NVDA has flags and no weak measure
    weak = analyse_run("RIVN")
    assert any(i["id"].startswith("M:") for i in parts.why_items(weak))


def test_the_first_thesis_has_at_most_3_reasons_and_exactly_3_breaks(monkeypatch):
    fake = FakeAI(lambda *a: {"reasons": ["a"], "breaks": ["one", "two"]}).install(monkeypatch)
    answers = iter([{"reasons": ["a"], "breaks": ["one", "two"]}, THESIS])
    fake.handler = lambda *a: next(answers)
    t = parts.first_thesis(R, [], TEXT, ctx())
    assert t == THESIS and len(fake.calls) == 2  # a bad shape is told and tried once more
    assert "could not be used" in fake.calls[1][2]
    FakeAI(lambda *a: {"reasons": ["a"], "breaks": ["one"]}).install(monkeypatch)
    with pytest.raises(parts.AIFormatError):
        parts.first_thesis(R, [], TEXT, ctx())


def test_the_thesis_text_is_plain_and_numbered():
    txt = parts.thesis_text(THESIS)
    assert txt.startswith("Why it is owned:\n1. It sells") and "What would break it:\n1. Revenue" in txt
    assert txt.endswith("3. A major customer leaves.")


def test_a_thesis_is_never_broken_without_a_verified_quote(monkeypatch):
    broken = {"status": "broken", "point": 2, "reason": "debt exploded", "quote": "NVIDIA borrowed 90 billion dollars more."}
    FakeAI(handler(check=broken)).install(monkeypatch)
    c = parts.thesis_check(R, [], TEXT, ctx(previous_thesis=parts.thesis_text(THESIS)))
    assert c["status"] == "watch" and "no verified quote" in c["reason"] and c["quote"] == ""
    broken["quote"] = NOTES
    c = parts.thesis_check(R, [], TEXT, ctx(previous_thesis=parts.thesis_text(THESIS)))
    assert (c["status"], c["point"], c["quote"]) == ("broken", 2, NOTES)


def test_the_drop_alert_check_with_news_only_says_watch(monkeypatch):
    FakeAI(lambda *a: {"status": "broken", "reason": "the news says so", "quote": "Reuters: the CEO resigned amid probe."}).install(monkeypatch)
    out = parts.drop_alert_check(R, TEXT, ctx(previous_thesis="t", news=["Reuters: the CEO resigned amid probe."]))
    assert out["status"] == "watch" and out["news_used"] and out["quote"] == ""
    FakeAI(lambda *a: {"status": "broken", "reason": "debt", "quote": NOTES}).install(monkeypatch)
    assert parts.drop_alert_check(R, TEXT, ctx(previous_thesis="t"))["status"] == "broken"  # evidence in the filing


# --- run_ai ---------------------------------------------------------------------------------------------------------------

def test_a_first_card_gets_the_thesis_and_both_audits(monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    part = parts.run_ai(R, TEXT, ctx())
    assert part.thesis == THESIS and part.thesis_status == "intact" and part.check is None
    assert sorted(a.audit for a in part.audits) == ["figure", "reading"] and not part.unverified and part.sell is None


def test_an_audit_fail_marks_the_entry_unverified_and_says_which_figure(monkeypatch):
    FakeAI(handler(verdict={"liquid": "fail"})).install(monkeypatch)
    part = parts.run_ai(R, TEXT, ctx())
    assert part.unverified and any("figure: liquid" in line for line in part.lines())


def test_a_routine_update_is_audited_one_time_in_five():
    ko = analyse_run("KO", quarters=True)
    c = lambda s: parts.Context(ticker="KO", company="KO", first=False, grades=["solid"], rng=random.Random(s))
    ran = [bool(parts.should_audit(c(s), ko, "solid", False)) for s in range(500)]
    assert 0.12 < sum(ran) / 500 < 0.28  # about 1 in 5


def test_the_audit_rules():
    rng = random.Random(7)
    base = dict(ticker="X", company="X", rng=rng)
    no_dc = analyse_run("PLTR", quarters=True)  # no data_check flag
    assert parts.should_audit(parts.Context(first=True, **base), no_dc, None, False) >= {"figure", "reading"}
    assert parts.should_audit(parts.Context(first=False, **base), no_dc, "mid", True) >= {"figure"}  # an open data check
    solid_weak = analyse_run("RIVN")  # grade weak
    assert parts.should_audit(parts.Context(first=False, **base), solid_weak, "solid", False) == {"figure", "reading"}


def test_when_the_ai_fails_the_numbers_still_stand(monkeypatch):
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    fake.fail = {"anthropic", "openrouter", "openai", "deepseek"}
    part = parts.run_ai(R, TEXT, ctx())
    assert part.thesis is None and part.why == [] and any("could not be written" in n for n in part.notes)


def test_an_out_of_scope_stock_gets_no_ai(monkeypatch):
    fake = FakeAI(handler()).install(monkeypatch)
    part = parts.run_ai(analyse_run("JPM"), TEXT, ctx())
    assert fake.calls == [] and part.thesis is None


# --- selling --------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("held,grade,grades,thesis,expected", [
    (True, "weak", ["mid"], "intact", "grade_weak"),
    (True, "weak", ["weak"], "intact", None),                     # already weak: it was said then
    (True, "mid", ["solid", "mid"], "intact", "mid_after_solid"),
    (True, "mid", ["solid"], "intact", None),                      # one mid is a "check now"
    (True, "mid", ["mid", "mid"], "intact", None),                 # not after a solid
    (True, "solid", ["solid"], "broken", "thesis_broken"),
    (True, "solid", ["solid"], "watch", None),
    (False, "weak", ["solid"], "broken", None),                    # not held: no sell suggestion
])
def test_sell_triggers(held, grade, grades, thesis, expected):
    assert sell.trigger(held, grade, grades, thesis) == expected


def test_a_sell_suggestion_with_clean_audits_is_sent_with_its_evidence(monkeypatch):
    broken = {"status": "broken", "point": 1, "reason": "growth turned", "quote": NOTES}
    FakeAI(handler(check=broken)).install(monkeypatch)
    part = parts.run_ai(R, TEXT, ctx(first=False, in_portfolio=True, grades=["solid"], previous_thesis=parts.thesis_text(THESIS)))
    assert part.sell["trigger"] == "thesis_broken" and part.sell["status"] == "sent"
    assert "CONSIDER SELLING · NVDA" in part.sell["text"] and "The decision is yours." in part.sell["text"]
    assert "Check the figure before acting" in part.sell["text"]  # NVDA has an open data_check flag
    assert sorted(a.audit for a in part.audits) == ["figure", "reading", "sell"]  # everything behind it is checked


def test_a_failed_audit_holds_the_sell_suggestion_back(monkeypatch):
    broken = {"status": "broken", "point": 1, "reason": "growth turned", "quote": NOTES}
    FakeAI(handler(check=broken, verdict={"debt": "fail"})).install(monkeypatch)
    part = parts.run_ai(R, TEXT, ctx(first=False, in_portfolio=True, grades=["solid"], previous_thesis=parts.thesis_text(THESIS)))
    assert part.sell["status"] == "held" and part.sell["text"].startswith("SELL SUGGESTION HELD · NVDA")
    assert "figure: debt" in part.sell["text"] and "CONSIDER SELLING" not in part.sell["text"]


def test_a_sell_suggestion_whose_audit_cannot_run_is_held(monkeypatch):
    broken = {"status": "broken", "point": 1, "reason": "growth turned", "quote": NOTES}
    h = handler(check=broken)
    FakeAI(lambda job, s, p: "I cannot help with that" if job == "auditor" else h(job, s, p)).install(monkeypatch)  # no verdict
    part = parts.run_ai(R, TEXT, ctx(first=False, in_portfolio=True, grades=["solid"], previous_thesis=parts.thesis_text(THESIS)))
    assert part.sell["status"] == "held" and "could not run" in part.sell["text"]


BROKEN = {"status": "broken", "point": 1, "reason": "growth turned", "quote": NOTES}
HELD_CTX = dict(first=False, in_portfolio=True, grades=["solid"], filing="0001045810-26-000075")


def held_ctx():
    return ctx(previous_thesis=parts.thesis_text(THESIS), **HELD_CTX)


def test_an_auditor_that_confirms_nothing_holds_the_sell_suggestion(monkeypatch):
    FakeAI(handler(check=BROKEN, verdict="not_found")).install(monkeypatch)
    part = parts.run_ai(R, TEXT, held_ctx())
    assert part.sell["status"] == "held" and "could not confirm the evidence" in part.sell["text"]
    assert "CONSIDER SELLING" not in part.sell["text"] and not part.unverified  # not confirmed is a note, not a mark
    assert "Source: filing 0001045810-26-000075" in part.sell["text"]


def test_an_auditor_that_answers_with_an_empty_list_holds_it_too(monkeypatch):
    def h(job, system, prompt):
        return [] if job == "auditor" else handler(check=BROKEN)(job, system, prompt)
    FakeAI(h).install(monkeypatch)
    assert parts.run_ai(R, TEXT, held_ctx()).sell["status"] == "held"


def test_one_unconfirmed_audit_among_passes_still_holds_it(monkeypatch):
    FakeAI(handler(check=BROKEN, verdict={"debt": "not_found"})).install(monkeypatch)
    part = parts.run_ai(R, TEXT, held_ctx())
    assert part.sell["status"] == "held" and "figure (1 of " in part.sell["text"]


def test_only_all_pass_sends_it(monkeypatch):
    FakeAI(handler(check=BROKEN)).install(monkeypatch)
    part = parts.run_ai(R, TEXT, held_ctx())
    assert part.sell["status"] == "sent" and parts.hold_reason({}) == ("not_run", "the figure audit did not run")


def test_the_hold_reason_names_a_disagreement_a_missing_audit_and_an_error():
    ok = lambda kind, result="pass", error=None, items=(): type("A", (), {
        "audit": kind, "result": result, "error": error, "items": list(items),
        "failed": lambda self: [i for i in self.items if i["verdict"] == "fail"]})()
    bad = {"id": "debt", "verdict": "fail", "quote": "", "reason": ""}
    assert parts.hold_reason({"figure": ok("figure"), "sell": ok("sell")}) is None
    assert parts.hold_reason({"figure": ok("figure", "fail", items=[bad]), "sell": ok("sell")}) == ("disagrees", "figure: debt")
    assert parts.hold_reason({"sell": ok("sell")}) == ("not_run", "the figure audit did not run")
    assert parts.hold_reason({"figure": ok("figure", "not_found", error="no model answered"), "sell": ok("sell")})[0] == "not_run"
    assert parts.hold_reason({"figure": ok("figure"), "sell": ok("sell"), "reading": ok("reading", "not_found", items=[{"verdict": "not_found"}])})[0] == "unconfirmed"


# GE's own statement rows (10-Q to 2026-06-30). By their words none reached the 12,000-character excerpts (roadmap
# rule 40); found by our figures' values, all of them do (rule 41). Net income is the Company's share (`NetIncomeLoss`,
# 4,273), not the total with noncontrolling interests (4,276).
GE_ROWS = {
    "revenue": "Total revenue $ 13,349 $ 11,023 $ 25,741 $ 20,957",
    "net income": "Net income (loss) attributable to the Company 2,370 2,028 4,273 4,006",
    "Cash from (used for) operating activities": "Cash from (used for) operating activities 5,018 3,755",
    "capex": "Add: gross additions to property, plant and equipment and internal-use software (666) (535)",
    "diluted shares": "1,047 1,040 1,071 1,063",
    "short-term borrowings": "Short-term borrowings (Note 10) $ 2,000 $ 1,686",
    "long-term borrowings": "Long-term borrowings (Note 10) 17,157 18,808",
    "cash": "Cash, cash equivalents and restricted cash $ 9,345 $ 12,392",
}


def test_a_mark_without_a_value_is_not_shown_as_not_computed():
    # GE: debt is good and decisive but has no single value; interest cover has neither
    block = parts._facts_block(analyse_run("GE", quarters=True))
    assert "debt: good, decisive" in block and "debt: None" not in block
    assert "interest_cover: not_computed" in block
    # each measure says what it means: the model read capital_return as cash paid to shareholders (acceptance test, NVDA / KO)
    assert "NOT cash paid to shareholders" in next(l for l in block.splitlines() if l.startswith("capital_return:"))
    assert all(" — " in l for l in block.splitlines())
    assert "NEW NUMBERS are current: where the thesis states an older figure or says a figure could not be computed, use NEW NUMBERS." in parts.CHECK_SYSTEM


def _figure_prompt(ticker, monkeypatch):
    """The prompt the figure audit sends for this company's real 10-Q (a fake auditor that answers nothing)."""
    fake = FakeAI(lambda *a: []).install(monkeypatch)
    items = parts.figure_items(analyse_run(ticker, quarters=True))
    auditor.audit("figure", items, filing_text(ticker)["text"])
    return items, fake.calls[0][2]


def test_ge_statement_rows_reach_the_figure_audit(monkeypatch):
    # rule 40 measured that GE's rows never reached the excerpts by their words; rule 41 finds them by value
    text = filing_text("GE")["text"]
    assert filing_text("GE")["accession"] == "0000040545-26-000049"
    assert all(row in text for row in GE_ROWS.values())
    items, prompt = _figure_prompt("GE", monkeypatch)
    rows = prompt.split("FILING ROWS THAT PRINT OUR FIGURES:\n")[1].split("\n\nFILING EXCERPTS:")[0]
    # short-term borrowings: the balance sheet's row or the borrowings note's total — the same 2,000 on the same date
    found = {name: row in rows for name, row in GE_ROWS.items()}
    found["short-term borrowings"] |= "Total short-term borrowings $ 2,000 $ 1,686" in rows
    assert found == {name: True for name in GE_ROWS}
    assert "Six months ended June 30" in rows and "June 30, 2026 December 31, 2025" in rows  # the columns are named
    assert len(prompt.split("\n\nFILING ROWS")[1]) <= 12000 + 200  # rows and excerpts share the old limit
    op_cash = next(i for i in items if i["id"] == "op_cash")
    assert op_cash["values"] == [5_018_000_000, 3_755_000_000]  # a 4-quarter total is looked up by its two parts
    assert '"values"' not in prompt.split("\n\nFILING ")[0]  # the numbers we search by are not sent as items


def test_nvidia_statement_rows_reach_the_figure_audit(monkeypatch):
    _, prompt = _figure_prompt("NVDA", monkeypatch)
    rows = prompt.split("FILING ROWS THAT PRINT OUR FIGURES:\n")[1].split("\n\nFILING EXCERPTS:")[0]
    for row in ("Net cash provided by operating activities 74,421 42,779", "Long-term debt 32,366 7,469",
                "Short-term debt 1,000 999", "Marketable debt securities 34,143 39,065", "Diluted 24,285 24,532 24,338 24,571"):
        assert row in rows


def test_the_figure_audit_sees_the_balance_sheet_row_of_debt(monkeypatch):
    fake = FakeAI(handler()).install(monkeypatch)
    parts.run_ai(R, TEXT, ctx())
    figure_prompt = next(p for job, s, p in fake.calls if job == "auditor" and "\"id\": \"debt\"" in p.split("\n\nFILING ")[0])
    assert "Long-term debt 32,366 7,469" in figure_prompt  # a 27-character table row used to be dropped


def test_the_auditor_runs_sonnet_first_like_the_writer(monkeypatch):
    # my decision (2026-10-09): every AI part, the auditor included, is Sonnet 5.5 high first; the family rule is dropped
    fake = FakeAI(handler(check=BROKEN)).install(monkeypatch)
    part = parts.run_ai(R, TEXT, held_ctx())
    auditors = {m for (job, _s, _p), m in zip(fake.calls, fake.models) if job == "auditor"}
    assert auditors == {"anthropic:claude-sonnet-5-5"} and part.sell["status"] == "sent"
    fake.fail = {"anthropic"}  # Sonnet down: writer and auditor both fall back to DeepSeek V4 Pro, and that is allowed
    fake.calls.clear(), fake.models.clear()
    part = parts.run_ai(R, TEXT, held_ctx())
    assert set(fake.models) == {"deepseek:deepseek-v4-pro"} and part.sell["status"] == "sent"


def test_a_borderline_flag_gets_no_why_question():
    import copy
    r = copy.copy(R)
    r.flags = R.flags + [{"flag": "borderline", "detail": "capital_return"}]
    r.codes = [f"U{i}" for i in range(1, len(r.flags) + 1)]
    ids = [i["id"] for i in parts.why_items(r)]
    assert f"U{len(r.flags)}" not in ids and len(ids) == len(R.flags)


def test_a_figure_claim_says_its_period_and_a_4_quarter_total_gives_its_parts():
    # GE, 2026-10-06: a correct 4-quarter operating cash (9.8 bn) was failed against the 10-Q's 6-month row (5.0 bn)
    items = {i["id"]: i for i in parts.figure_items(R)}  # NVDA with the last 4 quarters
    v = R.figures["op_cash"][R.last]
    assert f"period end {R.last} (TTM)" in items["op_cash"]["claim"]
    note = items["op_cash"]["note"]
    assert f"{v.ttm['annual']:,.0f} (in the 10-K, not in this filing)" in note and "never fail" in note
    assert f"this year to date {v.ttm['ytd']:,.0f}" in note and f"a year before {v.ttm['ytd_previous_year']:,.0f}" in note
    assert v.ttm["annual"] + v.ttm["ytd"] - v.ttm["ytd_previous_year"] == pytest.approx(v.value)
    assert f"period end {R.last} (Q)" in items["shares"]["claim"]  # the latest quarter's average, not a sum
    assert f"period end {R.last} (BS)" in items["debt"]["claim"]
    annual = {i["id"]: i for i in parts.figure_items(analyse_run("NVDA"))}
    assert "(FY)" in annual["op_cash"]["claim"] and "note" not in annual["op_cash"]
    for code in ("`(FY)`", "`(Q)`", "`(BS)`", "`(TTM)`"):  # every code is explained to the auditor
        assert code in auditor.card_text("figure")


def test_liquid_assets_without_a_line_of_their_own_are_never_failed():
    # GE, 2026-10-06: ~1.0 bn of time deposits sit inside "other current assets"; liquid assets count separate lines only
    note = {i["id"]: i for i in parts.figure_items(R)}["liquid"]["note"]
    assert "no line of its own" in note and "time deposits inside other current assets" in note and "never fail" in note
    assert "time deposits over 3 months" in auditor.card_text("figure")
    assert any("time deposits" in c[1] and c[4] == "pass" for c in testset.CASES)


def test_restricted_cash_in_one_line_with_cash_is_never_failed():
    # GE, SBUX: the code takes CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents; restricted cash counts as liquid
    note = {i["id"]: i for i in parts.figure_items(R)}["liquid"]["note"]
    assert "restricted cash counts" in note and "as one line" in note
    card = auditor.card_text("figure")
    assert "Restricted cash counts" in card and "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents" in card
    assert any("restricted cash" in c[1] and c[4] == "pass" for c in testset.CASES)


def test_a_stale_data_warning_is_not_asked_about():
    import copy
    r = copy.copy(R)
    r.flags = R.flags + [{"flag": "stale_data", "detail": "figures end 2026-04-03; the 10-Q to 2026-07-03 is not in SEC's data yet"}]
    r.codes = [f"U{i}" for i in range(1, len(r.flags) + 1)]
    assert f"U{len(r.flags)}" not in [i["id"] for i in parts.why_items(r)]


def test_a_why_answer_may_quote_two_sentences_and_the_writer_and_auditor_know_our_figures_are_given(monkeypatch):
    two = NOTES + " | Long-term debt 32,366 7,469"  # roadmap rule 47 (acceptance test 2026-10-09)
    FakeAI(handler(why_quote=two)).install(monkeypatch)
    assert all(w.verified for w in parts.ask_why(R, TEXT, ctx()))
    FakeAI(handler(why_quote=NOTES + " | Long-term debt 99,999 1,111")).install(monkeypatch)
    assert not any(w.verified for w in parts.ask_why(R, TEXT, ctx()))  # one invented sentence spoils it
    assert "which you may repeat" in parts.WHY_SYSTEM
    from shared import auditor
    assert "they are checked elsewhere" in auditor.card_text("reading")
