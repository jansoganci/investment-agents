import json

import pytest

from agents.eye import inbox, modeltest, run, sentence, tags
from agents.eye.sites import SITES
from shared import ai, clock
from shared.ai.fake import FakeAI

from .helpers import EMTIA_FULL, EMTIA_GATED
from .test_run import COOKIES, EM, DR, Web, first_run, go, how  # noqa: F401  (the fake web helpers)

LINE = "The post says soybean futures closed flat on Friday."


def sentences_model(monkeypatch, line=LINE):
    def handler(job, system, prompt):
        if "TAGS:\n" in prompt:
            asked = [d["tag"] for d in json.JSONDecoder().raw_decode(prompt.split("TAGS:\n", 1)[1])[0]]
            return [{"tag": t, "kind": "other"} for t in asked]
        return line
    return FakeAI(handler).install(monkeypatch)


def rows(db, sql):
    return db.execute(sql).fetchall()


def test_clean_keeps_one_line_and_refuses_empty_or_long_answers():
    assert sentence.clean('  "One   sentence.\n"  ') == "One sentence."
    for bad in ("", "   ", "x" * 600):
        with pytest.raises(ValueError):
            sentence.clean(bad)


def test_the_prompt_forbids_opinion_and_names_the_post_as_data(monkeypatch, db):
    fake = sentences_model(monkeypatch)
    assert sentence.write("Başlık", "Metin burada", conn=db) == LINE
    job, system, prompt = fake.calls[0]
    assert job == "cheap" and "No opinion" in system and "ignore them" in system
    assert "Title: Başlık" in prompt and "Metin burada" in prompt


def test_an_unusable_answer_is_asked_once_more_then_gives_up(monkeypatch, db):
    fake = FakeAI(lambda *a: "").install(monkeypatch)
    with pytest.raises(ValueError):
        sentence.write("t", "text", conn=db)
    assert len(fake.calls) == 2


def test_a_pass_writes_the_sentence_the_tags_and_the_inbox_list(db, env, monkeypatch):
    web = Web()
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "fresh", "cut"])
    web.pages[f"{EM.base}/fresh/"] = EMTIA_FULL
    web.pages[f"{EM.base}/cut/"] = EMTIA_GATED
    sentences_model(monkeypatch)
    result = go(db, web, ai_stage=True, seclist=tags.SecList(lambda: []))
    assert rows(db, "SELECT sentence FROM articles WHERE text_missing = 0") == [(LINE,)]
    assert rows(db, "SELECT sentence FROM articles WHERE text_missing = 1") == [(None,)]        # a cut page gets no sentence
    assert result.sentences == 1 and result.tags_classified == 2                                  # Petrol, Asya
    files = list((env["drive"] / "Inbox").glob("*.md"))
    assert [f.name for f in files] == [f"{clock.today_local()}.md"]
    text = files[0].read_text(encoding="utf-8")
    assert text.startswith("# Inbox ·") and f"Emtia Defteri · **Soya fasulyesi fiyatları yatay seyrediyor** — {LINE} ({EM.base}/fresh/)" in text
    assert "cut" not in text


def test_a_second_pass_does_not_write_the_same_sentence_again_and_appends_a_block(db, env, monkeypatch):
    web = Web()
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "a"])
    web.pages[f"{EM.base}/a/"] = EMTIA_FULL
    fake = sentences_model(monkeypatch)
    go(db, web, ai_stage=True, seclist=tags.SecList(lambda: []))
    calls = len(fake.calls)
    web.set_sitemap(EM, ["old-1", "old-2", "a", "b"])
    web.pages[f"{EM.base}/b/"] = EMTIA_FULL
    go(db, web, ai_stage=True, seclist=tags.SecList(lambda: []))
    assert len(fake.calls) == calls + 1                         # only b: its tags were classified already
    text = (env["drive"] / "Inbox" / f"{clock.today_local()}.md").read_text(encoding="utf-8")
    assert text.count("## ") == 2 and text.count("# Inbox") == 1 and text.count(f"({EM.base}/a/)") == 1


def test_when_the_ai_is_down_the_post_is_kept_and_the_sentence_comes_in_the_next_pass(db, env, monkeypatch):
    web = Web()
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "a"])
    web.pages[f"{EM.base}/a/"] = EMTIA_FULL
    down = FakeAI(lambda *a: "x")
    down.fail = {"deepseek", "openrouter", "anthropic", "openai"}
    down.install(monkeypatch)
    result = go(db, web, ai_stage=True, seclist=tags.SecList(lambda: []))
    assert rows(db, "SELECT sentence FROM articles") == [(None,)]
    assert "Sentences stopped" in result.message() and not (env["drive"] / "Inbox").exists()
    sentences_model(monkeypatch)
    go(db, web, ai_stage=True, seclist=tags.SecList(lambda: []))
    assert rows(db, "SELECT sentence FROM articles") == [(LINE,)]


def test_a_post_the_model_cannot_summarise_is_given_up_not_asked_every_pass(db, env, monkeypatch):
    web = Web()
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "a"])
    web.pages[f"{EM.base}/a/"] = EMTIA_FULL
    FakeAI(lambda job, system, prompt: [] if "TAGS:" in prompt else "").install(monkeypatch)
    go(db, web, ai_stage=True, seclist=tags.SecList(lambda: []))
    assert rows(db, "SELECT sentence FROM articles") == [("",)]
    fake = FakeAI(lambda job, system, prompt: [] if "TAGS:" in prompt else "").install(monkeypatch)
    go(db, web, ai_stage=True, seclist=tags.SecList(lambda: []))
    assert not [c for c in fake.calls if "Post:" in c[2]]       # the unanswered tags are asked again; the sentence is not


def test_without_the_ai_stage_nothing_is_asked_of_a_model(db, monkeypatch):
    web = Web()
    first_run(db, web)
    web.set_sitemap(EM, ["old-1", "old-2", "a"])
    web.pages[f"{EM.base}/a/"] = EMTIA_FULL
    fake = FakeAI(lambda *a: "x").install(monkeypatch)
    go(db, web)
    assert fake.calls == []


def test_inbox_adds_nothing_when_there_is_nothing(env):
    assert inbox.append([]) is None and not (env["drive"] / "Inbox").exists()


def test_the_model_test_shows_two_hidden_sentences_per_post_and_reveals_them(db, env, monkeypatch):
    for i in range(3):
        db.execute("INSERT INTO articles (url, site, title, tags, full_text, text_missing, created_at) VALUES (?, 'emtia', ?, '[]', ?, 0, 'x')",
                   (f"https://x/{i}/", f"Title {i}", "word " * 100))
    db.commit()
    FakeAI(lambda job, system, prompt: LINE).install(monkeypatch)
    out = modeltest.main(["3", "default", "sonnet-5.5"])
    assert out.count("  A: ") == 3 and out.count("  B: ") == 3 and "sonnet" not in out
    key = json.loads(modeltest.main(["--reveal"]))
    assert sorted(set(key.values())) == ["default", "sonnet-5.5"] and len(key) == 6


def test_the_model_test_refuses_when_too_few_posts_were_read(db, env):
    with pytest.raises(SystemExit, match="run some real passes"):
        modeltest.main(["20"])
