"""Agent 3 end to end with the AI parts on (a fake AI): the card, the database, the message."""

import json

import pytest

from agents.analysis import card, run
from shared import ai, drive, runlog
from shared.ai.fake import FakeAI
from tests.analysis.test_ai_parts import NOTES, THESIS, handler
from tests.fixtures.loader import FixtureSources


@pytest.fixture
def src():
    return FixtureSources()


def entries_of(ticker):
    return card.entries(drive.find_card(ticker).read_text())


def test_the_first_ai_run_writes_the_thesis_the_answers_and_the_audits(db, env, src, monkeypatch):
    fake = FakeAI(handler()).install(monkeypatch)
    with runlog.run("analysis") as r:
        out = run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True, run=r)
    body = drive.find_card("NVDA").read_text()
    assert "### Thesis\nWhy it is owned:\n1. It sells the chips AI runs on." in body
    assert "What would break it:\n1. Revenue growth turns negative." in body and "3. A major customer leaves." in body
    entry = db.execute("SELECT thesis_status, unverified FROM card_entries").fetchone()
    assert entry == ("intact", 0)
    assert sorted(x[0] for x in db.execute("SELECT audit FROM audits")) == ["figure", "reading"]  # a first card: cards 1 + 2
    assert db.execute("SELECT count(*) FROM ai_calls").fetchone()[0] == len(fake.calls) >= 4
    assert db.execute("SELECT cost_usd FROM runs WHERE job='analysis'").fetchone()[0] > 0  # the dollars are on the run row
    assert "answer" in body and NOTES in body  # a why answer and its quote sit on the warning
    assert "UNVERIFIED" not in out.text and out.grade == "solid"


def test_without_ai_the_card_is_as_in_phase_1(db, env, src, monkeypatch):
    fake = FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-06")
    assert fake.calls == []
    assert "Not written yet — the first thesis is written by agent 3's AI" in drive.find_card("NVDA").read_text()
    assert db.execute("SELECT count(*) FROM audits").fetchone()[0] == 0


def test_a_second_run_checks_the_thesis_and_does_not_write_a_new_one(db, env, src, monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True)
    FakeAI(handler(check={"status": "watch", "point": None, "reason": "debt is up, still covered", "quote": ""})).install(monkeypatch)
    out = run.analyze(db, "NVDA", src, today="2026-10-13", use_ai=True)
    last = entries_of("NVDA")[-1]
    assert "Unchanged — see the thesis of 2026-10-06. Status: watch. debt is up, still covered" in last["body"]
    assert "thesis_check:" in last["body"]
    assert db.execute("SELECT thesis_status FROM card_entries ORDER BY id DESC").fetchone()[0] == "watch"
    assert "Thesis watch: debt is up, still covered" in out.text
    # the thesis the next check reads is still the first one
    assert card.last_thesis(drive.find_card("NVDA").read_text())[0] == "2026-10-06"


def test_my_note_after_the_thesis_goes_to_the_next_check(db, env, src, monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True)
    path = drive.find_card("NVDA")
    card.append(path, card.note_entry("2026-10-08", "Thesis point 2 corrected: debt matters only above 2x free cash."), {})
    seen = {}

    def spy(job, system, prompt):
        if system.startswith("You check whether"):
            seen["prompt"] = prompt
        return handler()(job, system, prompt)
    FakeAI(spy).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-13", use_ai=True)
    assert "debt matters only above 2x free cash" in seen["prompt"]


def test_a_held_stock_with_a_broken_thesis_gets_a_sell_suggestion_with_its_evidence(db, env, src, monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True)
    db.execute("UPDATE stocks SET in_portfolio='yes'")
    db.commit()
    broken = {"status": "broken", "point": 3, "reason": "the major customer left", "quote": NOTES}
    FakeAI(handler(check=broken)).install(monkeypatch)
    out = run.analyze(db, "NVDA", src, today="2026-10-13", use_ai=True)
    assert "CONSIDER SELLING · NVDA — the thesis broke" in out.text and "The decision is yours." in out.text
    assert "sell_suggestion" in entries_of("NVDA")[-1]["body"]
    assert db.execute("SELECT count(*) FROM audits WHERE audit='sell'").fetchone()[0] == 1


