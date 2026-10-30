import json

import pytest

from agents.eye import tags
from shared import ai
from shared.ai.fake import FakeAI

SEC_ROWS = [
    [26172, "CUMMINS INC", "CMI", "NYSE"],
    [1090727, "UNITED PARCEL SERVICE INC", "UPS", "NYSE"],
    [1577552, "Alibaba Group Holding Ltd", "BABA", "NYSE"],
    [2000, "Standard Motor Products Inc", "SMP", "NYSE"],
    [34088, "EXXON MOBIL CORP", "XOM", "NYSE"],
]


@pytest.fixture
def seclist():
    return tags.SecList(lambda: SEC_ROWS)


def item(tag, kind, **kw):
    return {"tag": tag, "kind": kind, **kw}


def test_names_close_ignores_legal_words_case_and_turkish_letters():
    assert tags.names_close("Cummins", "CUMMINS INC")
    assert tags.names_close("Alibaba", "Alibaba Group Holding Ltd")
    assert tags.names_close("Exxon", "EXXON MOBIL CORP")                 # one extra word is allowed
    assert tags.names_close("Estée Lauder", "ESTEE LAUDER COMPANIES INC")
    assert not tags.names_close("Standard", "Standard Motor Products Inc")   # two extra words are not
    assert not tags.names_close("Standard Oil", "EXXON MOBIL CORP")
    assert not tags.names_close("", "CUMMINS INC")


def test_a_us_listed_company_that_passes_the_sec_check_is_confirmed(seclist):
    row = tags.decide(item("Cummins", "company", ticker="cmi", us_listed=True, name="Cummins Inc.", exchange="NASDAQ"), set(), seclist)
    assert (row["status"], row["maps_to"], row["exchange"], row["us_listed"]) == ("confirmed", "CMI", "NYSE", 1)


def test_an_adr_is_checked_like_any_us_listed_company(seclist):
    row = tags.decide(item("Alibaba", "company", ticker="BABA", us_listed=True), set(), seclist)
    assert row["status"] == "confirmed" and row["maps_to"] == "BABA"


def test_the_models_own_name_for_the_company_cannot_confirm_a_wrong_ticker(seclist):
    """Audit 2026-10-14, #20: tag "Standard", the model says SMP and calls it 'Standard Motor Products Inc': the SEC name matches the
    model's name, but not the tag's own text, so the company waits for my /tag instead of being confirmed by the model's own words."""
    row = tags.decide(item("Standard", "company", ticker="SMP", us_listed=True, name="Standard Motor Products Inc"), set(), seclist)
    assert row["status"] == "waiting" and "not close" in row["note"]


@pytest.mark.parametrize("answer, why", [
    (dict(ticker="ZZZZ", us_listed=True), "SEC does not know the ticker ZZZZ"),
    (dict(ticker=None, us_listed=True), "gave no ticker"),
    (dict(ticker="SMP", us_listed=True), "not close"),
    (dict(ticker="CMI", us_listed=None), "could not say whether"),
])
def test_a_us_looking_company_that_fails_the_check_waits_with_the_reason(seclist, answer, why):
    tag = "Standard" if answer.get("ticker") == "SMP" else "Cummins"
    row = tags.decide(item(tag, "company", **answer), set(), seclist)
    assert row["status"] == "waiting" and why in row["note"]


def test_a_company_not_listed_in_the_us_gets_no_sec_check_and_no_question():
    class Nobody:
        def find(self, ticker):
            raise AssertionError("SEC must not be asked for a company that is not listed in the US")

    row = tags.decide(item("Zhongkuang Resources", "company", ticker="1164.HK", us_listed=False, exchange="HKEX", country="China"),
                      set(), Nobody())
    assert (row["status"], row["maps_to"], row["us_listed"], row["exchange"], row["country"]) == ("confirmed", "1164.HK", 0, "HKEX", "China")


def test_other_kinds_commodity_sector_region_other(seclist):
    assert tags.decide(item("Bakır", "commodity", commodity="Copper "), set(), seclist)["maps_to"] == "copper"
    row = tags.decide(item("Yazılım ve İnternet", "sector", sector="Information Technology", subsector="Software"), {"Software"}, seclist)
    assert (row["kind"], row["maps_to"], row["subsector"]) == ("sector", "Information Technology", "Software")
    assert tags.decide(item("X", "sector", sector="Fossil"), set(), seclist)["kind"] == "other"      # not a GICS sector
    assert tags.decide(item("Japonya", "region"), set(), seclist)["status"] == "confirmed"
    assert tags.decide(item("Rapor Özetleri", "other"), set(), seclist)["kind"] == "other"


def test_a_subsector_must_be_on_the_approved_list_or_other(seclist):
    approved = {"Software"}
    assert tags.decide(item("A", "sector", sector="Energy", subsector="Invented"), approved, seclist)["subsector"] is None
    assert tags.decide(item("A", "sector", sector="Energy", subsector="other"), approved, seclist)["subsector"] == "other"


def article(db, title, tag_list, n=[0]):
    n[0] += 1
    db.execute("INSERT INTO articles (url, site, title, tags, full_text, created_at) VALUES (?, 'emtia', ?, ?, 'text', '2026-10-11T00:00:00Z')",
               (f"https://x/{n[0]}/", title, json.dumps(tag_list, ensure_ascii=False)))
    db.commit()


def asked_tags(prompt):
    """The tags in a request (the retry text after the JSON is ignored)."""
    return [d["tag"] for d in json.JSONDecoder().raw_decode(prompt.split("TAGS:\n", 1)[1])[0]]


