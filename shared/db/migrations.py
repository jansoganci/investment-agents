"""Numbered upgrade steps. The database carries its version in `PRAGMA user_version`.

Rules (roadmap section 5, "Structure changes"):
- A step is never edited after it is merged; a change is a new step with the next number.
- A step only adds (tables, columns, indexes) or rebuilds a table by copying every row. Data is never lost.
- Times are UTC text (`2026-10-04T20:15:03Z`). A missing figure is NULL, never 0.
- Names and values follow docs/GLOSSARY.md; CHECK lists hold the glossary values.
"""

STEP_1 = """
-- Stock identity = internal number (id) + CIK for SEC filers; the ticker is only a label.
CREATE TABLE stocks (
    id            INTEGER PRIMARY KEY,
    cik           TEXT UNIQUE,
    ticker        TEXT NOT NULL,
    company       TEXT,
    exchange      TEXT,
    country       TEXT,
    sector        TEXT,
    subsector     TEXT,
    status        TEXT NOT NULL CHECK (status IN ('candidate', 'watching', 'archived')),
    grade         TEXT CHECK (grade IN ('solid', 'mid', 'weak', 'unclear')),
    lynch_type    TEXT CHECK (lynch_type IN ('fast_grower', 'stalwart', 'slow_grower', 'cyclical', 'unprofitable',
                                             'turnaround', 'asset_play')),
    in_portfolio  TEXT NOT NULL DEFAULT 'no' CHECK (in_portfolio IN ('yes', 'no')),
    added_by      TEXT CHECK (added_by IN ('counter', 'user')),
    opened        TEXT,
    last_entry    TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX stocks_ticker ON stocks (ticker);

-- Agent 1: one row per post, downloaded once.
CREATE TABLE articles (
    id            INTEGER PRIMARY KEY,
    url           TEXT NOT NULL UNIQUE,
    site          TEXT NOT NULL,
    title         TEXT,
    published_at  TEXT,
    tags          TEXT,                         -- JSON list of the post's tags
    sentence      TEXT,                         -- the one neutral English sentence
    full_text     TEXT,
    read_deep     INTEGER NOT NULL DEFAULT 0 CHECK (read_deep IN (0, 1)),
    text_missing  INTEGER NOT NULL DEFAULT 0 CHECK (text_missing IN (0, 1)),
    created_at    TEXT NOT NULL
);

-- Tag mapping: a tag is classified once; I can correct it (`/tag`).
CREATE TABLE tags (
    id            INTEGER PRIMARY KEY,
    tag           TEXT NOT NULL UNIQUE,
    kind          TEXT CHECK (kind IN ('company', 'commodity', 'sector')),
    maps_to       TEXT,
    exchange      TEXT,
    country       TEXT,
    sector        TEXT,
    subsector     TEXT,
    source        TEXT CHECK (source IN ('ai', 'user')),
    created_at    TEXT NOT NULL
);

CREATE TABLE commodity_links (
    id            INTEGER PRIMARY KEY,
    stock_id      INTEGER NOT NULL REFERENCES stocks (id),   -- the company
    commodity     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('producer', 'user')),
    source        TEXT,
    created_at    TEXT NOT NULL
);

-- Agent 2: 5 criteria × 0–2; every criterion has a reason (JSON: criterion → reason).
CREATE TABLE scores (
    id               INTEGER PRIMARY KEY,
    stock_id         INTEGER NOT NULL REFERENCES stocks (id),
    week             TEXT NOT NULL,
    mentions         INTEGER CHECK (mentions BETWEEN 0 AND 2),
    tone             INTEGER CHECK (tone BETWEEN 0 AND 2),
    sector_tailwind  INTEGER CHECK (sector_tailwind BETWEEN 0 AND 2),
    news_flow        INTEGER CHECK (news_flow BETWEEN 0 AND 2),
    quick_health     INTEGER CHECK (quick_health BETWEEN 0 AND 2),
    score            INTEGER CHECK (score BETWEEN 0 AND 10),
    reasons          TEXT NOT NULL,
    created_at       TEXT NOT NULL
);

-- The missing-data ledger (agent 3).
CREATE TABLE missing_data (
    id            INTEGER PRIMARY KEY,
    stock_id      INTEGER NOT NULL REFERENCES stocks (id),
    year          TEXT,
    figure        TEXT NOT NULL,
    names_tried   TEXT,                         -- JSON list of XBRL names tried
    status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'tag_added', 'absent')),
    created_at    TEXT NOT NULL
);

-- Figures from filings, one row per figure and period; value NULL = not found (missing ≠ 0).
CREATE TABLE financials (
    id            INTEGER PRIMARY KEY,
    stock_id      INTEGER NOT NULL REFERENCES stocks (id),
    period_end    TEXT NOT NULL,
    period_type   TEXT NOT NULL CHECK (period_type IN ('annual', 'quarter', 'ttm')),
    form          TEXT,                         -- 10-K, 10-Q, 20-F
    figure        TEXT NOT NULL,
    value         REAL,
    unit          TEXT,
    xbrl          TEXT,                         -- the tag the figure came from (trace)
    filing        TEXT,                         -- accession number (trace)
    source        TEXT CHECK (source IN ('sec', 'user')),
    created_at    TEXT NOT NULL
);
CREATE INDEX financials_stock ON financials (stock_id, figure, period_end);

-- Daily closes from the one nightly price job. History is kept: one row per symbol and day, never overwritten.
CREATE TABLE prices (
    id            INTEGER PRIMARY KEY,
    symbol        TEXT NOT NULL,                -- a ticker, SPY, gold, USD/TRY, a sector fund …
    date          TEXT NOT NULL,
    close         REAL,
    adj_close     REAL,
    currency      TEXT,
    source        TEXT,
    created_at    TEXT NOT NULL,
    UNIQUE (symbol, date)
);

CREATE TABLE signals (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL CHECK (kind IN ('new_money_rank', 'weight_cap', 'drop_alert', 'expensive')),
    stock_id      INTEGER REFERENCES stocks (id),
    date          TEXT NOT NULL,
    detail        TEXT,                         -- JSON
    status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'done')),
    created_at    TEXT NOT NULL
);

-- The ledger: one row per event, append-only. `/undo` marks a row void, never deletes it.
CREATE TABLE holdings (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL CHECK (kind IN ('buy', 'sell', 'dividend', 'split')),
    stock_id      INTEGER NOT NULL REFERENCES stocks (id),
    date          TEXT NOT NULL,
    quantity      REAL,
    price         REAL,                         -- USD per share
    fee           REAL,
    amount        REAL,                         -- USD (dividend, after withholding)
    split_ratio   REAL,
    command_id    INTEGER REFERENCES command_log (id),
    void          INTEGER NOT NULL DEFAULT 0 CHECK (void IN (0, 1)),
    voided_by     INTEGER REFERENCES command_log (id),
    created_at    TEXT NOT NULL
);

-- My gold and BES entries. TL entries keep the TL amount and the USD/TRY rate used.
CREATE TABLE other_assets (
    id            INTEGER PRIMARY KEY,
    kind          TEXT NOT NULL CHECK (kind IN ('gold', 'bes')),
    date          TEXT NOT NULL,
    grams         REAL,                         -- gold; a sale is minus grams
    price_try     REAL,                         -- gold: TL per gram
    payment_try   REAL,                         -- BES: this month's payment
    total_try     REAL,                         -- BES: the total in the BES app
    usdtry        REAL,                         -- the rate used
    command_id    INTEGER REFERENCES command_log (id),
    void          INTEGER NOT NULL DEFAULT 0 CHECK (void IN (0, 1)),
    voided_by     INTEGER REFERENCES command_log (id),
    created_at    TEXT NOT NULL
);

-- Agent 4: one frozen row per week.
CREATE TABLE snapshots (
    id            INTEGER PRIMARY KEY,
    week_end      TEXT NOT NULL UNIQUE,
    stock_value   REAL,
    put_in        REAL,
    got_back      REAL,
    return_pct    REAL,
    spy_shadow    REAL,
    gold_shadow   REAL,
    gold_value    REAL,
    bes_value     REAL,
    total_wealth  REAL,
    goal_share    REAL,
    created_at    TEXT NOT NULL
);

-- Every job writes one row per run.
CREATE TABLE runs (
    id            INTEGER PRIMARY KEY,
    job           TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    status        TEXT NOT NULL CHECK (status IN ('running', 'ok', 'error')),
    cost_usd      REAL NOT NULL DEFAULT 0,
    error         TEXT
);
CREATE INDEX runs_job ON runs (job, started_at);

-- One row per card entry: the history behind the sell triggers and the archive reminder.
CREATE TABLE card_entries (
    id             INTEGER PRIMARY KEY,
    stock_id       INTEGER NOT NULL REFERENCES stocks (id),
    date           TEXT NOT NULL,
    record         TEXT NOT NULL CHECK (record IN ('research', 'fundamental', 'note')),
    who            TEXT NOT NULL CHECK (who IN ('agent_2', 'agent_3', 'user')),
    source         TEXT,
    grade          TEXT CHECK (grade IN ('solid', 'mid', 'weak', 'unclear')),
    lynch_type     TEXT,
    thesis_status  TEXT CHECK (thesis_status IN ('intact', 'broken', 'watch')),
    command_id     INTEGER REFERENCES command_log (id),
    created_at     TEXT NOT NULL
);

CREATE TABLE audits (
    id            INTEGER PRIMARY KEY,
    stock_id      INTEGER REFERENCES stocks (id),
    audit         TEXT NOT NULL CHECK (audit IN ('figure', 'reading', 'sell', 'event')),
    result        TEXT NOT NULL CHECK (result IN ('pass', 'fail', 'not_found')),
    detail        TEXT,                         -- JSON: items, quotes, reasons
    model         TEXT,
    cost_usd      REAL NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);

-- Every change I make through a command. `id` is the number shown to me; `/undo` uses it.
CREATE TABLE command_log (
    id            INTEGER PRIMARY KEY,
    command       TEXT NOT NULL,
    args          TEXT NOT NULL DEFAULT '',
    summary       TEXT,                         -- what changed, in plain English
    target_table  TEXT,
    target_id     INTEGER,
    status        TEXT NOT NULL DEFAULT 'done' CHECK (status IN ('done', 'void')),
    voided_by     INTEGER REFERENCES command_log (id),
    created_at    TEXT NOT NULL
);

-- My overrides from Telegram (e.g. `/model`). Append-only: the latest non-void row per key wins;
-- value NULL = back to the default in settings.yaml.
CREATE TABLE settings (
    id            INTEGER PRIMARY KEY,
    key           TEXT NOT NULL,
    value         TEXT,
    command_id    INTEGER REFERENCES command_log (id),
    void          INTEGER NOT NULL DEFAULT 0 CHECK (void IN (0, 1)),
    voided_by     INTEGER REFERENCES command_log (id),
    created_at    TEXT NOT NULL
);

-- The approved subsector list (only with my approval).
CREATE TABLE subsectors (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE,
    sector        TEXT NOT NULL,                -- one of the 11 GICS sectors
    command_id    INTEGER REFERENCES command_log (id),
    created_at    TEXT NOT NULL
);
"""

# (number, SQL). Append new steps at the end; never edit a merged step.
STEPS: list[tuple[int, str]] = [
    (1, STEP_1),
]


def latest(steps: list[tuple[int, str]] | None = None) -> int:
    steps = STEPS if steps is None else steps
    return steps[-1][0] if steps else 0
