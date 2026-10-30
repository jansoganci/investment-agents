"""/search: a question → English searches → the web and the Eye's posts → a Turkish answer with sources (stand-ins, no network)."""

import json
from datetime import datetime, timezone

import pytest

from shared import commands, search
from shared.ai.fake import FakeAI
from shared.commands import search as cmd

NOW = datetime(2026, 10, 29, 6, 0, tzinfo=timezone.utc)

REWRITE = {"queries": ["Pop Mart stock fall reason", "Pop Mart third quarter sales"], "keywords": ["Pop Mart", "POP"], "days": 14, "opinion": False}
ANSWER = ("Pop Mart'ın 3. çeyrek cirosu %45-%50 daraldı; Amerika satışları yaklaşık %75 azaldı [1]. "
          "Emtia Defteri'ne göre hisse zirveden %60 aşağıda [3].")


def hit(url, title, summary, site="Reuters", date="2026-10-28T08:00:00+00:00"):
    return search.Hit(title, url, site, date, "snip", summary, 2.0, 3)


WEB = [hit("https://x/1", "Pop Mart sales slump", "Pop Mart third-quarter revenue fell 45% to 50%; US sales fell about 75%."),
       hit("https://x/2", "Labubu craze fades", "Analysts say demand for Labubu toys has cooled.")]


def add_post(db, n, title, tags="[]", sentence="", text="", when="2026-10-28T03:00:00Z", site="emtia"):
    db.execute("INSERT INTO articles (id, url, site, title, published_at, tags, sentence, full_text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'x')",
               (n, f"https://{site}.example/{n}", site, title, when, tags, sentence, text))
    db.commit()


@pytest.fixture
def world(db, monkeypatch):
    seen = {"searches": [], "prompts": []}

    def handler(job, system, prompt):
        seen["prompts"].append((system[:12], prompt))
        return REWRITE if system.startswith("You turn one") else ANSWER

    def fake_search(query, **kw):
        seen["searches"].append((query, kw.get("after"), kw.get("count")))
        return WEB if len(seen["searches"]) == 1 else []
    monkeypatch.setattr(cmd.search, "search", fake_search)
    fake = FakeAI(handler).install(monkeypatch)
    add_post(db, 5, "Pop Mart hisseleri zirveden %60 düştü", tags='["Pop Mart"]', sentence="Pop Mart shares are 60% below their peak.",
             text="Pop Mart hissesi zirveden yüzde 60 aşağıda.")
    add_post(db, 6, "Bakır fiyatları", tags='["Bakır"]', text="Copper.")
    return {"db": db, "fake": fake, "seen": seen}


def test_the_answer_comes_from_the_web_and_the_posts_with_their_sources(world):
    text = cmd.ask("Pop Mart neden düştü", world["db"], NOW)
    assert text.startswith("🔎 ARA · Pop Mart neden düştü\n\nPop Mart'ın 3. çeyrek cirosu %45-%50 daraldı")
    assert "⚠" not in text                                              # 45, 50, 75, 60 are all in the sources
    sources = text.split("Kaynaklar\n")[1].splitlines()
    assert sources == ["1. [W] Reuters: Pop Mart sales slump — https://x/1",
                       "3. [ED] Emtia Defteri: Pop Mart hisseleri zirveden %60 düştü — https://emtia.example/5"]    # only the cited ones
    assert world["seen"]["searches"][0] == ("Pop Mart stock fall reason", "2026-10-15", 6)                          # 14 days back
    answer_prompt = world["seen"]["prompts"][-1][1]
    assert "QUESTION: Pop Mart neden düştü" in answer_prompt and "OPINION: no" in answer_prompt
    assert "[3] Emtia Defteri · 2026-10-28 · Pop Mart hisseleri" in answer_prompt and "Bakır" not in answer_prompt   # the post about copper is not a source


def test_a_number_that_is_in_no_source_is_marked(world, monkeypatch):
    FakeAI(lambda job, system, prompt: REWRITE if system.startswith("You turn one") else "Pop Mart cirosu %99 daraldı [1].").install(monkeypatch)
    assert "⚠ rakam doğrulanamadı (99)" in cmd.ask("Pop Mart neden düştü", world["db"], NOW)


def test_an_opinion_is_asked_for_only_when_the_question_asks(world, monkeypatch):
    prompts = []

    def handler(job, system, prompt):
        prompts.append(prompt)
        return dict(REWRITE, opinion=True) if system.startswith("You turn one") else ANSWER
    FakeAI(handler).install(monkeypatch)
    cmd.ask("Pop Mart için sence ne olur", world["db"], NOW)
    assert "OPINION: yes" in prompts[-1]


def test_a_broken_rewrite_falls_back_to_the_question_itself(world, monkeypatch):
    fake = FakeAI(lambda job, system, prompt: "no json" if system.startswith("You turn one") else ANSWER).install(monkeypatch)
    cmd.ask("NVDA haberleri", world["db"], NOW)
    assert world["seen"]["searches"][0][0] == "NVDA haberleri"
    assert len(fake.calls) == 2


