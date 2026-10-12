import pytest

from agents.research import run as research_run
from shared import commands, drive
from shared.ai.fake import FakeAI
from shared.commands import stocks
from tests.fixtures.loader import FixtureSources

from .test_run import PAGE, URL, go, model, world  # noqa: F401  (the fixture and helpers of the weekly run)


def say(*words, yes=False):
    return commands.run([*words, *(["--yes"] if yes else [])])


def test_candidates_before_any_score(db, env):
    code, text = say("candidates")
    assert code == 0 and "No stock has been scored yet" in text


def test_candidates_lists_the_latest_week_best_first_with_reasons(world):
    db = world["db"]
    go(db)
    code, text = say("candidates")
    assert code == 0 and text.startswith("CANDIDATES · week ") and "1. NVDA Nvda — 9/10 (mentions 1 · tone 2" in text
    assert "news flow: no confirmed serious negative; important positive: A large new data center contract." in text
    assert "· candidate" in text and "The score is a ranking, not a buy." in text


def test_candidates_is_in_the_menu_and_built():
    assert commands.REGISTRY["candidates"].built and "candidates" in commands.MENU


# --- /watch for a stock with no card ------------------------------------------------------------------------------------------

@pytest.fixture
def watch(db, env, monkeypatch):
    monkeypatch.setattr(stocks, "RESEARCH_ON_WATCH", True)
    monkeypatch.setattr(stocks, "SOURCES", FixtureSources())
    monkeypatch.setattr(research_run.page, "fetch_text", lambda url, max_bytes=0: PAGE)
    monkeypatch.setattr(research_run, "_ensure_prices", lambda conn, symbols, source=None: [])
    fake = FakeAI(model)
    fake.sources = [{"url": URL, "title": "t", "cited_text": None}]
    fake.install(monkeypatch)
    from agents.analysis import run as analysis

    seen = {}

    def analyze(conn, ticker, sources, **kw):
        seen["ticker"], seen["use_ai"] = ticker, kw.get("use_ai")
        return type("O", (), {"text": f"ANALYSIS · {ticker}\nGrade solid"})()

    monkeypatch.setattr(analysis, "analyze", analyze)
    return seen


def test_the_preview_of_a_new_stock_says_agent_2_runs_after(watch):
    code, text = say("watch", "NVDA")
    assert code == 0 and "agent 2 runs for it right after" in text and "then agent 3 writes the first analysis" in text


def test_watch_saves_the_state_then_agent_2_opens_the_card_then_agent_3_analyses(watch, db):
    code, text = say("watch", "NVDA", yes=True)
    assert code == 0 and "DONE · change #" in text
    assert "RESEARCH · NVDA" in text and "added by me" in text and "ANALYSIS · NVDA" in text
    assert watch == {"ticker": "NVDA", "use_ai": True}
    assert db.execute("SELECT status, added_by FROM stocks").fetchone() == ("watching", "user")
    assert drive.find_card("NVDA") is not None
    assert db.execute("SELECT mentions, tone FROM scores").fetchone() == (0, 1)             # no posts: mentions 0, tone 1


def test_a_stock_that_already_exists_is_only_a_state_change(watch, db):
    db.execute("INSERT INTO stocks (cik, ticker, company, status, in_portfolio, created_at) VALUES ('0001045810', 'NVDA', 'Nvidia', "
               "'candidate', 'no', 'x')")
    db.commit()
    code, text = say("watch", "NVDA", yes=True)
    assert "RESEARCH" not in text and db.execute("SELECT count(*) FROM scores").fetchone() == (0,)


def test_a_failure_in_research_does_not_hide_the_analysis(watch, db, monkeypatch):
    monkeypatch.setattr(research_run, "research_one", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    code, text = say("watch", "NVDA", yes=True)
    assert "ERROR · research" in text and "ANALYSIS · NVDA" in text
