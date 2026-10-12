import json
from datetime import date, timedelta

import pytest

from agents.analysis import card
from agents.counter import count as counter_count
from agents.research import __main__ as cli
from agents.research import run
from shared import clock, drive
from shared.ai.fake import FakeAI
from tests.fixtures.loader import FixtureSources

from .helpers import article, company_tag
from .test_health_tailwind import add_prices, rising

TODAY = clock.today_local()
URL = "https://news.example/nvda-contract"
POST = "NVIDIA yeni bir büyük veri merkezi sözleşmesi imzaladı. Şirket yıl sonu beklentisini yükseltti."
QUOTE = "Şirket yıl sonu beklentisini yükseltti."
PAGE = "NVIDIA signed a large new data center contract with a major cloud customer."
NEWS = {"story": "Nvidia designs chips for AI. It earns mostly from selling them to data centers.",
        "events": [{"summary": "A large new data center contract.", "date": "2026-10-01", "source_url": URL,
                    "quote": "signed a large new data center contract", "scope": "company_specific",
                    "class": "important_positive", "serious_type": None}],
        "commodity_links": [{"commodity": "copper", "role": "user", "source_url": URL}]}


def model(job, system, prompt):
    if job == "auditor":
        return [{"id": "e1", "verdict": "pass", "quote": PAGE, "reason": "ok"}]
    if "Today:" in prompt:
        return NEWS
    return {"tone": "positive", "about": "It signed a contract.", "kind": "event", "quote": QUOTE}


@pytest.fixture
def world(db, env, monkeypatch):
    company_tag(db, "Nvidia", "NVDA")
    db.execute("UPDATE tags SET sector = 'Information Technology', country = 'United States' WHERE tag = 'Nvidia'")
    for i in range(3):
        article(db, title=f"Nvidia {i}", text=POST, tags=("Nvidia",), published=clock.utc_iso(clock.now_utc() - timedelta(days=1)))
    run_at = clock.utc_iso()
    db.execute("INSERT INTO counts (run_at, kind, key, label, posts_7d, posts_30d, rank, has_card, points, created_at) "
               "VALUES (?, 'stock', 'NVDA', 'Nvidia', 3, 3, 1, 0, 1, ?)", (run_at, run_at))
    db.commit()
    add_prices(db, "XLK", rising(50, 100, 2.0))
    add_prices(db, "SPY", [400.0] * 50)
    add_prices(db, "HG=F", list(reversed(rising(50, 3.0, 0.02))))                  # copper below its average: good for a user
    fake = FakeAI(model)
    fake.sources = [{"url": URL, "title": "t", "cited_text": None}]
    fake.install(monkeypatch)
    return {"db": db, "fake": fake}


def go(db, **kw):
    kw.setdefault("sources", FixtureSources())
    kw.setdefault("fetch", lambda url, max_bytes=0: PAGE)
    kw.setdefault("ensure", lambda conn, symbols, source: [])
    return run.weekly(db, **kw)


def test_the_week_scores_the_stock_opens_the_card_and_writes_the_report(world):
    db = world["db"]
    text = go(db)
    assert text.startswith("RESEARCH · 1 stock(s) scored") and "NVDA Nvda — " in text
    stock = db.execute("SELECT status, added_by, sector, country, exchange, opened, last_entry, commodity_checked FROM stocks").fetchone()
    assert stock == ("candidate", "counter", "Information Technology", "United States", None, TODAY, TODAY, TODAY)
    sc = db.execute("SELECT mentions, tone, sector_tailwind, news_flow, quick_health, score, week FROM scores").fetchone()
    assert sc[0] == 1 and sc[1] == 2 and sc[2] == 2 and sc[3] == 2 and sc[4] == 2 and sc[5] == 9 and sc[6] == run.week_label(TODAY)
    assert db.execute("SELECT commodity, role FROM commodity_links").fetchone() == ("copper", "user")
    assert db.execute("SELECT class, status FROM news_events").fetchone() == ("important_positive", "not_checked")
    assert db.execute("SELECT record, who FROM card_entries").fetchone() == ("research", "agent_2")
    assert db.execute("SELECT read_deep FROM articles").fetchall() == [(1,)] * 3
    report = (drive.weekly() / f"{TODAY}-research.md").read_text(encoding="utf-8")
    assert "## 1. NVDA Nvda — 9/10" in report and "- **news_flow** 2/2" in report


def test_the_card_has_the_story_the_header_and_a_research_entry(world):
    go(world["db"])
    path = drive.find_card("NVDA")
    assert path is not None and path.parent.name == "NVDA - Nvda"
    text = path.read_text(encoding="utf-8")
    head, _ = card.split(text)
    assert head["status"] == "candidate" and head["sector"] == "Information Technology" and head["last_entry"] == TODAY
    assert "> Story: Nvidia designs chips for AI. It earns mostly from selling them to data centers." in text
    entry = card.entries(text)[-1]
    assert (entry["record"], entry["who"]) == ("research", "agent_2")
    data = card._yaml_of(entry["body"])
    assert data["score"] == 9 and set(data["criteria"]) == {"mentions", "tone", "sector_tailwind", "news_flow", "quick_health"}
    assert data["criteria"]["tone"]["quotes"][0]["quote"] == QUOTE
    assert data["events"][0]["source"] == URL and data["commodity_links"][0]["commodity"] == "copper"
    assert "### Summary" in entry["body"] and "### Thesis" not in entry["body"]


