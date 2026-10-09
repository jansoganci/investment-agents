"""The Mac-check helpers: `python -m shared.ai ping` and the auditor's error test sets."""

import pytest

from shared import ai
from shared.ai import __main__ as ai_main
from shared.ai.fake import FakeAI
from shared.auditor import testset


def test_ping_says_which_keys_are_missing_and_never_prints_a_key(db, monkeypatch):
    FakeAI(lambda *a: "OK").install(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret-123")
    text = ai_main.ping()
    assert "✓ anthropic claude-sonnet-5-5" in text and "✗ deepseek deepseek-v4-pro — DEEPSEEK_API_KEY is not set" in text
    assert "sk-secret-123" not in text
    assert db.execute("SELECT count(*) FROM ai_calls WHERE job = 'ping'").fetchone()[0] >= 1  # the calls are logged


@pytest.mark.usefixtures("db")
def test_a_yes_man_auditor_misses_the_error_cases_and_the_report_says_so(monkeypatch):
    # a yes-man auditor says `pass` to everything, with a real quote: the error cases must show up as misses
    FakeAI(lambda job, system, prompt: [{"id": i["id"], "verdict": "pass", "quote": "Revenue increased 12% to $4.1 billion in the quarter",
                                         "reason": "fine"} for i in __import__("json").loads(prompt.split("\n\nFILING ")[0])["items"]]
           ).install(monkeypatch)
    results = testset.run()
    text = testset.report(results)
    assert any(not r["ok"] for r in results) and "missed" in text and "GPT-6 Sol" in text


def test_the_cases_cover_the_known_traps():
    names = " ".join(c[1] for c in testset.CASES)
    assert all(w in names for w in ("Coca-Cola", "Nvidia", "Boeing", "Pfizer 2020", "NET", "sell suggestion"))
    assert {c[0] for c in testset.CASES} == {"figure", "reading", "sell"}


def test_the_strong_model_test_hides_the_models_and_keeps_the_key(db, env, monkeypatch):
    import json

    from agents.analysis import modeltest
    from tests.analysis.test_ai_parts import handler
    from tests.fixtures.loader import FixtureSources

    fake = FakeAI(handler()).install(monkeypatch)
    text = modeltest.main(["NVDA", "NVDA"], FixtureSources())
    assert "=== NVDA" in text and "A: " in text and "B: " in text
    assert "gpt-6-sol" not in text and "claude" not in text.lower() and "sonnet" not in text.lower()  # no model names shown
    key = json.loads((env["data"] / modeltest.KEY).read_text())
    assert sorted(key.values()) == ["anthropic:claude-sonnet-5-5"] * 2 + ["openai:gpt-6-sol"] * 2  # who really answered
    assert sorted(set(fake.models)) == ["anthropic:claude-sonnet-5-5", "openai:gpt-6-sol"]
    assert "gpt-6-sol" in modeltest.main(["--reveal"])


def test_the_strong_model_test_stops_instead_of_falling_back_to_another_model(db, env, monkeypatch):
    from agents.analysis import modeltest
    from tests.analysis.test_ai_parts import handler
    from tests.fixtures.loader import FixtureSources

    fake = FakeAI(handler()).install(monkeypatch)
    fake.fail = {"anthropic"}  # model A is down: GPT must not answer in its place and be compared with itself
    with pytest.raises(ai.AIError, match="anthropic claude-sonnet-5-5"):
        modeltest.main(["NVDA", "NVDA"], FixtureSources())
