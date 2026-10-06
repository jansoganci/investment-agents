"""Phase 1 commands (roadmap 10.2): /watch /archive /unarchive /analyze /card /green /missing /data and their /undo."""

import pytest

from agents.analysis import card, run
from shared import commands, drive
from shared.commands import stocks
from tests.fixtures.loader import FixtureSources


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    src = FixtureSources()
    monkeypatch.setattr(stocks, "SOURCES", src)
    return src


def do(*argv):
    return commands.run([*argv, "--yes"])


def status(db, ticker):
    return db.execute("SELECT status FROM stocks WHERE ticker=?", (ticker,)).fetchone()[0]


def test_watch_a_new_stock_previews_then_creates_it(db):
    code, text = commands.run(["watch", "KO"])
    assert code == 0 and text.startswith("CONFIRM") and "watching" in text
    assert db.execute("SELECT count(*) FROM stocks").fetchone()[0] == 0
    code, text = do("watch", "KO")
    assert code == 0 and "change #1" in text
    assert status(db, "KO") == "watching"
    assert db.execute("SELECT added_by FROM stocks").fetchone()[0] == "user"


def test_watch_a_candidate_writes_a_card_note(db, env):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    do("watch", "KO")
    head, body = card.split(drive.find_card("KO").read_text())
    assert head["status"] == "watching"
    assert "· note · user\nStatus: candidate → watching (/watch, change #1)" in body


def test_watch_refusals(db):
    assert commands.run(["watch", "ZZZZ"])[0] == 1  # SEC does not know it
    do("watch", "KO")
    code, text = do("watch", "KO")
    assert code == 1 and "already" in text


def test_archive_and_unarchive_and_their_undo(db, env):
    run.analyze(db, "KO", FixtureSources(), today="2026-10-05")
    do("watch", "KO")
    do("archive", "KO")
    assert status(db, "KO") == "archived"
    code, text = commands.run(["undo"])  # the last change: the archive
    assert "#2" in text and "watching" in text
    do("undo", "2")
    assert status(db, "KO") == "watching"
    body = card.split(drive.find_card("KO").read_text())[1]
    assert "Change #2 withdrawn: status back to watching" in body  # a dated note; nothing deleted
    assert "Status: watching → archived (/archive, change #2)" in body
    do("archive", "KO")
    do("unarchive", "KO")
    assert status(db, "KO") == "watching"


def test_undo_refuses_when_the_status_changed_since(db):
    do("watch", "KO")  # 1
    do("archive", "KO")  # 2
    code, text = do("undo", "1")
    assert code == 1 and "changed since" in text


def test_undo_of_watch_for_a_new_stock_makes_it_a_candidate(db):
    do("watch", "KO")
    do("undo", "1")
    assert status(db, "KO") == "candidate"


def test_analyze_runs_after_the_confirmation_and_writes_runs(db, env):
    code, text = commands.run(["analyze", "KO"])
    assert "estimated cost about $" in text and db.execute("SELECT count(*) FROM card_entries").fetchone()[0] == 0
    code, text = do("analyze", "KO")
    assert code == 0 and "ANALYSIS · KO" in text
    assert "AI skipped: the filing text could not be fetched" in text  # the numbers and the card are still written
    assert db.execute("SELECT count(*) FROM card_entries").fetchone()[0] == 1
    assert db.execute("SELECT job, status FROM runs").fetchall() == [("analysis", "ok")]
    code, text = do("undo", "1")
    assert code == 1 and "append-only" in text


def test_analyze_refuses_an_archived_stock(db):
    do("watch", "KO")
    do("archive", "KO")
    code, text = commands.run(["analyze", "KO"])
    assert code == 1 and "archived" in text


def test_card_green_and_missing(db, env):
    run.analyze(db, "NVDA", FixtureSources(), today="2026-10-05")
    run.analyze(db, "RIVN", FixtureSources(), today="2026-10-05")
    db.execute("UPDATE stocks SET status='watching'")
    db.commit()
    code, text = commands.run(["card", "NVDA"])
    assert code == 0 and "solid" in text and "card.md" in text
    code, text = commands.run(["green"])
    assert "NVDA" in text and "RIVN" not in text
    code, text = commands.run(["missing"])
    assert "RIVN · debt · 2024" in text and "/data RIVN 2024 debt" in text


def test_data_enters_a_figure_with_a_plausibility_check(db, env):
    run.analyze(db, "RIVN", FixtureSources(), today="2026-10-05")
    code, text = commands.run(["data", "RIVN", "2024", "debt", "44bn"])
    assert "are you sure" in text.lower()  # 10 times the other years
    code, text = commands.run(["data", "RIVN", "2024", "debt", "4.4bn"])
    assert "are you sure" not in text.lower()
    do("data", "RIVN", "2024", "debt", "4.4bn")
    row = db.execute("SELECT figure, period_end, value, source, void FROM financials WHERE source='user'").fetchone()
    assert row == ("debt", "2024", 4.4e9, "user", 0)
    code, text = commands.run(["missing"])
    assert "RIVN · debt · 2024" not in text
    do("undo")
    assert db.execute("SELECT void FROM financials WHERE source='user'").fetchone()[0] == 1


def test_data_refusals(db):
    assert commands.run(["data", "KO", "2025", "debt", "1bn"])[0] == 1  # no such stock yet
    do("watch", "KO")
    assert commands.run(["data", "KO", "2025", "colour", "1bn"])[0] == 1
    assert commands.run(["data", "KO", "2025", "debt", "lots"])[0] == 1


def test_menu_marks_phase_1_commands_as_built():
    for name in ("watch", "archive", "unarchive", "analyze", "card", "green", "missing", "data"):
        assert commands.REGISTRY[name].built


def test_analyze_takes_a_one_off_model_and_refuses_an_unknown_one(db):
    code, text = commands.run(["analyze", "KO", "opus-5.5"])
    assert code == 0 and "model opus-5.5" in text and "analyze KO opus-5.5 --yes" in text
    code, text = commands.run(["analyze", "KO", "nonsense-9"])
    assert code == 1 and "unknown model" in text
    code, text = commands.run(["analyze", "KO", "opus-5.5", "extra"])
    assert code == 1 and "usage" in text
