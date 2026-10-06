"""Asking me for a missing figure: plain, once, reminded once; the cheap model may not lose a ticker, year or command."""

import pytest

from agents.analysis import ask
from shared.ai.fake import FakeAI


def stock_with_missing(db, rows):
    db.execute("INSERT INTO stocks (cik, ticker, company, status, created_at) VALUES ('1', 'NKE', 'Nike', 'watching', 'x')")
    for year, figure in rows:
        db.execute("INSERT INTO missing_data (stock_id, year, figure, names_tried, status, created_at) "
                   "VALUES (1, ?, ?, '[]', 'open', 'x')", (year, figure))
    db.commit()


def test_the_template_says_why_where_and_how_to_answer():
    text = ask.template([("NKE", "2026", "interest"), ("NKE", "TTM 2026-02-28", "debt")])
    assert "NKE · 2026 · Interest expense" in text and "Why: the interest cover cannot be computed." in text
    assert "Where: income statement or the debt note → 'Interest expense'." in text
    assert "Answer: /data NKE 2026 interest <value, e.g. 0.25bn>" in text
    assert "Answer: /data NKE TTM 2026-02-28 debt <value" in text and "never counted as zero" in text


def test_a_figure_is_asked_once_then_reminded_once_a_week_later(db, monkeypatch):
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    fake.fail = {"deepseek", "openrouter", "openai"}  # the cheap model is down: the template is used as it is
    stock_with_missing(db, [("2026", "interest")])
    first = ask.request(db, today="2026-10-06")
    assert first.startswith("MISSING FIGURES") and "/data NKE 2026 interest" in first
    assert ask.request(db, today="2026-10-10") is None                      # not asked twice
    again = ask.request(db, today="2026-10-13")
    assert again.startswith("REMINDER") and "/data NKE 2026 interest" in again  # a week later, once
    assert ask.request(db, today="2026-11-30") is None                      # never again


def test_an_answered_figure_is_not_asked(db, monkeypatch):
    FakeAI(lambda *a: "x").install(monkeypatch).fail.update({"deepseek", "openrouter", "openai"})
    stock_with_missing(db, [("2026", "interest")])
    db.execute("INSERT INTO financials (stock_id, period_end, period_type, figure, value, source, created_at) "
               "VALUES (1, '2026', 'annual', 'interest', 250000000, 'user', 'x')")
    db.commit()
    assert ask.request(db, today="2026-10-06") is None


def test_the_cheap_model_text_is_used_only_if_nothing_is_lost(db, monkeypatch):
    original = ask.template([("NKE", "2026", "interest")])
    FakeAI(lambda *a: original.replace("cannot be computed", "is missing")).install(monkeypatch)
    assert "is missing" in ask.simplify(original)
    FakeAI(lambda *a: original.replace("/data NKE 2026 interest", "/data nke interest")).install(monkeypatch)
    assert ask.simplify(original) == original  # a changed command: the template stays
    FakeAI(lambda *a: original.replace("2026", "year")).install(monkeypatch)
    assert ask.simplify(original) == original  # a lost year: the template stays


def test_without_ai_the_message_is_the_plain_template_and_no_model_is_called(db, monkeypatch):
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    stock_with_missing(db, [("2026", "interest")])
    text = ask.request(db, plain=False, today="2026-10-06")
    assert "/data NKE 2026 interest" in text and fake.calls == []


def test_the_cheap_call_keeps_its_stock_when_the_message_is_about_one(db, monkeypatch):
    FakeAI(lambda *a: "x").install(monkeypatch)  # an unusable rewrite: the template is sent, the call is still logged
    stock_with_missing(db, [("2026", "interest")])
    ask.request(db, today="2026-10-06")
    assert db.execute("SELECT stock_id FROM ai_calls").fetchall() == [(1,)]
    db.execute("INSERT INTO stocks (cik, ticker, company, status, created_at) VALUES ('2', 'KO', 'Coca-Cola', 'watching', 'x')")
    for sid in (1, 2):
        db.execute("INSERT INTO missing_data (stock_id, year, figure, names_tried, status, created_at) "
                   "VALUES (?, '2025', 'debt', '[]', 'open', 'x')", (sid,))
    db.commit()
    ask.request(db, today="2026-10-06")  # one message about two stocks: no single stock to keep
    assert db.execute("SELECT stock_id FROM ai_calls ORDER BY id DESC LIMIT 1").fetchone() == (None,)