def test_a_stock_with_a_card_is_not_scored_again(world):
    db = world["db"]
    go(db)
    again = go(db)
    assert "Not researched — NVDA: NVDA already has a card" in again
    assert db.execute("SELECT count(*) FROM scores").fetchone() == (1,)


def test_without_a_counter_run_there_is_nothing_to_do(db, env):
    assert "the Counter has not run yet" in run.weekly(db)


def test_an_old_counter_run_is_noted(world):
    db = world["db"]
    old = clock.utc_iso(clock.now_utc() - timedelta(days=6))
    db.execute("UPDATE counts SET run_at = ?", (old,))
    db.commit()
    assert "The latest Counter run is 6 days old" in go(db)


def test_one_failing_stock_does_not_stop_the_others(world):
    db = world["db"]
    run_at = db.execute("SELECT max(run_at) FROM counts").fetchone()[0]
    db.execute("INSERT INTO counts (run_at, kind, key, label, posts_7d, posts_30d, rank, has_card, points, created_at) "
               "VALUES (?, 'stock', 'ZZZZ', 'Zed', 1, 1, 2, 0, 0, ?)", (run_at, run_at))
    db.commit()
    text = go(db)
    assert "1 stock(s) scored" in text and "Not researched — ZZZZ: SEC does not know the ticker ZZZZ" in text


def test_only_the_top_ranks_are_taken(world):
    db = world["db"]
    run_at = db.execute("SELECT max(run_at) FROM counts").fetchone()[0]
    db.execute("INSERT INTO counts (run_at, kind, key, label, posts_7d, posts_30d, rank, has_card, points, created_at) "
               "VALUES (?, 'stock', 'KO', 'Coca-Cola', 1, 1, 2, 0, 0, ?)", (run_at, run_at))
    db.commit()
    go(db, limit=1)
    assert [r[0] for r in db.execute("SELECT ticker FROM stocks")] == ["NVDA"]


def test_a_stock_i_added_myself_has_no_posts_so_mentions_are_zero_and_tone_one(db, env, monkeypatch):
    db.execute("INSERT INTO stocks (cik, ticker, company, status, in_portfolio, added_by, created_at) "
               "VALUES ('0001045810', 'NVDA', 'Nvidia Corp', 'watching', 'no', 'user', 'x')")
    db.commit()
    fake = FakeAI(model)
    fake.sources = [{"url": URL, "title": "t", "cited_text": None}]
    fake.install(monkeypatch)
    o = run.research_one(db, "NVDA", added_by="user", sources=FixtureSources(), fetch=lambda u, m=0: PAGE,
                         ensure=lambda c, s, p: [])
    assert (o.points["mentions"], o.points["tone"]) == (0, 1) and "no post mentions it" in o.reasons["tone"]
    assert "added by me" in o.lines()[0]
    assert db.execute("SELECT status, added_by FROM stocks").fetchone() == ("watching", "user")      # the state is not touched
    assert drive.find_card("NVDA") is not None and db.execute("SELECT count(*) FROM stocks").fetchone() == (1,)


def test_when_sec_cannot_be_read_the_quick_health_is_unclear_and_the_week_goes_on(world):
    class Broken(FixtureSources):
        def facts(self, cik):
            raise RuntimeError("SEC is down")

    db = world["db"]
    text = go(db, sources=Broken())
    assert "1 stock(s) scored" in text and "unclear — SEC data could not be read" in text
    assert db.execute("SELECT quick_health FROM scores").fetchone() == (1,)


def test_when_the_ai_is_down_every_ai_criterion_is_neutral_and_the_card_is_still_born(world):
    world["fake"].fail = {"anthropic", "deepseek", "openai", "openrouter"}
    db = world["db"]
    text = go(db)
    sc = db.execute("SELECT tone, news_flow FROM scores").fetchone()
    assert sc == (1, 1) and "unclear — the news could not be checked" in text and drive.find_card("NVDA") is not None


def test_a_rollback_leaves_no_stock_behind(world, monkeypatch):
    db = world["db"]
    monkeypatch.setattr(run.card, "write", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    text = go(db)
    assert "Not researched — NVDA: OSError: disk full" in text
    assert db.execute("SELECT count(*) FROM stocks").fetchone() == (0,) and db.execute("SELECT count(*) FROM scores").fetchone() == (0,)


def test_the_mention_bars_are_the_counters(db):
    for n in range(0, 12):
        assert run.mentions_points(n) == counter_count.mentions_points(n)


def test_week_label():
    assert run.week_label("2026-10-12") == "2026-W42" and run.week_label("2026-01-01") == "2026-W01"


def test_the_command_runs_the_weekly_job_and_one_stock(world, capsys, monkeypatch):
    monkeypatch.setattr(run, "LiveSources", lambda: FixtureSources())
    monkeypatch.setattr(run.page, "fetch_text", lambda url, max_bytes=0: PAGE)
    monkeypatch.setattr(run, "_ensure_prices", lambda conn, symbols, source=None: [])
    assert cli.main([]) == 0
    assert "RESEARCH · 1 stock(s) scored" in capsys.readouterr().out
    assert cli.main(["KO!"]) == 2
