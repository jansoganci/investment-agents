import json

NOW = "2026-10-12T09:00:00Z"
SINCE = "2026-10-05T09:00:00Z"
_n = [0]


def company_tag(db, name="Cummins", ticker="CMI", us=1, status="confirmed", kind="company"):
    db.execute("INSERT OR IGNORE INTO tags (tag, kind, maps_to, us_listed, source, status, created_at) VALUES (?, ?, ?, ?, 'ai', ?, 'x')",
               (name, kind, ticker, us, status))
    db.commit()


def article(db, title="Cummins veri merkezi motor talebi", text="Cummins veri merkezi motoru talebinin arttığını duyurdu. Şirket yıl sonu beklentisini yükseltti.",
            tags=("Cummins",), published="2026-10-10T08:00:00Z", text_missing=0):
    _n[0] += 1
    db.execute("INSERT INTO articles (url, site, title, published_at, tags, full_text, text_missing, created_at) VALUES (?, 'emtia', ?, ?, ?, ?, ?, ?)",
               (f"https://x/{_n[0]}/", title, published, json.dumps(list(tags), ensure_ascii=False), text, text_missing, published))
    db.commit()
    return db.execute("SELECT max(id) FROM articles").fetchone()[0]
