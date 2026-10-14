from datetime import date, timedelta

import pytest

from shared import clock, commands, summary
from shared.commands import builtin

from .helpers import NOW, entry, score, stock, tag

DAY = clock.today_local()
WEEK = "%d-W%02d" % date.fromisoformat(DAY).isocalendar()[:2]          # the week the summary of DAY belongs to


def test_an_empty_database_gives_only_the_header_the_portfolio_line_and_the_spend(db, env):
    lines = summary.build(db, DAY)
    assert lines[0] == f"SUNDAY SUMMARY · {DAY}"
    assert "Portfolio:" in lines and "(the portfolio run did not give a block this week)" in lines
    assert lines[-1] == "AI spend this month: $0.00 of $30"
    assert not any(l.endswith(":") and l not in ("Portfolio:",) for l in lines)           # no empty sections


def test_candidates_of_the_latest_week_only_and_only_while_they_are_candidates(db, env):
    a, b, c = stock(db, "AAA", "candidate"), stock(db, "BBB", "candidate", added_by="user"), stock(db, "CCC", "watching")
    old = stock(db, "OLD", "candidate")
    score(db, a, 9, WEEK), score(db, b, 5, WEEK), score(db, c, 8, WEEK), score(db, old, 10, "2020-W01")
    text = "\n".join(summary.build(db, DAY))
    assert "New candidates (a score is a ranking, not a buy):" in text
    assert text.index("- AAA") < text.index("- BBB") and "added by me" in text.split("- BBB")[1].splitlines()[0]
    assert "CCC" not in text and "OLD" not in text


def test_grade_changes_and_first_analyses_of_the_week(db, env):
    ko, nvda, ge = stock(db, "KO"), stock(db, "NVDA"), stock(db, "GE")
    entry(db, ko, "mid", (NOW - timedelta(days=30)).date().isoformat())
    entry(db, ko, "solid", DAY)                                     # changed this week
    entry(db, nvda, "solid", DAY)                                   # first analysis this week
    entry(db, ge, "mid", (NOW - timedelta(days=30)).date().isoformat())
    entry(db, ge, "mid", DAY)                                       # same grade: not listed
    text = "\n".join(summary.build(db, DAY))
    changes = text.split("Card changes this week:")[1].split("\n\n")[0]
    assert f"- KO: grade mid → solid ({DAY})" in changes and f"- NVDA: first analysis, grade solid ({DAY})" in changes and "GE" not in changes


def test_counter_notes_tag_questions_unclear_data_and_archive_reminders(db, env):
    run_at = clock.utc_iso()
    db.execute("INSERT INTO counts (run_at, kind, key, label, posts_7d, posts_30d, rank, has_card, points, created_at) VALUES "
               "(?, 'stock', 'KO', 'Coca-Cola', 8, 9, NULL, 1, NULL, ?), (?, 'stock', 'PEP', 'Pepsi', 3, 4, NULL, 1, NULL, ?), "
               "(?, 'non_us', 'Tencent', 'Tencent', 5, 9, 1, 0, NULL, ?)", (run_at, run_at) * 3)
    tag(db, "Standard Oil", status="waiting")
    tag(db, "Uranyum", "sector", subsector="other")
    xx = stock(db, "XX", grade="unclear")
    stock(db, "YY", grade="solid")
    zz = stock(db, "ZZ", grade="mid")
    entry(db, zz, "mid"), entry(db, zz, "weak")
    kept = stock(db, "KEEP", grade="mid", in_portfolio="yes")
    entry(db, kept, "mid"), entry(db, kept, "weak")
    db.execute("INSERT INTO missing_data (stock_id, figure, status, created_at) VALUES (?, 'interest', 'open', 'x')", (xx,))
    db.commit()
    text = "\n".join(summary.build(db, DAY))
    assert "- KO (8 posts)" in text and "PEP" not in text and "- Tencent (5 posts)" in text
    assert "1 tag(s) wait for you" in text and "Standard Oil" in text and "fit no approved subsector: Uranyum" in text
    assert "- grade unclear: XX" in text and "1 missing figure(s) are still open" in text
    assert "- ZZ: not solid on its last two cards (mid → weak) — archive it? /archive ZZ" in text and "KEEP" not in text.split("Archive reminders:")[1]


