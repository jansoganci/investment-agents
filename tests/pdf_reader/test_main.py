import fcntl
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from agents.pdf_reader import paths
from agents.pdf_reader.__main__ import main
from tests.pdf_reader.helpers import body, make_pdf, text_lines


def _later() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=10)


def _env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    monkeypatch.setenv("DATA_DIR", str(data))
    monkeypatch.setenv("DRIVE_DIR", str(drive))
    return data, drive


def test_usage(capsys):
    assert main(["x"]) == 2
    assert capsys.readouterr().out.strip() == "usage: python -m agents.pdf_reader"


def test_no_drive_dir(tmp_path, monkeypatch, capsys):
    _env(tmp_path, monkeypatch)
    monkeypatch.delenv("DRIVE_DIR")
    assert main([], now=_later(), sleep=lambda _seconds: None) == 2
    assert "DRIVE_DIR" in capsys.readouterr().out


def test_nothing_new(tmp_path, monkeypatch, capsys):
    _env(tmp_path, monkeypatch)
    assert main([], now=_later(), sleep=lambda _seconds: None) == 0
    assert capsys.readouterr().out.rstrip().endswith("nothing new")


def test_first_and_second_look(tmp_path, monkeypatch, capsys):
    _data, drive = _env(tmp_path, monkeypatch)
    new = drive / "PDF" / "New"
    new.mkdir(parents=True)
    make_pdf(new / "a.pdf", [text_lines(body(12)), text_lines(body(12))])
    now = _later()
    assert main([], now=now, sleep=lambda _seconds: None) == 0
    first = capsys.readouterr().out
    assert "queued: a.pdf (2 pages)" in first
    assert (
        "sorted: a.pdf · 2 pages · content 2 (written 2, scanned 0) · "
        "disclosure 0 (read 0) · disclosures start not found · "
        "invisible characters dropped 0"
    ) in first
    from agents.pdf_reader import registry
    rows = registry.load()
    assert [row["event"] for row in rows] == ["queued", "sorted"]
    assert (paths.work_dir(rows[0]["fingerprint"]) / "pages.json").is_file()
    assert main([], now=now, sleep=lambda _seconds: None) == 0
    second = capsys.readouterr().out
    assert "waiting for step 3 (not built yet): a.pdf" in second
    assert registry.load() == rows


def test_sorter_failure_three_tries(tmp_path, monkeypatch, capsys):
    _data, drive = _env(tmp_path, monkeypatch)
    new = drive / "PDF" / "New"
    new.mkdir(parents=True)
    pdf = new / "a.pdf"
    make_pdf(pdf, [text_lines(body(12)), text_lines(body(12))])

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("agents.pdf_reader.sorter.run", boom)
    now = _later()
    main([], now=now, sleep=lambda _seconds: None)
    first = capsys.readouterr().out
    assert "sorter failed (try 1 of 3): a.pdf · RuntimeError: boom" in first
    main([], now=now, sleep=lambda _seconds: None)
    second = capsys.readouterr().out
    assert "sorter failed (try 2 of 3): a.pdf · RuntimeError: boom" in second
    main([], now=now, sleep=lambda _seconds: None)
    third = capsys.readouterr().out
    assert "sorter failed (try 3 of 3): a.pdf · RuntimeError: boom" in third
    assert "moved to Failed after 3 tries: a.pdf" in third
    assert (drive / "PDF" / "Failed" / "a.pdf").is_file()
    assert not pdf.exists()


def test_lock_held(tmp_path, monkeypatch, capsys):
    _env(tmp_path, monkeypatch)
    paths.ensure_dirs()
    lock = open(paths.work_root() / "look.lock", "a")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        assert main([], now=_later(), sleep=lambda _seconds: None) == 0
        assert capsys.readouterr().out.strip() == "Another look is running; nothing was done."
    finally:
        lock.close()


def test_broken_registry(tmp_path, monkeypatch, capsys):
    data, _drive = _env(tmp_path, monkeypatch)
    registry = data / "pdf_registry.jsonl"
    registry.parent.mkdir(parents=True)
    registry.write_text("not-json\n", encoding="utf-8")
    assert main([], now=_later(), sleep=lambda _seconds: None) == 1
    assert "nothing was done" in capsys.readouterr().out


def test_module_runs(tmp_path):
    data = tmp_path / "data"
    drive = tmp_path / "Investing"
    env = os.environ.copy()
    env["DATA_DIR"] = str(data)
    env["DRIVE_DIR"] = str(drive)
    root = paths.ROOT
    result = subprocess.run(
        [sys.executable, "-m", "agents.pdf_reader"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "nothing new" in result.stdout
