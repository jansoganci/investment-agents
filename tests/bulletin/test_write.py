"""shared/bulletin/write: the prompt, reading the model's answer (what is dropped, flagged, capped), the call with its retry."""

import json
from datetime import datetime, timezone

import pytest

from shared.ai.fake import FakeAI
from shared.bulletin import write
from shared.bulletin.gather import Pack, Piece, StockInfo

NOW = datetime(2026, 10, 28, 5, 0, tzinfo=timezone.utc)


def pack(stocks=True):
    p = Pack(window_start="2026-10-27T05:15:00Z", window_end="2026-10-28T05:00:00Z")
    if stocks:
        p.stocks = [StockInfo("KO", "Coca-Cola", True, "2026-10-20", ("price war", "debt grows", "CEO leaves")),
                    StockInfo("NVDA", "Nvidia", False, None, ())]
    p.posts = [Piece("P1", "post", "SK Hynix", "SK Hynix\nCiro 104,6 trilyon won, beklenti 98,6.", "emtia", "2026-10-28T03:00:00Z"),
               Piece("P2", "post", "Cola", "Cola news\nKO raised prices 4%.", "emtia", "2026-10-28T02:00:00Z", tickers=("KO",))]
    p.web = [Piece("W1", "web", "Brent", "Brent tops $115\nBrent rose above 115 a barrel.", "Reuters", "2026-10-28T01:00:00Z", topic="oil")]
    p.filings = [Piece("F1", "filing", "KO 10-Q", "KO filed a 10-Q on 2026-10-27.", "sec", "x", tickers=("KO",))]
    p.earnings = [Piece("E1", "earnings", "KO earnings", "KO reports earnings on 2026-10-30 (Yahoo).", "yahoo", "2026-10-30")]
    return p


GOOD = {
    "calendar": [{"when": "tomorrow", "text": "Amazon reports earnings.", "sources": ["W1"]}, {"when": "someday", "text": "ECB meets.", "sources": ["W1"]}],
    "macro": [{"text": "Brent rose above 115 a barrel.", "sources": ["W1"], "rank": 2}],
    "stocks": {"KO": [{"text": "KO raised prices 4%.", "sources": ["P2"], "thesis_point": 1, "rank": 1}]},
    "interests": [{"group": "ai_infrastructure", "text": "SK Hynix Q3 revenue 104.6 trillion won (expected 98.6).", "sources": ["P1"], "rank": 3},
                  {"group": "robots", "text": "Another story.", "sources": ["P1", "P1"]}],
}


def test_the_prompt_has_the_day_my_stocks_and_only_posts_and_web_hits():
    text = write.build_prompt(pack(), NOW)
    assert "TODAY: 2026-10-28" in text and "WINDOW: 2026-10-27 08:15 to 2026-10-28 08:00" in text
    assert "- KO — Coca-Cola (held). Things that would break the thesis: 1. price war; 2. debt grows; 3. CEO leaves" in text
    assert "- NVDA — Nvidia (watching). Things that would break the thesis: no thesis yet" in text
    assert "[P1] emtia · 2026-10-28" in text and "[P2] emtia · 2026-10-28 · about KO" in text
    assert "[W1] Reuters · 2026-10-28 · search: oil" in text and "Ciro 104,6 trilyon won" in text
    assert "[F1]" not in text and "[E1]" not in text                                   # SEC lines and earnings dates are code
    assert 'none (return "stocks": {})' in write.build_prompt(pack(stocks=False), NOW)


def test_the_prompt_shows_the_figures_table_so_an_item_does_not_contradict_it():
    text = write.build_prompt(pack(), NOW, "S&P 500 · 7.743,98 · gün ▲ %0,3")
    assert "FIGURES" in text and "S&P 500 · 7.743,98" in text and text.index("FIGURES") < text.index("MY STOCKS")
    assert "FIGURES" not in write.build_prompt(pack(), NOW)
    assert "Never print the price level" in write.SYSTEM


def test_a_good_answer_becomes_items_with_their_fields():
    draft = write.parse(GOOD, pack())
    assert draft.notes == []
    cal = draft.of("calendar")
    assert [(i.when, i.text) for i in cal] == [("tomorrow", "Amazon reports earnings."), ("week", "ECB meets.")]   # an unknown `when` → week
    ko = draft.of("stocks")[0]
    assert (ko.ticker, ko.thesis_point, ko.rank, ko.sources) == ("KO", 1, 1, ("P2",))
    assert [i.rank for i in draft.top3()] == [1, 2, 3] and draft.top3()[0].ticker == "KO"
    ai_item, other = draft.of("interests")
    assert (ai_item.group, other.group, other.sources) == ("ai_infrastructure", "other", ("P1",))                  # unknown group → other; ids once


