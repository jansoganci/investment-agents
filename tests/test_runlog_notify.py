import pytest

from shared import notify, runlog


def test_run_writes_ok_row(db):
    with runlog.run("test_job") as r:
        r.add_cost(0.012)
        r.add_cost(0.003)
    row = db.execute("SELECT job, status, cost_usd, started_at, ended_at, error FROM runs").fetchone()
    assert row[0] == "test_job" and row[1] == "ok"
    assert row[2] == pytest.approx(0.015)
    assert row[3].endswith("Z") and row[4].endswith("Z")
    assert row[5] is None


def test_run_writes_error_row_and_reraises(db):
    with pytest.raises(ValueError):
        with runlog.run("broken_job"):
            raise ValueError("boom")
    row = db.execute("SELECT status, error, ended_at FROM runs WHERE job='broken_job'").fetchone()
    assert row[0] == "error" and "boom" in row[1] and row[2] is not None


def test_run_is_visible_as_running_while_it_works(db):
    with runlog.run("long_job"):
        status = db.execute("SELECT status FROM runs WHERE job='long_job'").fetchone()[0]
        assert status == "running"


def test_job_main_prints_error_message_and_exits_1(db, capsys):
    def work(r):
        raise RuntimeError("SEC did not answer")

    code = runlog.job_main("prices", work)
    out = capsys.readouterr().out
    assert code == 1
    assert out.startswith("ERROR · prices")
    assert "SEC did not answer" in out


def test_job_main_prints_returned_message(db, capsys):
    code = runlog.job_main("hello", lambda r: notify.message("HELLO", ["line one"]))
    assert code == 0
    assert capsys.readouterr().out == "HELLO\nline one\n"


def test_message_format():
    assert notify.message("DRIVE TEST", ["a", "b"]) == "DRIVE TEST\na\nb"


def test_message_is_cut_to_telegram_limit():
    text = notify.message("LONG", ["x" * 5000])
    assert len(text) <= notify.MAX_LEN
    assert text.endswith(notify.CUT_NOTE)


def test_error_message_names_job_and_time():
    text = notify.error("backup", "disk full")
    first, *rest = text.splitlines()
    assert first == "ERROR · backup"
    assert "disk full" in text
    assert "Turkey time" in text


def test_a_row_left_running_by_a_dead_process_is_closed_by_the_next_run_of_that_job(db):
    """Audit 2026-10-14, #17: otherwise `/status` warns about it for ever."""
    old, recent = "2020-01-01T00:00:00Z", runlog.clock.utc_iso()
    db.executemany("INSERT INTO runs (job, started_at, status) VALUES (?, ?, 'running')",
                   [("eye", old), ("eye", recent), ("prices", old)])
    db.commit()
    with runlog.run("eye"):
        pass
    rows = db.execute("SELECT job, started_at, status, error FROM runs ORDER BY id").fetchall()
    assert rows[0][2] == "error" and "abandoned" in rows[0][3]          # the old eye row is closed
    assert rows[1][2] == "running"                                      # a recent one may be a live run: left alone
    assert rows[2][2] == "running"                                      # another job's row is not touched
    assert rows[3][0] == "eye" and rows[3][2] == "ok"
