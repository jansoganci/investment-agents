"""agents/eye/companies: the companies a post's text is about → `articles.companies` → the tag classifier → the Counter."""

import json
from datetime import datetime, timezone

import pytest

from agents.counter import count
from agents.eye import companies, run, tags
from shared import ai, config
from shared.ai.fake import FakeAI

NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)


def article(db, title="Bakır yükseldi", text="BHP ve Rio Tinto üretimi kıstı.", tags_=("Bakır",), companies_=None, missing=0, day="2026-10-11T10:00:00Z"):
    cur = db.execute("INSERT INTO articles (url, site, title, published_at, tags, full_text, text_missing, companies, created_at) "
                     "VALUES (?, 'emtia', ?, ?, ?, ?, ?, ?, ?)",
                     (f"https://x/{title}/{day}", title, day, json.dumps(list(tags_), ensure_ascii=False), text, missing,
                      None if companies_ is None else json.dumps(companies_), day))
    db.commit()
    return cur.lastrowid


def model(monkeypatch, names=("BHP", "Rio Tinto")):
    def handler(job, system, prompt):
        if "TAGS:\n" in prompt:
            asked = [d["tag"] for d in json.JSONDecoder().raw_decode(prompt.split("TAGS:\n", 1)[1])[0]]
            known = {"BHP": ("BHP", True), "Rio Tinto": ("RIO", True), "Saudi Aramco": ("2222.SR", False)}
            return [{"tag": t, "kind": "company" if t in known else "other", "name": t, "ticker": known.get(t, (None,))[0],
                     "us_listed": known[t][1] if t in known else None} for t in asked]
        return json.dumps(list(names))
    return FakeAI(handler).install(monkeypatch)


def test_the_answer_is_cleaned_to_a_short_list_of_distinct_names():
    assert companies.clean(["  BHP ", "bhp", "Rio   Tinto", "", "x" * 80]) == ["BHP", "Rio Tinto"]
    assert companies.clean({"companies": ["Shell"]}) == ["Shell"]
    assert len(companies.clean([f"Co{i}" for i in range(10)])) == companies.MAX_COMPANIES
    for bad in ("BHP", [1, 2], {"x": 1}, None):
        with pytest.raises(ValueError):
            companies.clean(bad)


def test_a_company_the_post_does_not_print_is_dropped():
    text = "Antamina bakır madeni üretimi durdurdu. Fortum'un nükleer geliri arttı. Metal fiyatları düştü. Saudi Aramco'nun kârı arttı."
    assert companies.named_in("Fortum", "t", text) and companies.named_in("Saudi Aramco", "t", text)      # a Turkish ending; one telling word is enough
    assert not companies.named_in("Glencore", "Antamina durdu", text) and not companies.named_in("BHP", "t", text)      # inferred owners
    assert not companies.named_in("Meta", "t", text)                                  # "metal" is another word
    assert not companies.named_in("Tata Steel", "t", "Hindistan çelik (steel) fiyatları yükseldi.")      # "steel" alone is generic
    assert companies.named_in("Tata Steel", "t", "Tata Steel fiyatları artırdı.") and companies.named_in("İş Bankası", "t", "is bankasi")
    assert not companies.named_in("", "t", text)


def test_extract_keeps_only_the_names_the_post_prints(db, monkeypatch):
    model(monkeypatch, names=("BHP", "Glencore", "Fortum"))
    assert companies.extract("t", "BHP üretimi kıstı. Fortum'un geliri arttı.", conn=db) == ["BHP", "Fortum"]


def test_the_prompt_asks_for_companies_the_post_is_about_and_treats_the_post_as_data(db, monkeypatch):
    fake = model(monkeypatch)
    assert companies.ask("Başlık", "Metin burada", conn=db) == ["BHP", "Rio Tinto"]
    job, system, prompt = fake.calls[0]
    assert job == "cheap" and "ABOUT" in system and "named only in passing" in system and "ignore them" in system
    assert "Title: Başlık" in prompt and "Metin burada" in prompt


def test_an_unusable_answer_is_asked_once_more_then_gives_up(db, monkeypatch):
    fake = FakeAI(lambda *a: "not a list").install(monkeypatch)
    with pytest.raises(ValueError):
        companies.extract("t", "text", conn=db)
    assert len(fake.calls) == 2


