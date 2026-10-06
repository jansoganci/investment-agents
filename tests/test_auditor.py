"""shared/auditor: the engine, the code checks that come first, and the rule cards' known traps."""

import json

import pytest

from shared import auditor
from shared.ai.fake import FakeAI
from tests.fixtures.loader import filing_text

pytestmark = pytest.mark.usefixtures("db")  # every audit is an AI call: its cost is logged in the database

TEXT = filing_text("NVDA")["text"]
NOTES = "As of July 26, 2026, we had $33.5 billion aggregate principal amount of senior notes outstanding."
ITEMS = [{"id": "debt", "claim": "debt 33.4 bn: LongTermDebtNoncurrent + LongTermDebtCurrent, period 2026-07-26",
          "terms": ["senior notes"]},
         {"id": "cash", "claim": "cash 22.443 bn: CashAndCashEquivalentsAtCarryingValue", "terms": ["cash and cash equivalents"]}]


def answer(verdicts, quote=NOTES):
    return [{"id": i, "verdict": v, "quote": quote, "reason": "matches"} for i, v in verdicts.items()]


def test_a_pass_needs_a_quote_that_is_really_in_the_filing(monkeypatch):
    fake = FakeAI(lambda *a: answer({"debt": "pass", "cash": "pass"})).install(monkeypatch)
    res = auditor.audit("figure", ITEMS, TEXT)
    assert res.result == "pass" and [i["verdict"] for i in res.items] == ["pass", "pass"]
    job, system, prompt = fake.calls[0]
    assert job == "auditor" and "Rule card 1" in system and "Boeing" in system  # the card is the AI's instruction
    assert "aggregate principal amount of senior notes" in prompt  # the excerpts hold the evidence


def test_an_invented_quote_is_not_believed_whatever_the_verdict(monkeypatch):
    FakeAI(lambda *a: answer({"debt": "pass", "cash": "fail"}, quote="NVIDIA disclosed a $90 billion write-off.")).install(monkeypatch)
    res = auditor.audit("figure", ITEMS, TEXT)
    assert [i["verdict"] for i in res.items] == ["not_found", "not_found"]  # neither the pass nor the fail counts
    assert res.result == "not_found" and "no verified quote" in res.items[0]["reason"]


def test_one_fail_with_a_real_quote_fails_the_audit(monkeypatch):
    FakeAI(lambda *a: answer({"debt": "fail", "cash": "pass"})).install(monkeypatch)
    res = auditor.audit("figure", ITEMS, TEXT)
    assert res.result == "fail" and [i["id"] for i in res.failed()] == ["debt"]


def test_an_item_the_model_forgot_is_not_found(monkeypatch):
    FakeAI(lambda *a: answer({"debt": "pass"})).install(monkeypatch)
    res = auditor.audit("figure", ITEMS, TEXT)
    assert [i["verdict"] for i in res.items] == ["pass", "not_found"] and res.result == "not_found"  # 1 of 2 passes: under 70%


def test_json_in_a_code_fence_is_tolerated(monkeypatch):
    FakeAI(lambda *a: "```json\n" + json.dumps(answer({"debt": "pass", "cash": "pass"})) + "\n```").install(monkeypatch)
    assert auditor.audit("figure", ITEMS, TEXT).result == "pass"


def test_when_the_auditor_cannot_answer_there_is_no_verdict_and_no_crash(monkeypatch):
    fake = FakeAI(lambda *a: "I cannot help with that").install(monkeypatch)
    res = auditor.audit("reading", ITEMS, TEXT)
    assert res.result == "not_found" and "no JSON list" in res.error
    fake2 = FakeAI(lambda *a: "x").install(monkeypatch)
    fake2.fail = {"deepseek", "openrouter", "openai"}
    assert "no model answered" in auditor.audit("sell", ITEMS, TEXT).error


def test_save_writes_an_audits_row(db, monkeypatch):
    FakeAI(lambda *a: answer({"debt": "fail", "cash": "pass"})).install(monkeypatch)
    res = auditor.audit("figure", ITEMS, TEXT)
    db.execute("INSERT INTO stocks (cik, ticker, company, status, created_at) VALUES ('1', 'NVDA', 'Nvidia', 'candidate', 'x')")
    auditor.save(db, 1, res, "0001045810-26-000075")
    row = db.execute("SELECT stock_id, audit, result, filing, model FROM audits").fetchone()
    assert row[:4] == (1, "figure", "fail", "0001045810-26-000075") and row[4] == "deepseek-v4-pro"
    assert json.loads(db.execute("SELECT detail FROM audits").fetchone()[0])["items"][0]["id"] == "debt"


def test_the_rule_cards_carry_their_known_traps():
    assert all(w in auditor.card_text("figure") for w in ("Coca-Cola", "Boeing", "Pfizer 2020", "Nvidia"))
    assert "Cloudflare (NET)" in auditor.card_text("reading")
    assert "single bad quarter" in auditor.card_text("sell")


def test_no_threshold_every_item_must_pass(monkeypatch):
    items = [{"id": f"i{n}", "claim": f"figure {n} senior notes", "terms": ["senior notes"]} for n in range(10)]
    verdicts = [{"id": f"i{n}", "verdict": "pass" if n else "not_found", "quote": NOTES, "reason": "ok"} for n in range(10)]
    FakeAI(lambda *a: verdicts).install(monkeypatch)
    assert auditor.audit("figure", items, TEXT).result == "not_found"  # 9 of 10 is not a pass
    assert auditor.overall([]) == "not_found"
    assert auditor.overall([{"verdict": "pass"}, {"verdict": "fail"}]) == "fail"


def test_a_figure_or_sell_quote_without_a_number_proves_nothing(monkeypatch):
    plain = "As each series of senior notes matures, unless redeemed or repurchased, we must either repay or refinance the notes."
    assert plain in TEXT
    FakeAI(lambda *a: answer({"debt": "pass", "cash": "pass"}, quote=plain)).install(monkeypatch)
    assert auditor.audit("figure", ITEMS, TEXT).result == "not_found"
    assert auditor.audit("reading", ITEMS, TEXT).result == "pass"  # a reading quote may be plain prose


def test_a_figure_on_several_rows_may_be_quoted_as_several_rows(monkeypatch):
    rows = "Long-term debt 32,366 7,469 | As of July 26, 2026, we had $33.5 billion aggregate principal amount of senior notes outstanding."
    FakeAI(lambda *a: answer({"debt": "pass", "cash": "pass"}, quote=rows)).install(monkeypatch)
    assert auditor.audit("figure", ITEMS, TEXT).result == "pass"
    invented = "Long-term debt 32,366 7,469 | Long-term debt 99,999 1,111"
    FakeAI(lambda *a: answer({"debt": "pass", "cash": "pass"}, quote=invented)).install(monkeypatch)
    res = auditor.audit("figure", ITEMS, TEXT)
    assert res.result == "not_found" and "no verified quote" in res.items[0]["reason"]  # one invented row spoils the quote


def test_quote_ok_checks_every_row_and_keeps_single_quotes_as_before():
    from shared.sec import filing
    assert filing.quote_ok(TEXT, "Long-term debt 32,366 7,469")
    assert filing.quote_ok(TEXT, "Long-term debt 32,366 7,469 | Long-term debt 32,366 7,469")
    assert not filing.quote_ok(TEXT, "Long-term debt 32,366 7,469 | in millions")  # a part too short or not in the filing
    assert not filing.quote_ok(TEXT, "a" * 30)
