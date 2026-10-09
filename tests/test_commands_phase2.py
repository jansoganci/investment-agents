"""Phase 2 commands (roadmap 10.2): /spend /model /note /thesis /closewarning and their /undo."""

import pytest

from agents.analysis import card, run
from shared import ai, commands, drive
from shared.ai.fake import FakeAI
from shared.commands import stocks
from tests.analysis.test_ai_parts import handler
from tests.fixtures.loader import FixtureSources


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    src = FixtureSources()
    monkeypatch.setattr(stocks, "SOURCES", src)
    return src


def do(*argv):
    return commands.run([*argv, "--yes"])


def nvda_with_card(db, monkeypatch, ai_on=False):
    if ai_on:
        FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", FixtureSources(), today="2026-10-06", use_ai=ai_on)


def test_model_alone_only_shows_and_with_arguments_asks_first(db):
    code, text = commands.run(["model"])
    assert code == 0 and "strong: claude-sonnet-5-5 (anthropic)" in text and "auditor: claude-sonnet-5-5" in text
    code, text = commands.run(["model", "strong", "gpt-6-sol"])
    assert text.startswith("CONFIRM") and "claude-sonnet-5-5 (anthropic) → gpt-6-sol" in text
    assert ai.chain("strong", db)[0]["provider"] == "anthropic"  # nothing changed yet


def test_model_override_and_undo(db):
    code, text = do("model", "strong", "gpt-6-sol")
    assert code == 0 and "change #1" in text and "/undo 1" in text
    assert ai.chain("strong", db)[0]["model"] == "gpt-6-sol"
    assert "my override" in commands.run(["model"])[1]
    do("model", "strong", "default")
    assert ai.chain("strong", db)[0]["provider"] == "anthropic"
    code, text = do("undo", "2")  # takes back the "default": the override of change #1 is in force again
    assert code == 0 and ai.chain("strong", db)[0]["model"] == "gpt-6-sol"
    code, text = do("undo", "1")
    assert ai.chain("strong", db)[0]["provider"] == "anthropic"


def test_model_refuses_unknown_jobs_and_models(db):
    assert commands.run(["model", "strong", "nonsense-9"])[0] == 1
    assert "usage" in commands.run(["model", "weird", "gpt-6-sol"])[1]


def test_spend_adds_up_by_provider_and_shows_what_is_left(db, monkeypatch):
    FakeAI(lambda *a: "x").install(monkeypatch)
    ai.call("strong", "p", conn=db)
    ai.call("auditor", "p", conn=db)
    text = commands.run(["spend"])[1]
    assert "- anthropic: $0.01 · 2 calls" in text  # writer and auditor are both Sonnet
    assert "of $30" in text and "$29.99 left" in text
    db.execute("INSERT INTO ai_calls (job, provider, model, cost_usd, estimated, outcome, created_at) "
               "VALUES ('strong', 'openai', 'gpt-9', 0.5, 1, 'cut', ?)", (ai.month_start() + "T01:00:00Z",))
    db.commit()
    text = commands.run(["spend"])[1]
    assert "- openai: $0.50 · 1 calls, 1 at the default price (no price in settings.yaml), 1 billed but rejected" in text


def test_note_thesis_and_closewarning_write_dated_notes_and_undo_withdraws_them(db, env, monkeypatch):
    nvda_with_card(db, monkeypatch)
    path = drive.find_card("NVDA")
    code, text = commands.run(["note", "NVDA", "met", "management", "at", "a", "conference"])
    assert text.startswith("CONFIRM") and "met management at a conference" in text
    assert "met management" not in path.read_text()  # not before `yes`
    do("note", "NVDA", "met", "management", "at", "a", "conference")
    do("thesis", "NVDA", "point", "2:", "debt", "matters", "above", "2x", "free", "cash")
    body = path.read_text()
    assert "met management at a conference" in body and "Thesis correction: point 2: debt matters above 2x free cash" in body
    assert db.execute("SELECT count(*) FROM card_entries WHERE who='user'").fetchone()[0] == 2
    do("undo", "1")
    last = card.entries(path.read_text())[-1]
    assert last["record"] == "note" and "Change #1 withdrawn" in last["body"]
    assert "met management at a conference" in path.read_text()  # append-only: the old note stays


def test_closewarning_needs_a_real_open_warning_and_undo_reopens_it(db, env, monkeypatch):
    nvda_with_card(db, monkeypatch)
    path = drive.find_card("NVDA")
    code, text = commands.run(["closewarning", "NVDA", "U9", "not", "real"])
    assert code == 1 and "no open warning U9" in text and "Open: U1" in text
    code, text = do("closewarning", "NVDA", "U1", "one-off", "tax", "deposit,", "not", "recurring")
    assert code == 0 and "change #1" in text
    assert card.closed_warnings(path.read_text()) == {"U1"}
    assert "no open warning U1" in commands.run(["closewarning", "NVDA", "U1", "again"])[1]
    do("undo", "1")
    assert card.closed_warnings(path.read_text()) == set()
    assert "Warning U1 reopened — change #1 withdrawn" in path.read_text()


def test_notes_need_a_card(db, monkeypatch):
    assert "not in the system" in commands.run(["note", "ZZZ", "hello"])[1]
    stocks_row = db.execute("INSERT INTO stocks (cik, ticker, company, status, created_at) VALUES ('1', 'ABC', 'Abc', 'candidate', 'x')")
    db.commit()
    assert "has no card yet" in commands.run(["note", "ABC", "hello"])[1]


def test_model_allows_writer_and_auditor_in_one_family(db):
    # my decision (2026-10-09): writer and auditor may be the same model (both Sonnet 5.5 high by default)
    assert do("model", "auditor", "sonnet-5.5")[0] == 0
    assert do("model", "strong", "gpt-6-sol")[0] == 0 and do("model", "auditor", "gpt-6-sol")[0] == 0
