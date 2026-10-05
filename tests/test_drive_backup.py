import sqlite3
from datetime import date, timedelta

import pytest

from shared import backup, drive


# --- Drive paths ---

def test_paths(env):
    root = env["drive"]
    assert drive.inbox() == root / "Inbox"
    assert drive.weekly() == root / "Weekly"
    assert drive.backup_dir() == root / "Backup"
    assert drive.card_path("KO", "Coca-Cola Co") == root / "Stocks" / "KO - Coca-Cola Co" / "card.md"


def test_folder_name_is_safe(env):
    # a slash in a company name must not create a subfolder
    p = drive.stock_dir("BRK.B", "Berkshire Hathaway Inc/DE")
    assert p.parent == env["drive"] / "Stocks"
    assert "/" not in p.name


def test_missing_drive_dir_is_clear(monkeypatch):
    from shared import config

    monkeypatch.delenv("DRIVE_DIR", raising=False)
    with pytest.raises(config.SettingMissing):
        drive.inbox()


def test_drive_test_script_writes_a_dated_file_and_prints(db, env, capsys):
    from shared.drive import __main__ as cli

    assert cli.main(["test"]) == 0
    files = list((env["drive"] / "Inbox").glob("drive-test-*.md"))
    assert len(files) == 1
    assert "publish: no" in files[0].read_text()
    out = capsys.readouterr().out
    assert out.startswith("DRIVE TEST")
    assert files[0].name in out
    assert db.execute("SELECT status FROM runs WHERE job='drive_test'").fetchone()[0] == "ok"


def test_drive_folders_are_created(env):
    drive.ensure_folders()
    for name in ("Inbox", "Weekly", "Backup", "Stocks"):
        assert (env["drive"] / name).is_dir()


# --- Backup ---

def test_backup_copy_opens(db, env):
    db.execute("INSERT INTO subsectors (name, sector, created_at) VALUES ('Aviation', 'Industrials', '2026-10-04T00:00:00Z')")
    db.commit()
    path = backup.make_copy(date(2026, 10, 4))
    assert path.parent == env["drive"] / "Backup"
    copy = sqlite3.connect(path)
    assert copy.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert copy.execute("SELECT name FROM subsectors").fetchone()[0] == "Aviation"
    copy.close()


def _names(days):
    return [backup.file_name(d) for d in days]


def test_retention_keeps_7_daily_and_4_weekly():
    today = date(2026, 10, 4)  # a Sunday
    days = [today - timedelta(days=i) for i in range(60)]
    keep = backup.to_keep(_names(days), keep_daily=7, keep_weekly=4)
    kept = sorted(backup.date_of(n) for n in keep)
    # the last 7 days
    assert kept[-7:] == sorted(today - timedelta(days=i) for i in range(7))
    # plus 4 older weekly copies (the latest copy of each earlier week)
    older = kept[:-7]
    assert len(older) == 4
    assert len({d.isocalendar()[:2] for d in older}) == 4
    assert len(keep) == 11


def test_retention_with_few_files_keeps_all():
    days = [date(2026, 10, 4) - timedelta(days=i) for i in range(3)]
    assert set(backup.to_keep(_names(days), 7, 4)) == set(_names(days))


def test_prune_deletes_only_old_backup_files(env):
    folder = env["drive"] / "Backup"
    folder.mkdir(parents=True)
    for i in range(30):
        (folder / backup.file_name(date(2026, 10, 4) - timedelta(days=i))).write_text("x")
    (folder / "my-notes.txt").write_text("keep me")
    removed = backup.prune(folder, 7, 4)
    assert len(removed) == 30 - 11
    assert (folder / "my-notes.txt").exists()
    assert len(list(folder.glob("investment-agents-*.sqlite"))) == 11


def test_backup_job_writes_runs_row(db, env, capsys):
    from shared.backup import main

    assert main([]) == 0
    assert db.execute("SELECT status FROM runs WHERE job='backup'").fetchone()[0] == "ok"
    assert len(list((env["drive"] / "Backup").glob("*.sqlite"))) == 1


def test_backup_is_one_self_contained_file(db, env):
    # no -wal / -shm next to the copy in Drive, and no half-written file under the final name
    path = backup.make_copy(date(2026, 10, 4))
    copy = sqlite3.connect(path)
    assert copy.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    assert copy.execute("SELECT count(*) FROM stocks").fetchone()[0] == 0
    copy.close()
    assert sorted(p.name for p in (env["drive"] / "Backup").iterdir()) == [path.name]
