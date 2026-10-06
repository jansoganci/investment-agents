"""Warning codes stay the same from entry to entry (U1 stays U1); a closed warning stays closed (roadmap, /closewarning)."""

import pytest

from agents.analysis import ai as parts
from agents.analysis import card, run
from shared import drive
from shared.ai.fake import FakeAI
from tests.analysis.test_ai_parts import handler
from tests.fixtures.loader import FixtureSources


def test_the_key_of_a_warning_ignores_its_numbers():
    a = card.flag_key({"flag": "data_check", "detail": "debt 8.5 → 33.4 bn (2026)"})
    b = card.flag_key({"flag": "data_check", "detail": "debt 9.1 → 12.0 bn (2026)"})
    assert a == b == "data_check:debt # bn (2026)"
    assert card.flag_key({"flag": "data_check", "detail": "debt dropped to zero (2025)"}) != a


def entry(day, warnings):
    import yaml
    for w, k in zip(warnings, card._keys(warnings, "name")):
        w.setdefault("key", k)
    return (f"## {day} · fundamental · agent_3 · x\n```yaml\n" + yaml.safe_dump({"warnings": warnings}) + "```\n### Summary\ns\n")


def test_codes_are_reused_and_new_conditions_get_the_next_number():
    text = "# T\n\n" + entry("2026-10-06", [
        {"code": "U1", "name": "data_check", "detail": "debt 8.5 → 33.4 bn (2026)"},
        {"code": "U2", "name": "one_off", "detail": "gain 9.6 bn"}])
    flags = [{"flag": "one_off", "detail": "gain 7.1 bn"}, {"flag": "data_check", "detail": "debt 9 → 40 bn (2026)"},
             {"flag": "data_check", "detail": "share count jump ×10"}]
    codes, closed = card.assign_codes(text, flags)
    assert codes == ["U2", "U1", "U3"] and closed == set()
    assert card.assign_codes(None, flags)[0] == ["U1", "U2", "U3"]  # a card with no history starts at U1


def test_two_flags_with_the_same_shape_get_two_codes():
    flags = [{"flag": "one_off", "detail": "gain 9.6 bn"}, {"flag": "one_off", "detail": "gain 1.1 bn"}]
    first, _ = card.assign_codes(None, flags)
    assert first == ["U1", "U2"]
    text = "# T\n\n" + entry("2026-10-06", [{"code": c, "name": f["flag"], "detail": f["detail"]} for c, f in zip(first, flags)])
    assert card.assign_codes(text, flags)[0] == ["U1", "U2"]


def test_closing_and_reopening_a_warning():
    text = "# T\n\n" + card.note_entry("2026-10-08", "Warning U1 closed: one-off tax deposit, not recurring.")
    assert card.closed_warnings(text) == {"U1"}
    text += "\n" + card.note_entry("2026-10-09", "Warning U1 reopened — change #7 withdrawn (/undo).")
    assert card.closed_warnings(text) == set()
    assert card.closed_warnings("# T\n\n" + card.note_entry("2026-10-08", "Warning U1 closed: x", who="agent_3")) == set()  # only mine


@pytest.fixture
def src():
    return FixtureSources()


def test_the_codes_stay_the_same_across_analyses_and_a_closed_warning_is_not_asked_again(db, env, src, monkeypatch):
    FakeAI(handler()).install(monkeypatch)
    run.analyze(db, "NVDA", src, today="2026-10-06", use_ai=True)
    run.analyze(db, "NVDA", src, today="2026-10-13", use_ai=True)
    first, second = [card._yaml_of(e["body"])["warnings"] for e in card.entries(drive.find_card("NVDA").read_text())
                     if e["record"] == "fundamental"]
    assert [w["code"] for w in first] == [w["code"] for w in second] == ["U1", "U2", "U3", "U4"][:len(first)]
    assert all(w["flag_status"] == "open" for w in second)

    path = drive.find_card("NVDA")
    card.append(path, card.note_entry("2026-10-14", "Warning U3 closed: the 25 bn bond is known and covered."), {})
    seen = {}

    def spy(job, system, prompt):
        if system.startswith("You help a long-term"):
            seen["ids"] = [i["id"] for i in __import__("tests.analysis.test_ai_parts", fromlist=["items_in"]).items_in(prompt)]
        return handler()(job, system, prompt)
    FakeAI(spy).install(monkeypatch)
    out = run.analyze(db, "NVDA", src, today="2026-10-20", use_ai=True)
    third = [card._yaml_of(e["body"])["warnings"] for e in card.entries(path.read_text()) if e["record"] == "fundamental"][-1]
    assert {w["code"]: w["flag_status"] for w in third}["U3"] == "closed" and "U3" not in seen["ids"]
    assert "closed by me stay closed" in out.text


def test_a_debt_jump_in_a_new_year_is_a_new_warning_even_if_the_old_one_is_closed():
    text = ("# T\n\n" + entry("2026-10-06", [{"code": "U1", "name": "data_check", "detail": "debt 8.5 → 33.4 bn (2026)"}])
            + "\n" + card.note_entry("2026-10-08", "Warning U1 closed: the 25 bn bond is known."))
    codes, closed = card.assign_codes(text, [{"flag": "data_check", "detail": "debt 33.4 → 60.0 bn (2029)"}])
    assert codes == ["U2"] and closed == {"U1"}  # U2 is open: the closed U1 does not hide it
    assert card.assign_codes(text, [{"flag": "data_check", "detail": "debt 9 → 34 bn (2026)"}])[0] == ["U1"]  # the same one is U1


def test_warnings_of_one_shape_keep_their_codes_when_one_of_them_disappears():
    two = [{"flag": "one_off", "detail": "gain 9.6 bn"}, {"flag": "one_off", "detail": "gain 1.1 bn"}]
    text = "# T\n\n" + entry("2026-10-06", [{"code": "U1", "name": "one_off", "detail": two[0]["detail"]},
                                              {"code": "U2", "name": "one_off", "detail": two[1]["detail"]}])
    # the first one is gone; the second must stay U2, not slide onto U1 and inherit a closed state
    assert card.assign_codes(text, [two[1]])[0] == ["U2"]
    assert card.assign_codes(text, [two[0]])[0] == ["U1"]


def test_codes_written_by_phase_1_are_not_trusted():
    import yaml
    old = ("## 2026-10-05 · fundamental · agent_3 · x\n```yaml\n"
           + yaml.safe_dump({"warnings": [{"code": "U1", "name": "data_check", "detail": "debt 8.5 → 33.4 bn (2026)"},
                                          {"code": "U2", "name": "one_off", "detail": "gain 9.6 bn"}]}) + "```\n### Summary\ns\n")
    text = "# T\n\n" + old + "\n" + card.note_entry("2026-10-06", "Warning U1 closed: old.")
    codes, closed = card.assign_codes(text, [{"flag": "one_off", "detail": "gain 9.6 bn"}])
    assert codes == ["U3"] and closed == {"U1"}  # a fresh code after the old numbers; the old U1 closes nothing new