def test_a_failed_audit_marks_the_entry_unverified_and_holds_the_suggestion(db, env, src, monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True)
    db.execute("UPDATE stocks SET in_portfolio='yes'")
    db.commit()
    broken = {"status": "broken", "point": 3, "reason": "the major customer left", "quote": NOTES}
    FakeAI(handler(check=broken, verdict={"debt": "fail"})).install(monkeypatch)
    out = run.analyze(db, "NVDA", src, today="2026-10-13", use_ai=True)
    assert "SELL SUGGESTION HELD · NVDA" in out.text and "UNVERIFIED: the auditor disagrees" in out.text
    assert "CONSIDER SELLING" not in out.text
    assert db.execute("SELECT unverified FROM card_entries ORDER BY id DESC").fetchone()[0] == 1
    assert "unverified: 'yes'" in entries_of("NVDA")[-1]["body"] or "unverified: yes" in entries_of("NVDA")[-1]["body"]
    assert db.execute("SELECT result FROM audits WHERE audit='figure' ORDER BY id DESC").fetchone()[0] == "fail"


def test_if_the_ai_is_down_the_numbers_and_the_card_are_still_written(db, env, src, monkeypatch):
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    fake.fail = {"anthropic", "deepseek", "openai", "openrouter"}
    out = run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True)
    assert out.grade == "solid" and "The thesis could not be written" in out.text
    assert "the AI answer could not be used this time" in drive.find_card("NVDA").read_text()
    assert db.execute("SELECT thesis_status FROM card_entries").fetchone()[0] is None  # no thesis, so the next run writes it


def test_ask_for_missing_figures_when_asked_to(db, env, src, monkeypatch):
    FakeAI(lambda *a: "x").install(monkeypatch).fail.update({"deepseek", "openrouter", "openai"})
    out = run.analyze(db, "SNAP", src, today="2026-10-06", ask_missing=True)
    if db.execute("SELECT count(*) FROM missing_data").fetchone()[0]:
        assert "MISSING FIGURES — I need your help" in out.text and "/data SNAP" in out.text


def test_a_drop_alert_is_checked_against_the_thesis_and_closed(db, env, src, monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True)
    db.execute("INSERT INTO signals (kind, stock_id, date, detail, created_at) VALUES ('drop_alert', 1, '2026-10-12', "
               "'{\"drop\": -0.23}', 'x')")
    db.commit()
    FakeAI(lambda *a: {"status": "watch", "reason": "price fell, the filing shows no break", "quote": ""}).install(monkeypatch)
    text = run.drop_alerts(db, src, today="2026-10-13")
    assert "DROP ALERT · NVDA — thesis watch: price fell, the filing shows no break" in text and "/analyze NVDA" in text
    assert db.execute("SELECT status FROM signals").fetchone()[0] == "done"
    last = entries_of("NVDA")[-1]
    assert (last["date"], last["record"], last["who"]) == ("2026-10-13", "note", "agent_3")
    assert "filing only; no news was available" in last["body"]
    assert run.drop_alerts(db, src, today="2026-10-14") is None  # nothing pending any more


def test_a_drop_alert_without_a_thesis_asks_for_an_analysis_and_stays_pending(db, env, src, monkeypatch):
    run.analyze(db, "NVDA", src, today="2026-10-06")  # numbers only: no thesis
    db.execute("INSERT INTO signals (kind, stock_id, date, created_at) VALUES ('drop_alert', 1, '2026-10-12', 'x')")
    db.commit()
    FakeAI(lambda *a: "x").install(monkeypatch)
    assert "no thesis is written yet" in run.drop_alerts(db, src, today="2026-10-13")
    assert db.execute("SELECT status FROM signals").fetchone()[0] == "pending"


def test_an_archived_stock_drop_alert_is_closed_without_a_check(db, env, src, monkeypatch):
    run.analyze(db, "NVDA", src, today="2026-10-06")
    db.execute("UPDATE stocks SET status='archived'")
    db.execute("INSERT INTO signals (kind, stock_id, date, created_at) VALUES ('drop_alert', 1, '2026-10-12', 'x')")
    db.commit()
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    assert run.drop_alerts(db, src, today="2026-10-13") is None and fake.calls == []
    assert db.execute("SELECT status FROM signals").fetchone()[0] == "done"


def test_the_weekly_run_uses_the_ai_only_when_asked(db, env, src, monkeypatch):
    run.analyze(db, "NVDA", src, today="2026-10-06")
    db.execute("UPDATE stocks SET status='watching'")
    db.execute("UPDATE card_entries SET filing='an-older-filing'")  # so the newest filing counts as new
    db.commit()
    fake = FakeAI(handler()).install(monkeypatch)
    text = run.weekly(db, src, today="2026-10-13")
    assert "ANALYSIS · NVDA" in text and fake.calls == []  # without --ai: numbers only
    db.execute("UPDATE card_entries SET filing='an-older-filing'")
    db.commit()
    text = run.weekly(db, src, today="2026-10-20", use_ai=True)
    assert "ANALYSIS · NVDA" in text and fake.calls
    assert "Why it is owned:" in drive.find_card("NVDA").read_text()
