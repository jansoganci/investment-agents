"""Agent 3 end to end on saved data: SEC → measures → card.md + the database."""

import pytest

from agents.analysis import card, run
from shared import drive
from tests.fixtures.loader import FixtureSources


@pytest.fixture
def src():
    return FixtureSources()


def test_first_run_opens_a_bare_card_and_writes_the_entry(db, env, src):
    out = run.analyze(db, "KO", src, today="2026-10-05")
    stock = run.find_stock(db, "KO")
    assert stock["cik"] == "0000021344" and stock["status"] == "candidate" and stock["added_by"] == "user"
    assert (stock["grade"], stock["lynch_type"], stock["last_entry"]) == (out.grade, "slow_grower", "2026-10-05")
    path = drive.find_card("KO")
    head, body = card.split(path.read_text())
    assert head["grade"] == out.grade and head["opened"] == "2026-10-05" and head["status"] == "candidate"
    assert "## 2026-10-05 · fundamental · agent_3 · last 4 quarters to 2026-04-03 (10-Q)" in body
    entry = db.execute("SELECT record, who, grade, filing FROM card_entries").fetchone()
    assert entry[:3] == ("fundamental", "agent_3", out.grade) and entry[3]
    assert db.execute("SELECT count(*) FROM financials WHERE stock_id=?", (stock["id"],)).fetchone()[0] > 50
    assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 0  # the job wrapper writes `runs`, not analyze()


def test_second_run_appends_a_dated_entry_and_deletes_nothing(db, env, src):
    run.analyze(db, "KO", src, today="2026-10-05")
    path = drive.find_card("KO")
    body1 = card.split(path.read_text())[1]
    fin1 = db.execute("SELECT count(*) FROM financials").fetchone()[0]
    run.analyze(db, "KO", src, today="2026-10-12")
    head, body2 = card.split(path.read_text())
    assert body2.startswith(body1)  # the old entry is untouched
    assert body2.count("· fundamental · agent_3 ·") == 2 and "## 2026-10-12 · fundamental" in body2
    assert "Grade and type unchanged." in body2
    assert head["last_entry"] == "2026-10-12" and head["opened"] == "2026-10-05"
    assert db.execute("SELECT count(*) FROM card_entries").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM financials").fetchone()[0] == fin1  # same figures are not stored twice


def test_missing_figures_go_to_the_ledger_once(db, env, src):
    run.analyze(db, "SNAP", src, today="2026-10-05")
    n = db.execute("SELECT count(*) FROM missing_data").fetchone()[0]
    run.analyze(db, "SNAP", src, today="2026-10-06")
    assert db.execute("SELECT count(*) FROM missing_data").fetchone()[0] == n


def test_an_archived_stock_is_never_analyzed(db, env, src):
    run.analyze(db, "KO", src, today="2026-10-05")
    db.execute("UPDATE stocks SET status='archived'")
    db.commit()
    with pytest.raises(run.Refused, match="archived"):
        run.analyze(db, "KO", src)


def test_unknown_ticker_is_refused(db, env, src):
    with pytest.raises(run.Refused, match="does not know"):
        run.analyze(db, "ZZZZ", src)


def test_a_bank_gets_an_out_of_scope_entry(db, env, src):
    out = run.analyze(db, "JPM", src, today="2026-10-05")
    stock = run.find_stock(db, "JPM")
    assert (stock["out_of_scope"], stock["grade"], out.grade) == ("bank", "unclear", "unclear")
    assert "unclear — out of scope: bank (SIC 6021)" in drive.find_card("JPM").read_text()


def test_user_figures_fill_a_gap(db, env, src):
    # Rivian's 2024 debt is under a name our lists do not know yet → the ledger asks me; my figure fills it
    run.analyze(db, "RIVN", src, today="2026-10-05")
    sid = run.find_stock(db, "RIVN")["id"]
    assert db.execute("SELECT count(*) FROM missing_data WHERE figure='debt' AND year='2024'").fetchone()[0] == 1
    db.execute("INSERT INTO financials (stock_id, period_end, period_type, figure, value, source, created_at) "
               "VALUES (?, '2024', 'annual', 'debt', 4.4e9, 'user', 'x')", (sid,))
    db.commit()
    run.analyze(db, "RIVN", src, today="2026-10-06")
    text = drive.find_card("RIVN").read_text()
    assert text.count("debt not found (2024)") == 1  # only the first entry lists it as a gap


def test_weekly_analyzes_watching_stocks_with_a_new_filing_only(db, env, src):
    run.analyze(db, "KO", src, today="2026-10-05")
    run.analyze(db, "PFE", src, today="2026-10-05")
    db.execute("UPDATE stocks SET status='watching' WHERE ticker='KO'")
    db.execute("UPDATE stocks SET status='archived' WHERE ticker='PFE'")
    db.commit()
    # KO's last entry is based on its latest filing → nothing new; PFE is archived → never analyzed
    msg = run.weekly(db, src, today="2026-10-12")
    assert db.execute("SELECT count(*) FROM card_entries").fetchone()[0] == 2
    assert msg is None
    db.execute("UPDATE card_entries SET filing='older' WHERE stock_id=(SELECT id FROM stocks WHERE ticker='KO')")
    db.commit()
    msg = run.weekly(db, src, today="2026-10-12")
    assert msg and "ANALYSIS · KO" in msg
    assert db.execute("SELECT count(*) FROM card_entries").fetchone()[0] == 3


def test_a_figure_found_later_closes_its_open_row(db, env, src):
    run.analyze(db, "KO", src, today="2026-10-05")
    sid = db.execute("SELECT id FROM stocks WHERE ticker='KO'").fetchone()[0]
    db.execute("INSERT INTO missing_data (stock_id, year, figure, names_tried, status, created_at) "
               "VALUES (?, '2024', 'revenue', '[]', 'open', '2026-10-01')", (sid,))
    db.execute("INSERT INTO missing_data (stock_id, year, figure, names_tried, status, created_at) "
               "VALUES (?, 'TTM 2020-01-01', 'cash', '[]', 'open', '2026-10-01')", (sid,))
    db.commit()
    run.analyze(db, "KO", src, today="2026-10-06")
    rows = db.execute("SELECT figure, status FROM missing_data WHERE stock_id=? AND created_at='2026-10-01'", (sid,)).fetchall()
    assert {r[1] for r in rows} == {"tag_added"}
