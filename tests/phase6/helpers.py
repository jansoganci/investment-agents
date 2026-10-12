from shared import clock

NOW = clock.now_utc()


def stock(db, ticker, status="watching", grade=None, in_portfolio="no", company=None, added_by="counter"):
    cur = db.execute("INSERT INTO stocks (ticker, company, status, grade, in_portfolio, added_by, created_at) VALUES (?, ?, ?, ?, ?, ?, 'x')",
                     (ticker, company or ticker.title(), status, grade, in_portfolio, added_by))
    db.commit()
    return cur.lastrowid


def entry(db, stock_id, grade, day=None, record="fundamental"):
    cur = db.execute("INSERT INTO card_entries (stock_id, date, record, who, grade, created_at) VALUES (?, ?, ?, 'agent_3', ?, 'x')",
                     (stock_id, day or clock.today_local(), record, grade))
    db.commit()
    return cur.lastrowid


def score(db, stock_id, total=7, week="2026-W41", points=(1, 2, 1, 2, 1)):
    db.execute("INSERT INTO scores (stock_id, week, mentions, tone, sector_tailwind, news_flow, quick_health, score, reasons, created_at) "
               "VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', 'x')", (stock_id, week, *points, total))
    db.commit()


def tag(db, name, kind="company", status="confirmed", subsector=None, maps_to=None, us=1):
    db.execute("INSERT INTO tags (tag, kind, maps_to, us_listed, subsector, source, status, created_at) VALUES (?, ?, ?, ?, ?, 'ai', ?, 'x')",
               (name, kind, maps_to, us, subsector, status))
    db.commit()
