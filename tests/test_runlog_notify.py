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
