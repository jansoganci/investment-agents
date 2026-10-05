"""Read the saved sample data (tests/fixtures/). Each file carries `_meta` (source and date)."""

import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(*parts: str) -> dict:
    path = HERE.joinpath(*parts)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def sec_facts(ticker: str) -> dict:
    return load("sec", f"{ticker}_facts.json.gz")


def sec_submissions(ticker: str) -> dict:
    return load("sec", f"{ticker}_submissions.json.gz")
