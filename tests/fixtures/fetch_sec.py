"""Download the SEC sample data once, trimmed (phase 1 tests). Run: uv run python tests/fixtures/fetch_sec.py
Each file keeps only the figures our synonym lists and debt groups use, filings 10-K / 10-Q / 20-F from 2016 on, and
`_meta` with the source and the date. Needs SEC_UA in .env."""

import gzip
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared import sec  # noqa: E402
from shared.sec.synonyms import all_names  # noqa: E402

OUT = Path(__file__).resolve().parent / "sec"

# golden set (BAGLAM.md section 9) + Novo Nordisk (IFRS / 20-F) + traps: GE (1:8 reverse split, 2021), JPM (a bank), PLTR (no debt)
COMPANIES = {"KO": 21344, "NVDA": 1045810, "NKE": 320187, "SBUX": 829224, "PFE": 78003, "INTC": 50863, "BA": 12927,
             "SNAP": 1564408, "DOW": 1751788, "RIVN": 1874178, "NVO": 353278, "GE": 40545, "JPM": 19617,
             "PLTR": 1321655}
SINCE = "2016-01-01"


def trim_facts(raw: dict) -> dict:
    out = {"cik": raw.get("cik"), "entityName": raw.get("entityName"), "facts": {}}
    for tax in ("us-gaap", "ifrs-full"):
        keep = all_names(tax)
        for name, body in raw.get("facts", {}).get(tax, {}).items():
            if name not in keep:
                continue
            units = {}
            for unit, rows in body["units"].items():
                rows = [{k: r[k] for k in ("start", "end", "val", "accn", "fy", "fp", "form", "filed") if k in r}
                        for r in rows if r.get("form") in sec.FORMS and r.get("end", "") >= SINCE]
                if rows:
                    units[unit] = rows
            if units:
                out["facts"].setdefault(tax, {})[name] = {"units": units}
    return out


def trim_submissions(raw: dict) -> dict:
    recent = raw["filings"]["recent"]
    rows = [i for i, f in enumerate(recent["form"]) if f in sec.FORMS][:40]
    keys = ("accessionNumber", "filingDate", "reportDate", "form", "primaryDocument")
    return {k: raw.get(k) for k in ("cik", "name", "sic", "sicDescription", "tickers", "exchanges", "fiscalYearEnd",
                                    "stateOfIncorporation", "addresses")} | {
        "filings": {"recent": {k: [recent[k][i] for i in rows] for k in keys}}}


def save(path: Path, data: dict, url: str) -> None:
    data["_meta"] = {"source": url, "fetched": date.today().isoformat(), "trimmed": "see tests/fixtures/fetch_sec.py"}
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for t in sys.argv[1:] or COMPANIES:
        cik = sec.cik10(COMPANIES[t])
        save(OUT / f"{t}_facts.json.gz", trim_facts(sec.company_facts(cik)),
             f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")
        save(OUT / f"{t}_submissions.json.gz", trim_submissions(sec.submissions(cik)),
             f"https://data.sec.gov/submissions/CIK{cik}.json")
        print(t, "ok")
