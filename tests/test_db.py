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
    # nothing changed, so the copy taken before the step is not kept
    assert list((env["data"] / "pre-upgrade").glob("*.sqlite")) == []


def test_step_numbers_are_1_to_n():
    assert [n for n, _ in migrations.STEPS] == list(range(1, len(migrations.STEPS) + 1))


def test_cli_info(env, capsys):
    from shared.db.__main__ import main

    assert main(["init"]) == 0
    assert main(["info"]) == 0
    out = capsys.readouterr().out
    assert "version" in out.lower() and "stocks" in out


# --- Audit fixes (phase 0) ---------------------------------------------------------------------------------------

def _stock_with_links(conn):
    conn.execute("INSERT INTO stocks (ticker, company, status, created_at) VALUES ('KO', 'Coca-Cola', 'watching', '2026-10-04T00:00:00Z')")
    conn.execute("INSERT INTO command_log (command, args, created_at) VALUES ('bought', '10 KO 85.65', '2026-10-04T00:00:00Z')")
    conn.execute("INSERT INTO holdings (kind, stock_id, date, quantity, price, command_id, created_at) VALUES ('buy', 1, '2026-10-04', 10, 85.65, 1, '2026-10-04T00:00:00Z')")
    conn.commit()


REBUILD_STOCKS = """
CREATE TABLE stocks_new (
    id INTEGER PRIMARY KEY, cik TEXT UNIQUE, ticker TEXT NOT NULL, company TEXT, exchange TEXT, country TEXT,
    sector TEXT, subsector TEXT, status TEXT NOT NULL, grade TEXT, lynch_type TEXT, in_portfolio TEXT NOT NULL DEFAULT 'no',
    added_by TEXT, opened TEXT, last_entry TEXT, created_at TEXT NOT NULL, test_note TEXT
);
INSERT INTO stocks_new (id, cik, ticker, company, exchange, country, sector, subsector, status, grade, lynch_type,
                        in_portfolio, added_by, opened, last_entry, created_at)
    SELECT id, cik, ticker, company, exchange, country, sector, subsector, status, grade, lynch_type,
           in_portfolio, added_by, opened, last_entry, created_at FROM stocks;
DROP TABLE stocks;
ALTER TABLE stocks_new RENAME TO stocks;
CREATE INDEX stocks_ticker ON stocks (ticker);
"""


def test_rebuild_step_keeps_rows_and_links(env):
    # a table that other tables point to (stocks) can be rebuilt by copying every row
    dbmod.init()
    conn = dbmod.connect()
    _stock_with_links(conn)
    v = dbmod.version(conn)
    assert dbmod.upgrade(conn, steps=migrations.STEPS + [(v + 1, REBUILD_STOCKS)]) == [v + 1]
    assert conn.execute("SELECT id, ticker, company FROM stocks").fetchall() == [(1, "KO", "Coca-Cola")]
    assert conn.execute("SELECT stock_id, quantity FROM holdings").fetchall() == [(1, 10)]
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1  # the check is on again afterwards
    conn.close()


def test_step_that_breaks_links_is_refused(env):
    dbmod.init()
    conn = dbmod.connect()
    _stock_with_links(conn)
    v = dbmod.version(conn)
    with pytest.raises(sqlite3.IntegrityError):
        dbmod.upgrade(conn, steps=migrations.STEPS + [(v + 1, "UPDATE holdings SET stock_id = 99")])
    assert dbmod.version(conn) == v
    assert conn.execute("SELECT stock_id FROM holdings").fetchone()[0] == 1
    conn.close()


def test_upgrade_race_second_process_does_nothing(env, monkeypatch):
    # two jobs start right after `git pull`: the second one must not run the same step again
    dbmod.init()
    first, second = dbmod.connect(), dbmod.connect()
    v = dbmod.version(first)
    steps = migrations.STEPS + [(v + 1, "CREATE TABLE t_race (id INTEGER PRIMARY KEY)")]
    assert dbmod.upgrade(first, steps=steps) == [v + 1]

    real = dbmod.version
    calls = {"n": 0}

    def stale(conn):  # the second job read the version before the first one finished
        calls["n"] += 1
        return v if calls["n"] == 1 else real(conn)

    monkeypatch.setattr(dbmod, "version", stale)
    assert dbmod.upgrade(second, steps=steps) == []
    assert len(list((env["data"] / "pre-upgrade").glob("*.sqlite"))) == 1
    first.close()
    second.close()


@pytest.mark.parametrize("table", ["holdings", "other_assets", "card_entries", "command_log", "prices"])
def test_append_only_tables_refuse_delete(db, table):
    _stock_with_links(db)
    db.execute("INSERT INTO other_assets (kind, date, grams, price_try, created_at) VALUES ('gold', '2026-10-04', 1, 4689, '2026-10-04T00:00:00Z')")
    db.execute("INSERT INTO card_entries (stock_id, date, record, who, created_at) VALUES (1, '2026-10-04', 'note', 'user', '2026-10-04T00:00:00Z')")
    db.execute("INSERT INTO prices (symbol, date, close, created_at) VALUES ('SPY', '2026-10-02', 500.0, '2026-10-03T00:00:00Z')")
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(f"DELETE FROM {table}")
    db.rollback()
    assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 1


def test_prices_are_never_overwritten(db):
    db.execute("INSERT INTO prices (symbol, date, close, created_at) VALUES ('SPY', '2026-10-02', 500.0, '2026-10-03T00:00:00Z')")
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE prices SET close = 1")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT OR REPLACE INTO prices (symbol, date, close, created_at) VALUES ('SPY', '2026-10-02', 2.0, 'x')")
    db.rollback()
    # the nightly job's way: a day that is already there is skipped
    db.execute("INSERT OR IGNORE INTO prices (symbol, date, close, created_at) VALUES ('SPY', '2026-10-02', 3.0, 'x')")
    assert db.execute("SELECT close FROM prices").fetchall() == [(500.0,)]


def test_void_marking_still_works(db):
    _stock_with_links(db)
    db.execute("UPDATE holdings SET void = 1, voided_by = 1 WHERE id = 1")
    assert db.execute("SELECT void FROM holdings").fetchone()[0] == 1


def test_card_entries_lynch_type_uses_the_glossary_values(db):
    db.execute("INSERT INTO stocks (ticker, status, created_at) VALUES ('KO', 'watching', '2026-10-04T00:00:00Z')")
    db.execute("INSERT INTO card_entries (stock_id, date, record, who, lynch_type, created_at) VALUES (1, '2026-10-04', 'fundamental', 'agent_3', 'stalwart', 'x')")
    db.execute("INSERT INTO card_entries (stock_id, date, record, who, created_at) VALUES (1, '2026-10-04', 'research', 'agent_2', 'x')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO card_entries (stock_id, date, record, who, lynch_type, created_at) VALUES (1, '2026-10-04', 'fundamental', 'agent_3', 'bank', 'x')")