def test_when_the_recent_search_finds_nothing_it_tries_once_without_the_date(world, monkeypatch):
    calls = []

    def fake_search(query, **kw):
        calls.append((query, kw.get("after")))
        return [] if kw.get("after") else WEB
    monkeypatch.setattr(cmd.search, "search", fake_search)
    cmd.ask("Pop Mart neden düştü", world["db"], NOW)
    assert [c[1] for c in calls] == ["2026-10-15", "2026-10-15", None, None]


def test_without_any_source_there_is_no_model_answer(world, monkeypatch):
    monkeypatch.setattr(cmd.search, "search", lambda q, **kw: [])
    fake = FakeAI(lambda job, system, prompt: dict(REWRITE, keywords=["Zzyzx"])).install(monkeypatch)
    text = cmd.ask("Bilinmeyen Şirket", world["db"], NOW)
    assert "yeni bir kaynak buldum" in text and len(fake.calls) == 1        # only the rewrite


def test_a_search_failure_is_refused_in_plain_words(world, monkeypatch):
    def broken(query, **kw):
        raise search.SearchError("DEEPSEEK_API_KEY is not set")
    monkeypatch.setattr(cmd.search, "search", broken)
    with pytest.raises(commands.Refused, match="web search could not be made: DEEPSEEK_API_KEY is not set"):
        cmd.ask("Pop Mart", world["db"], NOW)


def test_the_command_checks_its_input_and_costs_are_logged(world, monkeypatch):
    code, text = commands.run(["search"])
    assert code == 1 and text.startswith("usage: /search")
    code, text = commands.run(["search", "x" * 400])
    assert code == 1 and "at most 300" in text
    code, text = commands.run(["search", "Pop", "Mart", "neden", "düştü"])
    assert code == 0 and "Pop Mart'ın 3. çeyrek cirosu" in text and len(text) <= 4096
    jobs = [r[0] for r in world["db"].execute("SELECT job FROM ai_calls")]
    assert jobs.count("cheap") == 2


def test_shortened_links_are_not_printed(world):
    items = [{"n": 1, "tag": "W", "label": "PCMag", "title": "Sold out", "url": "https://pcmag.com/news/sk-hyn...2029"}]
    assert cmd.shown_sources("Sold out [1].", items) == ["1. [W] PCMag: Sold out"]


def test_every_cited_source_is_listed_and_tracking_parameters_are_cut():
    items = [{"n": n, "tag": "W", "label": "Site", "title": f"Title {n}",
              "url": f"https://x.example/{n}?utm_source=briefed&utm_medium=referral&id={n}&srnd=phx"} for n in range(1, 10)]
    shown = cmd.shown_sources("A [1, 2, 3]. B [4]. C [7, 8, 9].", items)
    assert [s.split(".")[0] for s in shown] == ["1", "2", "3", "4", "7", "8", "9"]
    assert shown[0] == "1. [W] Site: Title 1 — https://x.example/1?id=1"


def test_the_answer_prompt_asks_for_plain_short_text():
    assert "no markdown" in cmd.ANSWER_SYSTEM and "Four to six short lines" in cmd.ANSWER_SYSTEM


def test_verify_checks_each_line_against_the_sources_it_cites():
    items = [{"n": 1, "text": "Pop Mart fell 5% on Monday.", "title": "a"}, {"n": 2, "text": "Revenue was 99 million.", "title": "b"}]
    text, warnings = cmd.verify("Pop Mart %5 düştü [1]\nCiro 99 milyon oldu [1]", items)             # 99 is in source 2, but the line cites 1
    assert "Ciro 99 milyon" in text and warnings == ["⚠ rakam doğrulanamadı (99)"]
    text, warnings = cmd.verify("Pop Mart %5 düştü [1]\nCiro 99 milyon oldu [2]", items)
    assert warnings == []


def test_verify_drops_advice_removes_markdown_flags_missing_citations_and_cuts_long_answers():
    items = [{"n": 1, "text": "Pop Mart fell.", "title": "a"}]
    text, warnings = cmd.verify("**Pop Mart düştü** [1]\nPop Mart satın alın [1]\nBilinmeyen [99]", items)
    assert "*" not in text and "satın al" not in text and "Bilinmeyen" in text
    assert "⚠ tavsiye içeren bir satır çıkarıldı" in warnings and "⚠ olmayan kaynak numarası: [99]" in warnings
    long = "\n".join(["Pop Mart düştü [1]" + " x" * 40] * 30)
    cut, warnings = cmd.verify(long, items)
    assert len(cut) <= cmd.MAX_ANSWER_CHARS and "ℹ cevap uzun olduğu için kısaltıldı" in warnings
