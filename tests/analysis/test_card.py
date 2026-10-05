"""The card writer (roadmap section 3, "Card format"): header updated only by code, entries appended, nothing deleted."""

import yaml

from agents.analysis import card
from agents.analysis.measures import Market, analyse
from shared.sec.facts import Facts
from tests.fixtures.loader import sec_facts, sec_submissions

STOCK = {"ticker": "KO", "company": "Coca Cola Co", "exchange": "NYSE", "country": "US", "sector": "Consumer Staples",
         "subsector": None, "status": "watching", "in_portfolio": "no", "lynch_type": None, "grade": None,
         "last_entry": None, "opened": "2026-10-05"}
SOURCE = {"report": "10-K", "period_end": "2025-12-31", "url": "https://www.sec.gov/x", "as_of": "2026-10-05",
          "filing": "0000021344-26-000010", "label": "2025 annual (10-K)"}


def ko():
    return analyse(Facts(sec_facts("KO"), sec_submissions("KO"), quarters=False), "KO", Market(splits=[]))


def test_new_card_has_the_header_and_the_title():
    text = card.new_card(STOCK)
    head, _ = card.split(text)
    assert head["ticker"] == "KO" and head["publish"] == "no" and head["opened"] == "2026-10-05"
    assert "# Coca Cola Co (KO)" in text and "> Story:" in text


def test_fundamental_entry_format():
    entry = card.fundamental_entry(ko(), SOURCE, "2026-10-05", previous=None)
    assert entry.startswith("## 2026-10-05 · fundamental · agent_3 · 2025 annual (10-K)\n")
    block = entry.split("```yaml\n", 1)[1].split("\n```", 1)[0]
    data = yaml.safe_load(block)
    assert data["grade"] == "mid" and data["lynch_type"] == "slow_grower"
    m = data["measures"]["capital_return"]
    assert m["mark"] == "mid" and m["decisive"] == "yes" and 0.14 < m["value"] < 0.15
    assert data["measures"]["interest_cover"]["mark"] == "good"
    assert data["source"]["filing"] == "0000021344-26-000010"
    assert [w["name"] for w in data["warnings"]][:1] == ["one_off"] and data["warnings"][0]["code"] == "U1"
    for heading in ("### Summary", "### Thesis", "### What changed"):
        assert heading in entry


def test_not_computed_is_written_as_such():
    entry = card.fundamental_entry(ko(), SOURCE, "2026-10-05", previous=None)
    data = yaml.safe_load(entry.split("```yaml\n", 1)[1].split("\n```", 1)[0])
    assert data["price"]["peg"] == "not_computed"


def test_append_keeps_everything_and_updates_only_the_header(tmp_path):
    path = tmp_path / "card.md"
    path.write_text(card.new_card(STOCK) + "\n## 2026-10-01 · note · user\nmy own words\n", encoding="utf-8")
    before_body = card.split(path.read_text())[1]
    card.append(path, card.fundamental_entry(ko(), SOURCE, "2026-10-05", previous=None),
                {"grade": "mid", "lynch_type": "slow_grower", "last_entry": "2026-10-05"})
    head, body = card.split(path.read_text())
    assert body.startswith(before_body)  # append-only: the old body is untouched
    assert (head["grade"], head["lynch_type"], head["last_entry"], head["opened"]) == ("mid", "slow_grower", "2026-10-05", "2026-10-05")
    card.append(path, card.note_entry("2026-10-06", "Status: watching → archived (/archive, change #3)"), {"status": "archived"})
    head, body2 = card.split(path.read_text())
    assert body2.startswith(body) and head["status"] == "archived"
    assert "## 2026-10-06 · note · user\nStatus: watching → archived" in body2


def test_only_the_code_fields_can_change(tmp_path):
    path = tmp_path / "card.md"
    path.write_text(card.new_card(STOCK), encoding="utf-8")
    try:
        card.append(path, "", {"opened": "2030-01-01"})
    except ValueError:
        pass
    else:
        raise AssertionError("opened must never change")


def test_out_of_scope_entry():
    r = analyse(Facts(sec_facts("JPM"), sec_submissions("JPM"), quarters=False), "JPM", Market(splits=[]))
    entry = card.fundamental_entry(r, SOURCE | {"label": "2025 annual (10-K)"}, "2026-10-05", previous=None)
    assert "unclear — out of scope: bank (SIC 6021)" in entry
    data = yaml.safe_load(entry.split("```yaml\n", 1)[1].split("\n```", 1)[0])
    assert data["out_of_scope"] == "bank" and data["grade"] == "unclear" and "measures" not in data


def test_what_changed_names_the_grade_change():
    entry = card.fundamental_entry(ko(), SOURCE, "2026-10-05", previous={"grade": "solid", "lynch_type": "slow_grower"})
    assert "grade solid → mid" in entry
