"""Japan's 10-year government bond yield, from the Ministry of Finance's daily file (Yahoo has no reliable symbol for it).

    mof.update(conn)      stores the new days as symbol `JP10Y` in `prices` (source `mof`, close = the yield in percent)

The file is a CSV: a title line, then a header `Date,1Y,2Y,…,10Y,…` and one row a day (`2026/10/27,…`); a day without a figure
holds `-`. The first time the whole history is read (`jgbcme_all.csv`) and the last `KEEP_DAYS` days are kept; afterwards the
small current file is enough. A day already stored is never overwritten (the table refuses it too). Roadmap "Morning bulletin" 5;
docs/BULLETIN_PLAN.md slice 2. Written from the file's known layout: the first real read is the Air check (plan, T4).
"""

from __future__ import annotations

import csv
import io
import re
import urllib.error
import urllib.request
from datetime import date, timedelta

from shared import clock

SYMBOL = "JP10Y"
BASE = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/"
CURRENT_URL = BASE + "jgbcme.csv"
ALL_URL = BASE + "historical/jgbcme_all.csv"
KEEP_DAYS = 120          # of the full history; enough for the 1-month change with room
PLAUSIBLE = (-5.0, 30.0) # percent; Japan's 10Y was negative from 2016 to 2020, so below zero is real
COLUMN = "10Y"
USER_AGENT = "investment-agents/1.0 (personal research)"
DATE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")


class MofError(RuntimeError):
    pass


def _get_text(url: str, timeout: float = 30) -> str:
    """The file's text. Replaced in tests."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return answer.read().decode("utf-8-sig", errors="replace")
    except urllib.error.HTTPError as error:
        raise MofError(f"the Ministry of Finance file answered HTTP {error.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise MofError(f"the Ministry of Finance file could not be reached ({type(error).__name__})") from None


def parse(text: str) -> list[tuple[str, float]]:
    """[(YYYY-MM-DD, yield in percent)] in file order; days without a figure are left out. MofError if the layout is not the known one."""
    rows = list(csv.reader(io.StringIO(text)))
    header = next((i for i, r in enumerate(rows) if r and r[0].strip().lower() == "date"), None)
    if header is None:
        raise MofError("the Ministry of Finance file has no `Date` header row")
    names = [c.strip() for c in rows[header]]
    if COLUMN not in names:
        raise MofError(f"the Ministry of Finance file has no `{COLUMN}` column (columns: {', '.join(names[:20])})")
    at = names.index(COLUMN)
    out = []
    for r in rows[header + 1:]:
        if len(r) <= at:
            continue
        m = DATE.match(r[0].strip())
        if not m:
            continue
        try:
            value = float(r[at].strip())
        except ValueError:
            continue  # "-" = no figure that day
        out.append((date(int(m[1]), int(m[2]), int(m[3])).isoformat(), value))
    return out


def update(conn, get_text=None, now=None) -> int:
    """Store the days that are not stored yet; returns how many were new. Raises MofError."""
    get_text = get_text or _get_text
    first = conn.execute("SELECT 1 FROM prices WHERE symbol = ? LIMIT 1", (SYMBOL,)).fetchone() is None
    rows = parse(get_text(ALL_URL if first else CURRENT_URL))
    today = date.fromisoformat(clock.today_local(now))
    if first:
        since = (today - timedelta(days=KEEP_DAYS)).isoformat()
        rows = [(d, v) for d, v in rows if d >= since]
    created = clock.utc_iso(now)
    new = 0
    for day, value in rows:
        if day > today.isoformat():
            continue
        if not PLAUSIBLE[0] < value < PLAUSIBLE[1]:   # checked on the days we keep only: the file goes back to 1974
            raise MofError(f"the 10Y figure {value} on {day} is not a plausible yield in percent")
        cur = conn.execute("INSERT OR IGNORE INTO prices (symbol, date, close, adj_close, currency, source, created_at) "
                           "VALUES (?, ?, ?, ?, '%', 'mof', ?)", (SYMBOL, day, value, value, created))
        new += cur.rowcount
    conn.commit()
    return new