def test_fill_saves_the_newest_first_skips_cut_posts_and_never_asks_twice(db, monkeypatch):
    old = article(db, "old", day="2026-10-01T10:00:00Z")
    new = article(db, "new", day="2026-10-11T10:00:00Z")
    cut = article(db, "cut", text="", missing=1)
    done = article(db, "done", companies_=["Shell"])
    fake = model(monkeypatch)
    stats = companies.fill(db, limit=1)
    assert stats.asked == 1 and db.execute("SELECT companies FROM articles WHERE id = ?", (cut + 0,)).fetchone()[0] is None
    got = dict(db.execute("SELECT id, companies FROM articles").fetchall())
    assert got[cut] is None and got[done] == '["Shell"]'
    assert sum(v is not None for k, v in got.items() if k in (old, new)) == 1 and got[cut] is None      # one of the two, the newest id first
    companies.fill(db)
    assert all(v is not None for k, v in dict(db.execute("SELECT id, companies FROM articles").fetchall()).items() if k != cut)
    before = len(fake.calls)
    assert companies.fill(db).asked == 0 and len(fake.calls) == before


def test_one_post_that_cannot_be_answered_does_not_stop_the_others(db, monkeypatch):
    a = article(db, "a")
    b = article(db, "b")
    answers = iter(["junk", "junk", '["BHP"]'])
    FakeAI(lambda *x: next(answers)).install(monkeypatch)
    stats = companies.fill(db)
    got = dict(db.execute("SELECT id, companies FROM articles").fetchall())
    assert stats.asked == 1 and stats.failed == 1 and sorted(v for v in got.values() if v) == ['["BHP"]']      # the unusable one stays NULL


def test_no_budget_stops_the_run_and_leaves_the_rest_for_next_time(db, monkeypatch):
    article(db, "a")
    article(db, "b")
    def boom(*a, **k):
        raise ai.AIError("monthly limit reached")
    monkeypatch.setattr(ai, "call", boom)
    stats = companies.fill(db)
    assert stats.asked == 0 and "stopped" in stats.note
    assert db.execute("SELECT count(*) FROM articles WHERE companies IS NULL").fetchone()[0] == 2


def test_the_trial_prints_and_saves_nothing(db, monkeypatch):
    article(db, "a", text="BHP ve Rio Tinto bakır üretimini kıstı. " * 4)
    model(monkeypatch)
    text = companies.trial(db, 5)
    assert "BHP, Rio Tinto" in text and "1 of 1 posts name at least one company" in text
    assert db.execute("SELECT companies FROM articles").fetchone()[0] is None


def test_names_from_the_text_are_classified_like_tags_and_the_counter_counts_them(db, monkeypatch):
    for i in range(3):
        article(db, f"p{i}", tags_=("Bakır",), companies_=["BHP", "Saudi Aramco"])
    db.execute("INSERT INTO tags (tag, kind, maps_to, source, created_at) VALUES ('Bakır', 'commodity', 'copper', 'user', 'x')")
    db.commit()
    assert tags.new_tags(db, 10) == ["BHP", "Saudi Aramco"]
    model(monkeypatch)
    stats = tags.classify_new(db, seclist=tags.SecList(lambda: [[1, "BHP Group Ltd", "BHP", "NYSE"]]))
    assert stats.classified == 2 and tags.new_tags(db, 10) == []
    assert db.execute("SELECT kind, maps_to, us_listed, status FROM tags WHERE tag = 'BHP'").fetchone() == ("company", "BHP", 1, "confirmed")
    result = count.count(db, NOW, write=False)
    stock = {e.key: e for e in result.of("stock")}
    non_us = {e.key: e for e in result.of("non_us")}
    assert stock["BHP"].posts_7d == 3 and non_us["2222.SR"].posts_7d == 3 and {e.key for e in result.of("commodity")} == {"copper"}


def test_a_post_is_counted_once_even_if_its_tag_and_its_text_name_the_same_company(db):
    db.execute("INSERT INTO tags (tag, kind, maps_to, us_listed, source, created_at) VALUES ('BHP', 'company', 'BHP', 1, 'ai', 'x'), "
               "('BHP Group', 'company', 'BHP', 1, 'ai', 'x')")
    article(db, "a", tags_=("BHP",), companies_=["BHP Group", "BHP"])
    db.commit()
    assert {e.key: e.posts_7d for e in count.count(db, NOW, write=False).of("stock")} == {"BHP": 1}


