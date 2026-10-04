from pathlib import Path

import pytest

from shared import commands
from shared.commands import Applied, Plan


@pytest.fixture
def gold_cmd():
    """A stand-in changing command for the tests (the real /gold comes in phase 3)."""

    def plan(conn, args):
        grams, price = float(args[0]), float(args[1])

        def apply(conn, command_id):
            cur = conn.execute(
                "INSERT INTO other_assets (kind, date, grams, price_try, command_id, created_at) "
                "VALUES ('gold', '2026-10-04', ?, ?, ?, '2026-10-04T18:00:00Z')",
                (grams, price, command_id),
            )
            return Applied(f"Gold: {grams:g} g at {price:,.0f} TL", "other_assets", cur.lastrowid)

        return Plan([f"add a gold purchase: {grams:g} g at {price:,.0f} TL a gram"], ["testgold", *args], apply)

    cmd = commands.Command("testgold", "test only", "/testgold <grams> <price>", changes=True, plan=plan)
    commands.REGISTRY["testgold"] = cmd
    yield cmd
    del commands.REGISTRY["testgold"]


def test_change_without_yes_only_previews(db, gold_cmd):
    code, text = commands.run(["testgold", "1", "4689"])
    assert code == 0
    assert text.startswith("CONFIRM")
    assert "1 g at 4,689 TL" in text
    assert "testgold 1 4689 --yes" in text
    assert db.execute("SELECT count(*) FROM other_assets").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM command_log").fetchone()[0] == 0


def test_change_with_yes_writes_command_log_with_a_number(db, gold_cmd):
    code, text = commands.run(["testgold", "1", "4689", "--yes"])
    assert code == 0
    row = db.execute("SELECT id, command, args, status, target_table, target_id, summary FROM command_log").fetchone()
    assert row[1:6] == ("testgold", "1 4689", "done", "other_assets", 1)
    assert f"#{row[0]}" in text
    assert "Gold: 1 g" in row[6]
    assert db.execute("SELECT command_id FROM other_assets").fetchone()[0] == row[0]


def test_slash_name_works(db, gold_cmd):
    code, _ = commands.run(["/testgold", "1", "4689", "--yes"])
    assert code == 0


def test_undo_marks_void_and_deletes_nothing(db, gold_cmd):
    commands.run(["testgold", "1", "4689", "--yes"])
    commands.run(["testgold", "2", "4700", "--yes"])

    code, preview = commands.run(["undo"])
    assert code == 0 and "#2" in preview and "undo 2 --yes" in preview
    assert db.execute("SELECT count(*) FROM other_assets WHERE void=1").fetchone()[0] == 0  # preview changes nothing

    code, text = commands.run(["undo", "2", "--yes"])
    assert code == 0
    rows = db.execute("SELECT id, grams, void, voided_by FROM other_assets ORDER BY id").fetchall()
    assert len(rows) == 2  # nothing deleted
    undo_id = db.execute("SELECT id FROM command_log WHERE command='undo'").fetchone()[0]
    assert rows[0][2:] == (0, None)
    assert rows[1][2:] == (1, undo_id)
    log = db.execute("SELECT status, voided_by FROM command_log WHERE id=2").fetchone()
    assert log == ("void", undo_id)
    assert f"#{undo_id}" in text


def test_undo_by_number(db, gold_cmd):
    commands.run(["testgold", "1", "4689", "--yes"])
    commands.run(["testgold", "2", "4700", "--yes"])
    commands.run(["undo", "1", "--yes"])
    assert db.execute("SELECT id FROM other_assets WHERE void=1").fetchall() == [(1,)]


def test_undo_without_number_takes_the_last_change_not_yet_void(db, gold_cmd):
    commands.run(["testgold", "1", "4689", "--yes"])
    commands.run(["testgold", "2", "4700", "--yes"])
    commands.run(["undo", "--yes"])
    commands.run(["undo", "--yes"])
    assert db.execute("SELECT count(*) FROM other_assets WHERE void=1").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM other_assets").fetchone()[0] == 2


def test_undo_twice_is_refused(db, gold_cmd):
    commands.run(["testgold", "1", "4689", "--yes"])
    commands.run(["undo", "1", "--yes"])
    code, text = commands.run(["undo", "1", "--yes"])
    assert code == 1 and "already" in text.lower()


def test_undo_unknown_number(db):
    code, text = commands.run(["undo", "99", "--yes"])
    assert code == 1 and "#99" in text


def test_undo_with_nothing_to_undo(db):
    code, text = commands.run(["undo"])
    assert code == 1 and "nothing" in text.lower()


def test_unknown_command_is_refused(db):
    code, text = commands.run(["sellall"])
    assert code == 2 and "not on the command list" in text.lower()


def test_planned_command_says_not_built_yet(db):
    code, text = commands.run(["bought", "10", "KO", "85.65"])
    assert code == 1 and "phase 3" in text
    assert db.execute("SELECT count(*) FROM command_log").fetchone()[0] == 0


def test_help_lists_every_command(db):
    code, text = commands.run(["help"])
    assert code == 0
    for name in commands.MENU:
        assert f"/{name}" in text


def test_menu_matches_roadmap_10_2():
    assert set(commands.MENU) == {
        "help", "summary", "green", "candidates", "card", "portfolio", "missing", "spend", "model", "status",
        "watch", "archive", "unarchive", "bought", "sold", "gold", "bes", "analyze", "closewarning", "thesis",
        "note", "data", "tag", "subsector", "undo",
    }


def test_status_with_no_runs(db):
    code, text = commands.run(["status"])
    assert code == 0 and text.startswith("STATUS") and "No runs yet" in text


def test_status_shows_last_run_and_errors(db):
    from shared import runlog

    with runlog.run("backup"):
        pass
    with pytest.raises(RuntimeError):
        with runlog.run("drive_test"):
            raise RuntimeError("Drive folder missing")
    code, text = commands.run(["status"])
    assert "backup: ok" in text
    assert "drive_test: error" in text and "Drive folder missing" in text
    assert "Errors in the last 7 days: 1" in text


def test_info_command_does_not_write(db):
    commands.run(["status"])
    commands.run(["help"])
    assert db.execute("SELECT count(*) FROM command_log").fetchone()[0] == 0


def test_setcommands_text_is_valid_for_telegram():
    lines = commands.setcommands_text().splitlines()
    assert len(lines) == len(commands.MENU)
    for line in lines:
        name, desc = line.split(" - ", 1)
        assert name.islower() and name.isalpha() and len(name) <= 32
        assert 3 <= len(desc) <= 256


def test_setcommands_file_is_up_to_date():
    path = Path(__file__).resolve().parent.parent / "docs" / "telegram_setcommands.txt"
    assert path.read_text(encoding="utf-8") == commands.setcommands_text() + "\n"


def test_failed_change_writes_nothing(db):
    def plan(conn, args):
        def apply(conn, command_id):
            conn.execute(
                "INSERT INTO other_assets (kind, date, grams, price_try, command_id, created_at) "
                "VALUES ('gold', '2026-10-04', 1, 4689, ?, 'x')",
                (command_id,),
            )
            raise RuntimeError("broke halfway")

        return Plan(["add a gold purchase"], ["testbroken"], apply)

    commands.REGISTRY["testbroken"] = commands.Command("testbroken", "test only", "/testbroken", changes=True, plan=plan)
    try:
        with pytest.raises(RuntimeError):
            commands.run(["testbroken", "--yes"])
    finally:
        del commands.REGISTRY["testbroken"]
    assert db.execute("SELECT count(*) FROM command_log").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM other_assets").fetchone()[0] == 0
