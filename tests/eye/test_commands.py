import json

import pytest

from shared import commands, sec
from shared.commands import Refused

CMD = commands.REGISTRY


def add_tag(db, tag, kind="company", maps_to=None, status="waiting", note="n", us_listed=1):
    db.execute("INSERT INTO tags (tag, kind, maps_to, source, status, us_listed, note, created_at) VALUES (?, ?, ?, 'ai', ?, ?, ?, 'x')",
               (tag, kind, maps_to, status, us_listed, note))
    db.commit()


def say(*words, yes=False):
    code, text = commands.run([*words, *(["--yes"] if yes else [])])
    return code, text


def tag_row(db, tag):
    cur = db.execute("SELECT kind, maps_to, exchange, status, source, us_listed, note FROM tags WHERE tag = ?", (tag,))
    return cur.fetchone()


@pytest.fixture
def lookup(monkeypatch):
    known = {"CMI": {"cik": "0000026172", "name": "CUMMINS INC", "ticker": "CMI", "exchange": "NYSE", "all_tickers": ["CMI"]}}
    monkeypatch.setattr(sec, "lookup", lambda t: known.get(t.upper()))


def test_both_commands_are_built_and_in_the_menu():
    assert CMD["tag"].built and CMD["subsector"].built
    assert "tag" in commands.MENU and "subsector" in commands.MENU


def test_tag_alone_lists_the_tags_that_wait(db, env):
    add_tag(db, "Cummins", note="SEC does not know the ticker ZZZ")
    add_tag(db, "Bakır", kind="commodity", status="confirmed", note=None)
    code, text = say("tag")
    assert code == 0 and "1 wait for me (2 mapped)" in text and "Cummins: SEC does not know the ticker ZZZ" in text


def test_a_us_company_is_confirmed_after_the_sec_knows_the_ticker(db, env, lookup):
    add_tag(db, "Cummins")
    code, text = say("tag", "Cummins", "company", "CMI")
    assert code == 0 and "CONFIRM" in text and "company CMI (NYSE)" in text and tag_row(db, "Cummins")[3] == "waiting"
    code, text = say("tag", "Cummins", "company", "CMI", yes=True)
    assert "DONE · change #" in text
    assert tag_row(db, "Cummins") == ("company", "CMI", "NYSE", "confirmed", "user", 1, None)


def test_a_ticker_the_sec_does_not_know_is_refused_with_the_way_out(db, env, lookup):
    add_tag(db, "Zhongkuang Resources")
    code, text = say("tag", "Zhongkuang", "Resources", "company", "ZZZ")
    assert code == 1 and "SEC does not know the ticker ZZZ" in text and "company non-us" in text


def test_a_company_not_listed_in_the_us_needs_no_sec(db, env, monkeypatch):
    monkeypatch.setattr(sec, "lookup", lambda t: pytest.fail("SEC must not be asked"))
    add_tag(db, "Zhongkuang Resources")
    say("tag", "Zhongkuang", "Resources", "company", "non-us", yes=True)
    assert tag_row(db, "Zhongkuang Resources") == ("company", None, None, "confirmed", "user", 0, None)


def test_commodity_sector_region_other(db, env):
    for name in ("Petrol", "Yazılım ve İnternet", "Japonya", "Rapor Özetleri"):
        add_tag(db, name, kind="other", status="confirmed", us_listed=None)
    say("tag", "Petrol", "commodity", "Crude", "Oil", yes=True)
    say("tag", "Yazılım", "ve", "İnternet", "sector", "information technology", yes=True)
    say("tag", "Japonya", "region", yes=True)
    say("tag", "Rapor", "Özetleri", "other", yes=True)
    assert tag_row(db, "Petrol")[:2] == ("commodity", "crude oil")
    assert tag_row(db, "Yazılım ve İnternet")[:2] == ("sector", "Information Technology")
    assert tag_row(db, "Japonya")[0] == "region" and tag_row(db, "Rapor Özetleri")[0] == "other"


