"""SEC data (free, no key; a contact line on every request — `SEC_UA` in .env; at most 10 requests a second).

    company_facts(cik)   every XBRL figure the company ever filed (10-K, 10-Q, 20-F …) — one request
    submissions(cik)     name, SIC industry code, tickers, exchanges, the list of filings
    lookup(ticker)       ticker → CIK, name, exchange (SEC's company list)

Shared because agent 2's quick health uses it too. Reading the figures: `shared.sec.facts`.
"""

from __future__ import annotations

import gzip
import json
import os
import time
import urllib.error
import urllib.request

from shared import config  # noqa: F401 — loads .env

FORMS_ANNUAL = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
FORMS_QUARTER = {"10-Q", "10-Q/A"}
FORMS = FORMS_ANNUAL | FORMS_QUARTER

_last_call = 0.0


class SecError(RuntimeError):
    pass


def user_agent() -> str:
    ua = os.environ.get("SEC_UA", "").strip()
    if not ua:
        raise config.SettingMissing('SEC_UA is not set in .env (SEC asks for a contact line, e.g. "investment-agents you@mail.com").')
    return ua


def _get_bytes(url: str, tries: int = 3) -> bytes:
    global _last_call
    for attempt in range(tries):
        wait = 0.15 - (time.monotonic() - _last_call)  # stay well under 10 requests a second
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept-Encoding": "gzip"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                return body
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise SecError(f"SEC has no data at {url}") from exc
            if exc.code in (429, 500, 502, 503) and attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            raise SecError(f"SEC answered {exc.code} for {url}") from exc
        except urllib.error.URLError as exc:
            if attempt < tries - 1:
                time.sleep(2 ** attempt)
                continue
            raise SecError(f"SEC could not be reached ({exc.reason})") from exc
    raise SecError(f"SEC could not be reached: {url}")


def _get(url: str, tries: int = 3) -> dict:
    return json.loads(_get_bytes(url, tries))


def cik10(cik: str | int) -> str:
    return str(int(cik)).zfill(10)


def company_facts(cik: str | int) -> dict:
    return _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10(cik)}.json")


def submissions(cik: str | int) -> dict:
    return _get(f"https://data.sec.gov/submissions/CIK{cik10(cik)}.json")


def lookup(ticker: str) -> dict | None:
    """Ticker → {cik, name, ticker, exchange} from SEC's company list; None if SEC does not know the ticker."""
    data = _get("https://www.sec.gov/files/company_tickers_exchange.json")
    want = ticker.upper().replace(".", "-")
    for cik, name, tk, exchange in data["data"]:
        if tk.upper().replace(".", "-") == want:
            same = [t.upper() for c, _n, t, _e in data["data"] if c == cik]  # share classes of the same company
            return {"cik": cik10(cik), "name": name, "ticker": tk.upper(), "exchange": exchange, "all_tickers": same}
    return None


def filing_url(cik: str | int, accession: str, document: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{document}"


def filing_html(cik: str | int, accession: str, document: str) -> str:
    """The main document of a filing (HTML), as text. Used for the quotes and the excerpts the AI reads (phase 2)."""
    return _get_bytes(filing_url(cik, accession, document)).decode("utf-8", errors="replace")


def primary_document(subs: dict, accession: str) -> str | None:
    recent = (subs.get("filings") or {}).get("recent") or {}
    for accn, doc in zip(recent.get("accessionNumber", []), recent.get("primaryDocument", [])):
        if accn == accession:
            return doc
    return None
