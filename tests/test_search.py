"""shared/search: DeepSeek's web search — the query, the answer, the errors, the cost line, the monthly limit (no real network)."""

import json

import pytest

from shared import ai, search
from shared.search import SearchError

ANSWER = {"results": [
    {"rerank_score": 2.4, "title": "Brent tops $115", "url": "https://example.com/brent", "snippet": "Brent rose.",
     "summary": "Brent crude rose above $115 a barrel on Iran worries.", "content": "", "site_name": "Example News",
     "site_icon": None, "date": "2026-10-28T06:00:00+00:00", "authority": 3},
    {"rerank_score": None, "title": "No address", "url": "", "snippet": "", "summary": ""},
    {"rerank_score": 1.1, "title": "WTI near $101", "url": "https://example.org/wti", "snippet": "", "summary": "WTI rose.",
     "site_name": None, "date": None, "authority": -1},
]}


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-secret")


@pytest.fixture
def sent(monkeypatch):
    """Answers in turn with what `sent.replies` holds; records every request body and key."""
    class Box:
        replies = [(200, json.dumps(ANSWER).encode())]
        bodies, keys = [], []

    def post(body, key, timeout=search.TIMEOUT_S):
        Box.bodies.append(body)
        Box.keys.append(key)
        return Box.replies.pop(0) if len(Box.replies) > 1 else Box.replies[0]
    monkeypatch.setattr(search, "_post", post)
    return Box


def test_the_query_gets_english_and_the_start_date():
    assert search.build_query("  Brent   crude oil ", after="2026-10-27") == "Brent crude oil lang:en after:2026-10-27"
    assert search.build_query("Pop Mart", english=False) == "Pop Mart"


def test_a_query_too_long_or_empty_is_refused_before_sending():
    with pytest.raises(SearchError, match="at most 128"):
        search.build_query("x" * 120, after="2026-10-27")
    with pytest.raises(SearchError, match="empty"):
        search.build_query("   ")


def test_hits_keep_their_fields_and_one_search_is_logged(db, key, sent):
    hits = search.search("Brent crude oil", count=5, after="2026-10-27", conn=db)
    assert sent.bodies == [{"query": "Brent crude oil lang:en after:2026-10-27", "count": 5}]
    assert sent.keys == ["sk-test-secret"]
    assert [h.url for h in hits] == ["https://example.com/brent", "https://example.org/wti"]  # a hit without an address is dropped
    first = hits[0]
    assert (first.title, first.site_name, first.date, first.score, first.authority) == (
        "Brent tops $115", "Example News", "2026-10-28T06:00:00+00:00", 2.4, 3)
    assert first.summary.startswith("Brent crude rose")
    assert db.execute("SELECT job, provider, model, input_tokens, cost_usd, outcome FROM ai_calls").fetchall() == [
        ("search", "deepseek", "search", None, 0.00075, "ok")]


def test_an_empty_answer_costs_nothing_and_is_not_logged(db, key, sent):
    sent.replies = [(200, b'{"results": []}')]
    assert search.search("nothing here", conn=db) == []
    assert db.execute("SELECT count(*) FROM ai_calls").fetchone() == (0,)


def test_the_search_dollars_count_in_the_month_and_on_the_run(db, key, sent):
    class Run:
        id, cost = None, 0.0

        def add_cost(self, usd):
            self.cost += usd
    r = Run()
    search.search("a", conn=db, run=r)
    search.search("b", conn=db, run=r)
    assert ai.month_spend(db) == pytest.approx(0.0015)
    assert r.cost == pytest.approx(0.0015)


def test_no_key_means_no_request(db, sent):
    with pytest.raises(SearchError, match="DEEPSEEK_API_KEY is not set"):
        search.search("Brent", conn=db)
    assert sent.bodies == []


@pytest.mark.parametrize("status, words", [(401, "the key was refused"), (402, "balance is empty"), (429, "rate limit"),
                                           (503, "overloaded"), (418, "unexpected")])
def test_an_http_error_says_what_happened_without_the_key(db, key, sent, status, words):
    sent.replies = [(status, json.dumps({"error": {"message": "detail from DeepSeek", "type": "x"}}).encode())]
    with pytest.raises(SearchError) as caught:
        search.search("Brent", conn=db)
    text = str(caught.value)
    assert f"HTTP {status}" in text and words in text and "detail from DeepSeek" in text
    assert "sk-test-secret" not in text
    assert db.execute("SELECT count(*) FROM ai_calls").fetchone() == (0,)  # a failed request is not billed


def test_an_answer_that_is_not_the_expected_json_is_an_error(db, key, sent):
    for raw in (b"<html>", b'{"items": []}'):
        sent.replies = [(200, raw)]
        with pytest.raises(SearchError):
            search.search("Brent", conn=db)


def test_the_monthly_limit_stops_a_search(db, key, sent):
    db.execute("INSERT INTO ai_calls (job, provider, model, cost_usd, created_at) VALUES ('strong', 'deepseek', 'deepseek-v4-pro', "
               "999, ?)", (ai.month_start() + "T00:00:00Z",))
    db.commit()
    with pytest.raises(SearchError, match="monthly AI limit"):
        search.search("Brent", conn=db)
    assert sent.bodies == []


def test_the_command_prints_hits_and_the_cost(db, key, sent, capsys):
    assert search.main(["Brent crude oil"]) == 0
    out = capsys.readouterr().out
    assert "SEARCH · 2 hit(s)" in out and "Brent tops $115 — Example News · 2026-10-28" in out
    assert "WTI near $101 — ? · no date" in out and "Cost: $0.00075" in out
    assert search.main([]) == 2


def test_the_command_reports_a_failure_in_one_message(db, sent, capsys):
    assert search.main(["Brent"]) == 1
    assert capsys.readouterr().out.startswith("SEARCH · failed\nDEEPSEEK_API_KEY is not set")