@pytest.mark.parametrize("args, why", [
    (["Cummins"], "usage"),
    (["Cummins", "company"], "needs a ticker"),
    (["Cummins", "commodity"], "needs its name"),
    (["Cummins", "sector", "Fossil"], "must be one of"),
    (["Cummins", "region", "Asia"], "takes no value"),
    (["Unknown", "tag"], "usage"),
    (["Nobody", "region"], "No post has the tag"),
])
def test_bad_input_is_refused_and_changes_nothing(db, env, lookup, args, why):
    add_tag(db, "Cummins")
    code, text = say("tag", *args)
    assert code == 1 and why in text and tag_row(db, "Cummins")[3] == "waiting"


def test_the_name_may_differ_in_case_but_two_matches_are_refused(db, env):
    add_tag(db, "Cummins")
    assert say("tag", "cummins", "region")[0] == 0
    add_tag(db, "CUMMINS", kind="other")
    assert "matches 2 tags" in say("tag", "cUmMiNs", "region")[1]


def test_undo_puts_the_earlier_mapping_back(db, env, lookup):
    add_tag(db, "Cummins")
    before = tag_row(db, "Cummins")
    code, text = say("tag", "Cummins", "company", "CMI", yes=True)
    number = int(text.split("#")[1].split()[0])
    assert "To cancel it: /undo" in text
    code, text = say("undo", str(number), yes=True)
    assert code == 0 and "Cancelled" in text
    assert tag_row(db, "Cummins") == before


def test_subsector_add_list_undo_and_comes_back(db, env):
    assert "approved list is empty" in say("subsector")[1]
    code, text = say("subsector", "add", "Energy", "Uranium", yes=True)
    assert "Subsector 'Uranium' added under Energy" in text
    number = int(text.split("#")[1].split()[0])
    say("subsector", "add", "Health", "Care", "Medical", "Devices", yes=True)
    listing = say("subsector")[1]
    assert "Energy: Uranium" in listing and "Health Care: Medical Devices" in listing
    assert "already on the list" in say("subsector", "add", "Energy", "uranium")[1]
    say("undo", str(number), yes=True)
    assert "Energy: Uranium" not in say("subsector")[1]
    assert db.execute("SELECT void FROM subsectors WHERE name = 'Uranium'").fetchone() == (1,)      # marked, not deleted
    say("subsector", "add", "Energy", "Uranium", yes=True)
    assert "Energy: Uranium" in say("subsector")[1]
    assert db.execute("SELECT count(*) FROM subsectors WHERE name = 'Uranium'").fetchone() == (1,)


@pytest.mark.parametrize("args", [["add"], ["add", "Energy"], ["add", "Mining", "Gold"], ["remove", "Energy", "X"]])
def test_subsector_bad_input_is_refused(db, env, args):
    code, text = say("subsector", *args)
    assert code == 1 and ("usage" in text.lower() or "GICS" in text)


def test_an_approved_subsector_reaches_the_classifier(db, env, monkeypatch):
    from agents.eye import tags
    from shared.ai.fake import FakeAI
    say("subsector", "add", "Energy", "Uranium", yes=True)
    db.execute("INSERT INTO articles (url, site, title, tags, full_text, created_at) VALUES ('https://x/1/', 'emtia', 't', ?, 'x', 'x')",
               (json.dumps(["Uranyum"]),))
    db.commit()
    fake = FakeAI(lambda job, system, prompt: [{"tag": "Uranyum", "kind": "sector", "sector": "Energy", "subsector": "Uranium"}]).install(monkeypatch)
    tags.classify_new(db, seclist=tags.SecList(lambda: []))
    assert '"Uranium"' in fake.calls[0][2]
    assert db.execute("SELECT subsector FROM tags WHERE tag = 'Uranyum'").fetchone() == ("Uranium",)