def test_errors_are_first_and_the_portfolio_and_agent_3_text_are_kept(db, env):
    lines = summary.build(db, DAY, portfolio_text="PORTFOLIO · $1,596", analysis_text="ANALYSIS · NVDA new 10-Q", errors=["research: boom"])
    assert lines[1:3] == ["", "THINGS THAT FAILED THIS WEEK"] and "- research: boom" in lines
    assert "PORTFOLIO · $1,596" in lines and "ANALYSIS · NVDA new 10-Q" in lines


def test_the_summary_is_saved_in_drive_and_the_command_shows_the_latest(db, env):
    assert "No Sunday summary has been written yet" in commands.run(["summary"])[1]
    summary.save("2026-10-04", ["SUNDAY SUMMARY · 2026-10-04", "", "old"])
    summary.save("2026-10-11", ["SUNDAY SUMMARY · 2026-10-11", "", "newer"])
    code, text = commands.run(["summary"])
    assert code == 0 and text.startswith("SUNDAY SUMMARY · 2026-10-11") and "newer" in text and "old" not in text
    assert (env["drive"] / "Weekly" / "2026-10-11-summary.md").exists()


def test_the_message_is_cut_for_telegram_but_the_file_is_whole(db, env):
    lines = ["SUNDAY SUMMARY · x"] + ["- " + "word " * 40] * 60
    assert len(summary.message(lines)) <= 4096
    assert len(summary.save("2026-10-11", lines).read_text()) > 4096


def test_summary_is_built_and_in_the_menu():
    assert commands.REGISTRY["summary"].built


# --- /status warnings -----------------------------------------------------------------------------------------------------

def test_a_job_running_for_more_than_an_hour_is_warned_about(db, env):
    db.execute("INSERT INTO runs (job, started_at, status) VALUES ('prices', ?, 'running'), ('eye', ?, 'running')",
               (clock.utc_iso(NOW - timedelta(hours=3)), clock.utc_iso(NOW - timedelta(minutes=5))))
    db.commit()
    out = builtin.warnings(db, NOW)
    assert any("prices has been running since" in w and "may be stuck" in w for w in out) and not any("eye" in w for w in out)


def test_the_backup_warning_needs_a_backup_that_is_recent(db, env):
    assert any("no backup found" in w for w in builtin.warnings(db, NOW))
    folder = env["drive"] / "Backup"
    folder.mkdir(parents=True)
    old = folder / "investment-agents-2026-10-01.sqlite"
    old.write_bytes(b"x")
    import os
    os.utime(old, (NOW.timestamp() - 50 * 3600,) * 2)
    assert any("newest backup is 50 hours old (limit 36)" in w for w in builtin.warnings(db, NOW))
    fresh = folder / "investment-agents-2026-10-11.sqlite"
    fresh.write_bytes(b"x")
    os.utime(fresh, (NOW.timestamp() - 3600,) * 2)
    assert builtin.warnings(db, NOW) == []


def test_status_shows_the_warnings(db, env):
    db.execute("INSERT INTO runs (job, started_at, status) VALUES ('prices', ?, 'running')", (clock.utc_iso(NOW - timedelta(hours=3)),))
    db.commit()
    code, text = commands.run(["status"])
    assert code == 0 and "WARNING: prices has been running since" in text


def test_without_a_drive_folder_status_has_no_backup_warning(db, monkeypatch):
    monkeypatch.delenv("DRIVE_DIR", raising=False)
    assert builtin.warnings(db, NOW) == []


def test_candidates_of_an_older_week_are_not_shown_as_new_when_this_week_had_no_research(db, env):
    """Audit 2026-10-14, #5: if Research gave nothing this week, last week's list must not be shown as this week's."""
    a = stock(db, "AAA", "candidate")
    score(db, a, 9, "2020-W01")
    assert "AAA" not in "\n".join(summary.build(db, DAY))
    assert summary.candidates(db) and "AAA" in summary.candidates(db)[0]               # the /candidates command still shows the latest


def test_the_counter_lines_are_empty_when_the_latest_counter_run_found_nothing(db, env):
    db.execute("INSERT INTO counts (run_at, kind, key, label, posts_7d, posts_30d, rank, has_card, points, created_at) "
               "VALUES ('2026-10-05T09:00:00Z', 'stock', 'AAPL', 'Apple', 9, 9, NULL, 1, NULL, 'x')")
    db.execute("INSERT INTO runs (job, started_at, ended_at, status) VALUES ('counter', '2026-10-12T09:00:00Z', '2026-10-12T09:00:01Z', 'ok')")
    db.commit()
    assert summary.counter_lines(db) == ([], [])
