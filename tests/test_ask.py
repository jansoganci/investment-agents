import sqlite3

import pytest

from shared import ask


def test_select_works(db):
    db.execute("INSERT INTO subsectors (name, sector, created_at) VALUES ('Aviation', 'Industrials', '2026-10-04T00:00:00Z')")
    db.commit()
    cols, rows = ask.query("SELECT name, sector FROM subsectors")
    assert cols == ["name", "sector"] and rows == [("Aviation", "Industrials")]


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO subsectors (name, sector, created_at) VALUES ('X', 'Energy', 'now')",
        "UPDATE stocks SET status='archived'",
        "DELETE FROM runs",
        "DROP TABLE runs",
        "CREATE TABLE x (a)",
        "PRAGMA query_only = OFF",
        "ATTACH DATABASE 'other.db' AS other",
    ],
)
def test_cannot_write(db, sql):
    with pytest.raises(sqlite3.Error):
        ask.query(sql)
    assert db.execute("SELECT count(*) FROM subsectors").fetchone()[0] == 0


def test_tables_lists_columns(db):
    text = ask.tables_text()
    assert "stocks:" in text and "ticker" in text


def test_reads_a_card(db, env):
    folder = env["drive"] / "Stocks" / "KO - Coca-Cola Co"
    folder.mkdir(parents=True)
    (folder / "card.md").write_text("---\nticker: KO\n---\n")
    assert "ticker: KO" in ask.card("KO")
    assert ask.card("ZZZZ") is None


def test_cli_refuses_a_write(db, capsys):
    from shared.ask import main

    assert main(["sql", "DELETE FROM runs"]) == 1
    assert "read-only" in capsys.readouterr().out.lower()
