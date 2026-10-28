"""shared/bulletin/translate: the cheap model's Turkish text, kept only when its numbers are the English item's."""

import json

from shared.ai.fake import FakeAI
from shared.bulletin import translate
from shared.bulletin.write import Draft, Item


def draft():
    return Draft(items=[Item("macro", "Brent rose 3.1% to $115.20.", ("W1",)),
                        Item("interests", "SK Hynix Q3 revenue 104.6 trillion won (expected 98.6).", ("P1",), group="ai_infrastructure"),
                        Item("stocks", "KO raised prices 4%.", ("P2",), ticker="KO")])


def test_good_translations_are_kept_and_the_call_is_cheap(db, monkeypatch):
    answer = {"0": "Brent %3,1 artarak 115,20 $'a yükseldi.", "1": "SK Hynix 3. çeyrek cirosu 104,6 trilyon won (beklenti 98,6).",
              "2": "KO fiyatları %4 artırdı."}
    fake = FakeAI(lambda job, system, prompt: answer).install(monkeypatch)
    out = translate.translate(draft(), conn=db)
    assert [i.turkish for i in out.items] == list(answer.values()) and all(i.turkish_flag is None for i in out.items)
    assert [c[0] for c in fake.calls] == ["cheap"]
    assert json.loads(fake.calls[0][2]) == {"0": "Brent rose 3.1% to $115.20.", "1": "SK Hynix Q3 revenue 104.6 trillion won (expected 98.6).",
                                           "2": "KO raised prices 4%."}


def test_a_translation_with_other_numbers_or_none_is_flagged(db, monkeypatch):
    answer = {"0": "Brent %3,1 artarak 125,20 $'a yükseldi.", "1": "  "}                     # a number changed · empty · key 2 missing
    FakeAI(lambda *a: answer).install(monkeypatch)
    out = translate.translate(draft(), conn=db)
    assert [(i.turkish, i.turkish_flag) for i in out.items] == [
        (None, "çeviri kontrolü: rakamlar uyuşmuyor"), (None, "çeviri eksik"), (None, "çeviri eksik")]
    assert any("changed its numbers: Brent rose" in n for n in out.notes)


def test_a_model_that_fails_leaves_english_items_and_a_note(db, monkeypatch):
    FakeAI(lambda *a: "no json at all").install(monkeypatch)
    out = translate.translate(draft(), conn=db)
    assert all(i.turkish is None and i.turkish_flag == "çeviri yapılamadı" for i in out.items)
    assert out.notes[0].startswith("Translation failed (ValueError")


def test_every_provider_failing_is_not_an_exception(db, monkeypatch):
    fake = FakeAI(lambda *a: "x")
    fake.fail = {"deepseek", "openai", "anthropic", "openrouter"}
    fake.install(monkeypatch)
    out = translate.translate(draft(), conn=db)
    assert out.notes[0].startswith("Translation failed (AIError") and out.items[0].turkish_flag == "çeviri yapılamadı"


def test_an_empty_draft_calls_nothing(db, monkeypatch):
    fake = FakeAI(lambda *a: {}).install(monkeypatch)
    translate.translate(Draft(), conn=db)
    assert fake.calls == []