def model(prompt_to_answers):
    def handler(job, system, prompt):
        return prompt_to_answers(asked_tags(prompt))
    return handler


def test_new_tags_are_classified_once_with_the_posts_context(db, monkeypatch, seclist):
    article(db, "Cummins data center engines", ["Cummins", "Amerika Hisseleri", "Rapor Özetleri"])
    article(db, "Copper stocks", ["Bakır", "Rapor Özetleri"])
    answers = {"Cummins": item("Cummins", "company", ticker="CMI", us_listed=True, name="Cummins Inc"),
               "Amerika Hisseleri": item("Amerika Hisseleri", "region"),
               "Rapor Özetleri": item("Rapor Özetleri", "other"),
               "Bakır": item("Bakır", "commodity", commodity="copper")}
    fake = FakeAI(model(lambda asked: [answers[t] for t in asked])).install(monkeypatch)
    stats = tags.classify_new(db, seclist=seclist)
    assert stats.classified == 4 and stats.waiting == 0
    assert dict(db.execute("SELECT tag, kind FROM tags").fetchall()) == {
        "Cummins": "company", "Amerika Hisseleri": "region", "Rapor Özetleri": "other", "Bakır": "commodity"}
    assert len(fake.calls) == 1 and fake.calls[0][0] == "cheap"
    assert "Cummins data center engines" in fake.calls[0][2]            # the post title is sent as context
    again = FakeAI(lambda *a: pytest.fail("a known tag must not be asked again")).install(monkeypatch)
    assert tags.classify_new(db, seclist=seclist).classified == 0 and again.calls == []


def test_tags_go_in_batches_and_a_bad_answer_is_asked_once_more(db, monkeypatch, seclist):
    article(db, "t", [f"tag{i}" for i in range(25)])
    replies = iter(["not json at all"])

    def handler(job, system, prompt):
        first = next(replies, None)
        if first:
            return first
        return [item(t, "other") for t in asked_tags(prompt)]

    fake = FakeAI(handler).install(monkeypatch)
    stats = tags.classify_new(db, seclist=seclist)
    assert stats.classified == 25 and len(fake.calls) == 5             # 25 names in batches of 8 = 4 batches; batch 1 twice (the first answer was unusable)
    assert "could not be used" in fake.calls[1][2]


def test_a_tag_the_model_skips_stays_unclassified_for_the_next_pass(db, monkeypatch, seclist):
    article(db, "t", ["A", "B"])
    FakeAI(model(lambda asked: [item("A", "other")])).install(monkeypatch)
    assert tags.classify_new(db, seclist=seclist).classified == 1
    assert tags.new_tags(db, 10) == ["B"]


def test_an_ai_failure_is_a_note_not_a_crash_and_nothing_is_saved(db, monkeypatch, seclist):
    article(db, "t", ["A"])
    fake = FakeAI(lambda *a: "x")
    fake.fail = {"deepseek", "openrouter", "anthropic", "openai"}
    fake.install(monkeypatch)
    stats = tags.classify_new(db, seclist=seclist)
    assert "not classified now" in stats.note and db.execute("SELECT count(*) FROM tags").fetchone()[0] == 0


def test_sec_list_is_loaded_once():
    calls = []
    lst = tags.SecList(lambda: calls.append(1) or SEC_ROWS)
    lst.find("CMI"), lst.find("UPS"), lst.find("nope")
    assert len(calls) == 1 and lst.find("cmi")["name"] == "CUMMINS INC"


def test_the_sec_list_is_fetched_before_any_tag_row_is_written_and_a_failure_leaves_the_tags_for_the_next_pass(db, monkeypatch):
    """Audit 2026-10-14, #12: SEC is never asked while a write is open, and any failure of the list (a timeout too) only waits."""
    article(db, "t", ["Cummins", "Bakır"])
    answers = {"Cummins": item("Cummins", "company", ticker="CMI", us_listed=True), "Bakır": item("Bakır", "commodity", commodity="copper")}
    FakeAI(model(lambda asked: [answers[t] for t in asked])).install(monkeypatch)
    seen = {}

    def loader():
        seen["in_transaction"] = db.in_transaction          # nothing of this batch may be half-written when SEC is asked
        raise TimeoutError("SEC is slow")
    stats = tags.classify_new(db, seclist=tags.SecList(loader))
    assert seen["in_transaction"] is False and "SEC could not be asked" in stats.note and "TimeoutError" in stats.note
    assert db.execute("SELECT count(*) FROM tags").fetchone()[0] == 0 and tags.new_tags(db, 10) == ["Cummins", "Bakır"]


def test_a_batch_cut_at_the_token_limit_is_skipped_and_the_next_one_goes_on(db, monkeypatch, seclist):
    article(db, "t", [f"tag{i}" for i in range(12)])
    first = [True]

    def handler(job, system, prompt):
        if first[0]:
            first[0] = False
            raise ai.AIError("cut", outcomes=("cut",))
        return [item(t, "other") for t in asked_tags(prompt)]

    monkeypatch.setattr(ai, "call", lambda job, prompt, **k: type("R", (), {"text": json.dumps(handler(job, k.get("system"), prompt))})())
    stats = tags.classify_new(db, seclist=seclist)
    assert stats.classified == 4 and "not classified now" in stats.note              # batch 1 (8 names) skipped, batch 2 (4 names) done
    assert len(tags.new_tags(db, 50)) == 8
