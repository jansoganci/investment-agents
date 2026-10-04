import sqlite3

import pytest

from shared import db as dbmod
from shared.db import migrations

ALL_TABLES = {
    # roadmap section 5
    "stocks", "articles", "tags", "commodity_links", "scores", "missing_data", "financials", "prices",
    "signals", "holdings", "other_assets", "snapshots", "runs",
    # added 2026-10-04
    "card_entries", "audits", "command_log", "settings", "subsectors",
}


def table_names(conn):
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return {r[0] for r in rows}


def test_init_creates_every_table(db):
    assert ALL_TABLES <= table_names(db)


def test_init_sets_latest_version(db):
    assert dbmod.version(db) == migrations.latest()


def test_init_twice_keeps_rows(env):
    dbmod.init()
    conn = dbmod.connect()
    conn.execute("INSERT INTO subsectors (name, sector, created_at) VALUES ('Aviation', 'Industrials', '2026-10-04T00:00:00Z')")
    conn.commit()
    conn.close()
    dbmod.init()
    conn = dbmod.connect()
    assert conn.execute("SELECT count(*) FROM subsectors").fetchone()[0] == 1


def test_wal_is_on(db):
    assert db.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_busy_timeout_is_set(db):
    assert db.execute("PRAGMA busy_timeout").fetchone()[0] >= 1000


def test_connect_without_init_fails_clearly(env):
    with pytest.raises(dbmod.DatabaseMissing):
        dbmod.connect()


def test_stock_identity_is_internal_number_plus_cik(db):
    db.execute("INSERT INTO stocks (ticker, company, cik, status, created_at) VALUES ('FB', 'Meta Platforms', '0001326801', 'watching', '2026-10-04T00:00:00Z')")
    sid = db.execute("SELECT id FROM stocks WHERE cik='0001326801'").fetchone()[0]
    # a ticker change does not change the identity
    db.execute("UPDATE stocks SET ticker='META' WHERE id=?", (sid,))
    assert db.execute("SELECT id FROM stocks WHERE ticker='META'").fetchone()[0] == sid
    # the same CIK cannot be a second stock
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO stocks (ticker, cik, status, created_at) VALUES ('META', '0001326801', 'candidate', '2026-10-04T00:00:00Z')")


def test_glossary_values_are_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO stocks (ticker, status, created_at) VALUES ('X', 'takipte', '2026-10-04T00:00:00Z')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO runs (job, started_at, status) VALUES ('x', '2026-10-04T00:00:00Z', 'tamam')")


def test_price_history_is_never_overwritten(db):
    db.execute("INSERT INTO prices (symbol, date, close, source, created_at) VALUES ('SPY', '2026-10-02', 500.0, 'yahoo', '2026-10-03T00:00:00Z')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO prices (symbol, date, close, source, created_at) VALUES ('SPY', '2026-10-02', 501.0, 'yahoo', '2026-10-04T00:00:00Z')")
    assert db.execute("SELECT close FROM prices WHERE symbol='SPY'").fetchone()[0] == 500.0


def test_missing_is_null_not_zero(db):
    # a figure that cannot be found is stored as NULL (missing ≠ 0)
    db.execute("INSERT INTO stocks (ticker, status, created_at) VALUES ('KO', 'watching', '2026-10-04T00:00:00Z')")
    db.execute("INSERT INTO financials (stock_id, period_end, period_type, figure, value, created_at) VALUES (1, '2025-12-31', 'annual', 'capex', NULL, '2026-10-04T00:00:00Z')")
    assert db.execute("SELECT value FROM financials").fetchone()[0] is None


def test_upgrade_step_keeps_every_row(env):
    dbmod.init()
    conn = dbmod.connect()
    conn.execute("INSERT INTO stocks (ticker, company, status, created_at) VALUES ('KO', 'Coca-Cola', 'watching', '2026-10-04T00:00:00Z')")
    conn.execute("INSERT INTO holdings (kind, stock_id, date, quantity, price, created_at) VALUES ('buy', 1, '2026-10-04', 10, 85.65, '2026-10-04T00:00:00Z')")
    conn.commit()
    v = dbmod.version(conn)

    steps = migrations.STEPS + [(v + 1, "ALTER TABLE stocks ADD COLUMN test_note TEXT")]
    done = dbmod.upgrade(conn, steps=steps)

    assert done == [v + 1]
    assert dbmod.version(conn) == v + 1
    assert conn.execute("SELECT ticker, company FROM stocks").fetchall() == [("KO", "Coca-Cola")]
    assert conn.execute("SELECT quantity, price FROM holdings").fetchall() == [(10, 85.65)]
    assert conn.execute("SELECT test_note FROM stocks").fetchone()[0] is None
    conn.close()


def test_upgrade_copies_the_database_first(env):
    dbmod.init()
    conn = dbmod.connect()
    v = dbmod.version(conn)
    dbmod.upgrade(conn, steps=migrations.STEPS + [(v + 1, "CREATE TABLE t_extra (id INTEGER PRIMARY KEY)")])
    conn.close()
    copies = list((env["data"] / "pre-upgrade").glob("*.sqlite"))
    assert len(copies) == 1


def test_failed_upgrade_step_changes_nothing(env):
    dbmod.init()
    conn = dbmod.connect()
    v = dbmod.version(conn)
    bad = migrations.STEPS + [(v + 1, "ALTER TABLE stocks ADD COLUMN ok_col TEXT; THIS IS NOT SQL")]
    with pytest.raises(sqlite3.Error):
        dbmod.upgrade(conn, steps=bad)
    assert dbmod.version(conn) == v
    cols = [r[1] for r in conn.execute("PRAGMA table_info(stocks)")]
    assert "ok_col" not in cols


def test_step_numbers_are_1_to_n():
    assert [n for n, _ in migrations.STEPS] == list(range(1, len(migrations.STEPS) + 1))


def test_cli_info(env, capsys):
    from shared.db.__main__ import main

    assert main(["init"]) == 0
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "version" in out.lower() and "stocks" in out