def test_what_cannot_be_trusted_is_dropped_with_a_note():
    bad = {"macro": [{"text": "No source.", "sources": []}, {"text": "A source that does not exist.", "sources": ["W99"]},
                     {"text": "A filing is not a source for the writer.", "sources": ["F1"]},
                     {"text": "Goldman upgraded NVDA.", "sources": ["W1"]}, {"text": "x" * 700, "sources": ["W1"]},
                     {"text": "  ", "sources": ["W1"]}, "not a dict", {"text": "Fine.", "sources": ["W1"], "rank": 7}],
           "stocks": {"TSLA": [{"text": "Not mine.", "sources": ["W1"]}], "KO": [{"text": "Thesis point out of range.", "sources": ["P2"], "thesis_point": 5}]},
           "interests": None}
    draft = write.parse(bad, pack())
    assert [i.text for i in draft.items] == ["Fine.", "Thesis point out of range."]
    assert draft.of("macro")[0].rank is None and draft.of("stocks")[0].thesis_point is None
    text = "\n".join(draft.notes)
    for part in ("(no source that exists): No source.", "A source that does not exist.", "A filing is not a source", "\"upgraded\" is advice",
                 "too long, 700", "without text", "TSLA is not one of my stocks"):
        assert part in text


def test_a_thesis_point_needs_a_thesis_and_a_rank_is_used_once():
    answer = {"stocks": {"NVDA": [{"text": "Nvidia news.", "sources": ["W1"], "thesis_point": 2, "rank": 1}]},
              "macro": [{"text": "Macro.", "sources": ["W1"], "rank": 1}]}
    draft = write.parse(answer, pack())
    assert draft.of("stocks")[0].thesis_point is None                                  # NVDA has no breaks yet
    assert [i.rank for i in draft.items] == [None, 1] or [i.rank for i in draft.items] == [1, None]
    assert len(draft.top3()) == 1


def test_a_section_over_its_limit_keeps_ranked_items_and_the_order():
    rows = [{"text": f"Item {n}.", "sources": ["W1"]} for n in range(12)]
    rows[11]["rank"] = 1
    draft = write.parse({"macro": rows}, pack())
    texts = [i.text for i in draft.of("macro")]
    assert len(texts) == write.CAPS["macro"] and texts[-1] == "Item 11." and texts[:7] == [f"Item {n}." for n in range(7)]
    assert any("macro: 4 item(s) over the limit of 8" in n for n in draft.notes)


def test_numbers_not_in_the_cited_sources_are_flagged_but_the_item_stays():
    answer = {"macro": [{"text": "Brent rose above 115 a barrel.", "sources": ["W1"]},
                        {"text": "Brent rose above 120 a barrel.", "sources": ["W1"]},
                        {"text": "SK Hynix revenue 104.6 trillion won.", "sources": ["W1"]}]}
    draft = write.check_numbers(write.parse(answer, pack()), pack())
    assert [i.flags for i in draft.items] == [[], ["numbers: 120"], ["numbers: 104.6"]]       # P1 has it, but W1 is what was cited


def test_write_calls_the_strong_model_once_and_checks(db, monkeypatch):
    fake = FakeAI(lambda job, system, prompt: GOOD).install(monkeypatch)
    draft = write.write(pack(), conn=db, now=NOW)
    assert [c[0] for c in fake.calls] == ["strong"] and fake.calls[0][1] == write.SYSTEM
    assert "[W1] Reuters" in fake.calls[0][2] and draft.model.startswith("deepseek:")
    assert len(draft.items) == 6 and all(i.flags == [] for i in draft.items)


def test_an_unusable_answer_is_asked_again_once(db, monkeypatch):
    answers = iter(["Sorry, here you go: not json", json.dumps(GOOD)])
    fake = FakeAI(lambda job, system, prompt: next(answers)).install(monkeypatch)
    assert len(write.write(pack(), conn=db, now=NOW).items) == 6
    assert "could not be used" in fake.calls[1][2]
    bad = FakeAI(lambda *a: "[1, 2]").install(monkeypatch)
    with pytest.raises(ValueError, match="not usable twice"):
        write.write(pack(), conn=db, now=NOW)
    assert len(bad.calls) == 2


def test_nothing_to_write_means_no_model_call(db, monkeypatch):
    fake = FakeAI(lambda *a: GOOD).install(monkeypatch)
    empty = Pack(window_start="a", window_end="b")
    draft = write.write(empty, conn=db, now=NOW)
    assert draft.items == [] and "nothing was written" in draft.notes[0] and fake.calls == []


def test_describe_lists_every_item_with_sources_and_flags():
    draft = write.check_numbers(write.parse({"macro": [{"text": "Brent rose above 120 a barrel.", "sources": ["W1"], "rank": 1}]}, pack()), pack())
    text = write.describe(draft)
    assert "MACRO\n1. TOP1 Brent rose above 120 a barrel.\n   sources: W1 ⚠ numbers: 120" in text