def test_the_pass_asks_for_companies_only_when_the_setting_is_on(db, monkeypatch):
    article(db, "a", companies_=None)
    db.execute("UPDATE articles SET sentence = 'done'")
    db.commit()
    fake = model(monkeypatch)
    settings = dict(config.settings())
    monkeypatch.setattr(config, "settings", lambda: dict(settings, eye=dict(settings.get("eye") or {}, extract_companies=False)))
    result = run.Result()
    run.after_reading(db, result, seclist=tags.SecList(lambda: []))
    assert result.companies_asked == 0 and db.execute("SELECT companies FROM articles").fetchone()[0] is None
    monkeypatch.setattr(config, "settings", lambda: dict(settings, eye=dict(settings.get("eye") or {}, extract_companies=True)))
    result = run.Result()
    run.after_reading(db, result, seclist=tags.SecList(lambda: [[1, "BHP Group Ltd", "BHP", "NYSE"]]))
    assert result.companies_asked == 1 and db.execute("SELECT companies FROM articles").fetchone()[0] == '["BHP", "Rio Tinto"]'
    assert db.execute("SELECT count(*) FROM tags WHERE tag IN ('BHP', 'Rio Tinto')").fetchone()[0] == 2     # classified in the same pass


def test_classify_catches_up_the_names_found_by_fill(db, monkeypatch, capsys):
    for i in range(3):
        article(db, f"p{i}", companies_=["BHP", "Saudi Aramco"])
    model(monkeypatch)
    from shared import db as dbmod

    class Keep:                                     # the command closes its connection; the test database must stay open
        def __getattr__(self, name):
            return (lambda: None) if name == "close" else getattr(db, name)

    real = tags.SecList
    monkeypatch.setattr(dbmod, "connect", lambda *a, **k: Keep())
    monkeypatch.setattr(tags, "SecList", lambda *a, **k: real(lambda: [[1, "BHP Group Ltd", "BHP", "NYSE"]]))
    assert companies.classify() == 0
    assert "3 names classified" in capsys.readouterr().out
    assert db.execute("SELECT count(*) FROM tags WHERE tag IN ('BHP', 'Saudi Aramco')").fetchone()[0] == 2


def test_refresh_classifies_then_counts(monkeypatch):
    from agents.counter import __main__ as counter_cli
    order = []
    monkeypatch.setattr(companies, "classify", lambda rounds=10: order.append("classify") or 0)
    monkeypatch.setattr(counter_cli, "main", lambda argv=None: order.append(("count", argv)) or 0)
    assert companies.main(["--refresh"]) == 0 and order == ["classify", ("count", [])]


def test_the_codex_cases_curly_apostrophe_joined_names_and_look_alike_names():
    # codex test of 2026-10-30: "Glencore’un" (a curly apostrophe) and "ExxonMobil" were missed; Tata Motors / Rio de Janeiro passed wrongly
    yes = [("Glencore", "Glencore’un üretimi arttı"), ("Glencore", "Glencore'un üretimi arttı"), ("Exxon Mobil", "ExxonMobil kârı arttı"),
           ("Tata Steel", "Tata Steel fiyatları artırdı"), ("Rio Tinto", "Rio Tinto sevkiyatı arttı"), ("Saudi Aramco", "Aramco'nun kârı"),
           ("Kyushu Electric Power", "Kyushu Electric 12 LNG kargosu alacak"), ("Fortum", "Fortum’un nükleer geliri"), ("Anglo American", "Anglo American üretimi")]
    no = [("Tata Steel", "Tata Motors satışları arttı"), ("Rio Tinto", "Rio de Janeiro limanı"), ("Rio Tinto", "Tinto Group'un geliri"),
          ("Meta", "metal fiyatları"), ("Anglo American", "American Airlines yükseldi"), ("Glencore", "Antamina durdu")]
    for name, text in yes:
        assert companies.named_in(name, "t", text), (name, text)
    for name, text in no:
        assert not companies.named_in(name, "t", text), (name, text)


def test_the_prompt_leaves_out_companies_named_only_in_a_price_quote():
    assert "Platts window" in companies.SYSTEM and "named in passing" in companies.SYSTEM
