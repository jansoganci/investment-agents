"""The Wednesday message (my decision, 2026-11-01): what waits for me, in the order holdings → watched → candidates."""

from datetime import timedelta

from shared import clock, drive, notify, open_items

from .helpers import NOW, stock, tag

DAY = "2026-11-04"
OLD = (NOW - timedelta(days=40)).isoformat()


def missing(db, sid, figure="operating", year="2024", created="x", status="open"):
    db.execute("INSERT INTO missing_data (stock_id, year, figure, status, created_at) VALUES (?, ?, ?, ?, ?)", (sid, year, figure, status, created))
    db.commit()


def test_nothing_open_is_still_a_message(db, env):
    lines, items = open_items.build(db, DAY)
    assert lines == [f"OPEN ITEMS · {DAY} — nothing open"] and items.count() == 0


def test_holdings_come_first_then_watched_then_candidates(db, env):
    hold = stock(db, "HHH", "watching", in_portfolio="yes")
    watch = stock(db, "WWW", "watching")
    cand = stock(db, "CCC", "candidate")
    for sid in (cand, watch, hold):
        missing(db, sid, created=clock.utc_iso())
    text = "\n".join(open_items.build(db, DAY)[0])
    assert text.index("MY HOLDINGS") < text.index("STOCKS I WATCH") < text.index("CANDIDATES")
    assert text.index("HHH") < text.index("WWW") < text.index("CCC")
    assert "data CCC 2024 operating <value, e.g. 0.25bn>" in text and "/data" not in text        # written without the slash
    assert "archive <TICKER>" in text                                                            # how to drop a candidate's questions


def test_a_ttm_year_is_written_the_way_the_data_command_wants_it(db, env):
    missing(db, stock(db, "SLB", "watching"), year="TTM 2026-09-30", created=clock.utc_iso())
    text = "\n".join(open_items.build(db, DAY)[0])
    assert "data SLB TTM 2026-09-30 operating" in text


def test_a_candidate_question_drops_after_four_weeks_but_a_watched_stock_keeps_it(db, env):
    missing(db, stock(db, "OLDC", "candidate"), created=OLD)
    missing(db, stock(db, "OLDW", "watching"), created=OLD)
    lines, items = open_items.build(db, DAY)
    text = "\n".join(lines)
    assert "OLDC" not in text and "OLDW" in text and items.hidden == 1 and "1 dropped this time" in text


def test_an_archived_stock_is_not_asked_about(db, env):
    missing(db, stock(db, "GONE", "archived"), created=clock.utc_iso())
    assert open_items.build(db, DAY)[1].count() == 0


def test_waiting_tags_are_all_listed_with_their_reason_and_how_to_answer(db, env):
    for i in range(12):
        tag(db, f"Name {i}", status="waiting")
    db.execute("UPDATE tags SET note = 'SEC does not know the ticker X' WHERE tag = 'Name 3'")
    db.commit()
    text = "\n".join(open_items.build(db, DAY)[0])
    assert "TAGS THAT WAIT FOR ME (12)" in text and "Name 11" in text                              # no 5-name cut
    assert "- Name 3 — SEC does not know the ticker X → tag Name 3 company <TICKER>  (or: tag Name 3 company non-us)" in text


def test_resolved_since_last_time_counts_only_closed_items_not_hidden_ones(db, env):
    done = stock(db, "DONE", "watching")
    hidden = stock(db, "HID", "candidate")
    missing(db, done, "capex", "2023", created=clock.utc_iso())
    missing(db, hidden, "capex", "2023", created=clock.utc_iso())
    tag(db, "Aramco", status="waiting")
    lines, items = open_items.build(db, "2026-10-28")
    open_items.save("2026-10-28", lines, items)
    db.execute("UPDATE missing_data SET status = 'tag_added' WHERE stock_id = ?", (done,))        # found since
    db.execute("UPDATE missing_data SET created_at = ? WHERE stock_id = ?", (OLD, hidden))        # only hidden (4 weeks)
    db.execute("UPDATE tags SET status = 'confirmed' WHERE tag = 'Aramco'")                        # I answered
    db.commit()
    text = "\n".join(open_items.build(db, DAY)[0])
    assert "Resolved since last time: 2 (DONE 2023 capex, tag Aramco)" in text and "HID 2023" not in text.split("Resolved")[1].splitlines()[0]
    assert text.splitlines()[0] == f"OPEN ITEMS · {DAY} — nothing open"


def test_the_first_list_has_no_resolved_line_and_the_file_is_saved(db, env):
    missing(db, stock(db, "SLB", "watching"), created=clock.utc_iso())
    lines, items = open_items.build(db, DAY)
    assert "Resolved" not in "\n".join(lines)
    path = open_items.save(DAY, lines, items)
    assert path.name == f"{DAY}-open-items.md" and (drive.weekly() / f"{DAY}-open-items.json").exists()


def test_a_long_list_is_not_cut(db, env):
    for i in range(80):
        missing(db, stock(db, f"T{i:02d}", "watching"), created=clock.utc_iso())
    text = open_items.run(DAY)
    assert len(text) > notify.MAX_LEN and "(cut" not in text and "T79" in text


def test_the_job_prints_the_message(db, env, capsys):
    assert open_items.main(["--day", DAY]) == 0
    assert capsys.readouterr().out.startswith(f"OPEN ITEMS · {DAY} — nothing open")
    assert open_items.main(["--bad"]) == 2
