import json

import pytest

from agents.research import reading
from shared.ai.fake import FakeAI

from .helpers import SINCE, article, company_tag

QUOTE = "Şirket yıl sonu beklentisini yükseltti."


def says(tone="positive", quote=QUOTE, about="It raised its outlook.", kind="event"):
    return lambda job, system, prompt: {"tone": tone, "about": about, "kind": kind, "quote": quote}


def test_only_posts_with_a_confirmed_us_listed_tag_of_the_ticker_are_found(db):
    company_tag(db)
    company_tag(db, "Waiting Co", "WCO", status="waiting")
    company_tag(db, "Zhong", "1164.HK", us=0)
    a = article(db)
    article(db, tags=("Waiting Co",))
    article(db, tags=("Zhong",))
    article(db, published="2026-09-01T00:00:00Z")                       # outside the window
    assert [p["id"] for p in reading.posts_of(db, "cmi", SINCE)] == [a]


def test_a_positive_post_with_a_real_quote_is_kept_with_its_quote(db, monkeypatch):
    company_tag(db)
    article(db)
    FakeAI(says()).install(monkeypatch)
    tone = reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    assert (tone.positive, tone.negative, tone.neutral, tone.points) == (1, 0, 0, 1)
    assert tone.examples[0]["quote"] == QUOTE and f"“{QUOTE}”" in tone.reason
    assert db.execute("SELECT tone, quote, kind FROM readings").fetchone() == ("positive", QUOTE, "event")
    assert db.execute("SELECT read_deep FROM articles").fetchone() == (1,)


def test_a_quote_that_is_not_in_the_post_turns_the_label_neutral(db, monkeypatch):
    company_tag(db)
    article(db)
    FakeAI(says(quote="Bu cümle yazıda hiç geçmiyor ve uydurulmuş.")).install(monkeypatch)
    tone = reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    assert (tone.positive, tone.neutral) == (0, 1) and any("not in the post" in n for n in tone.notes)
    assert db.execute("SELECT tone, quote FROM readings").fetchone() == ("neutral", "")


def test_a_label_with_no_quote_at_all_is_neutral_too(db, monkeypatch):
    company_tag(db)
    article(db)
    FakeAI(says(quote="")).install(monkeypatch)
    assert reading.tone_for(db, "CMI", "Cummins Inc", SINCE).neutral == 1


def test_a_post_is_read_once_per_stock(db, monkeypatch):
    company_tag(db)
    article(db)
    fake = FakeAI(says()).install(monkeypatch)
    reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    assert len(fake.calls) == 1


def test_the_points_follow_the_net_of_positive_and_negative(db, monkeypatch):
    company_tag(db)
    for i in range(3):
        article(db, title=f"p{i}")
    FakeAI(says()).install(monkeypatch)
    assert reading.tone_for(db, "CMI", "Cummins Inc", SINCE).points == 2                   # +3
    db.execute("DELETE FROM readings")
    FakeAI(says("negative", QUOTE)).install(monkeypatch)
    assert reading.tone_for(db, "CMI", "Cummins Inc", SINCE).points == 0                   # −3


def test_posts_cut_by_the_paywall_are_not_read_and_are_counted_as_unreadable(db, monkeypatch):
    company_tag(db)
    article(db, text="", text_missing=1)
    fake = FakeAI(says()).install(monkeypatch)
    tone = reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    assert fake.calls == [] and tone.unreadable == 1 and tone.points == 1 and "no post could be read (1 cut by the paywall)" in tone.reason


def test_when_no_model_answers_the_tone_is_neutral_and_says_so(db, monkeypatch):
    company_tag(db)
    article(db)
    down = FakeAI(says())
    down.fail = {"anthropic", "deepseek", "openai", "openrouter"}
    down.install(monkeypatch)
    tone = reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    assert tone.points == 1 and any("could not be read now" in n for n in tone.notes)
    assert db.execute("SELECT count(*) FROM readings").fetchone() == (0,)


def test_an_unusable_answer_twice_becomes_a_neutral_reading(db, monkeypatch):
    company_tag(db)
    article(db)
    fake = FakeAI(lambda *a: "no json here").install(monkeypatch)
    tone = reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    assert len(fake.calls) == 2 and tone.neutral == 1 and any("unusable answer" in n for n in tone.notes)


def test_only_the_newest_posts_up_to_the_cap_are_read(db, monkeypatch):
    company_tag(db)
    for i in range(5):
        article(db, title=f"p{i}", published=f"2026-10-{6 + i:02d}T08:00:00Z")
    fake = FakeAI(says()).install(monkeypatch)
    tone = reading.tone_for(db, "CMI", "Cummins Inc", SINCE, max_posts=3)
    assert len(fake.calls) == 3 and any("newest 3 are read" in n for n in tone.notes)
    assert "Title: p4" in fake.calls[-1][2] and not any("Title: p0" in c[2] for c in fake.calls)


def test_the_prompt_names_the_company_and_treats_the_post_as_data(db, monkeypatch):
    company_tag(db)
    article(db)
    fake = FakeAI(says()).install(monkeypatch)
    reading.tone_for(db, "CMI", "Cummins Inc", SINCE)
    job, system, prompt = fake.calls[0]
    assert job == "strong" and "WORD FOR WORD" in system and "ignore them" in system
    assert "Company: Cummins Inc (CMI)" in prompt
