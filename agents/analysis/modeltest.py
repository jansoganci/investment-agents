"""The strong-model test (roadmap section 10.1: "two companies' 'why?' answers, shown without model names; I choose").

    uv run python -m agents.analysis.modeltest KO NVDA            two companies, the default strong model against GPT-6 Sol
    uv run python -m agents.analysis.modeltest KO NVDA sonnet-5.5 gpt-6-sol   choose the two models
    uv run python -m agents.analysis.modeltest --reveal           which model was "A" and which "B"

It reads the real SEC data and the real filings and writes nothing to the cards or the stock tables (only `ai_calls`)."""

from __future__ import annotations

import json
import random
import sys

from agents.analysis import ai as parts
from agents.analysis import card
from agents.analysis.measures import Market, analyse
from agents.analysis.run import LiveSources, _source
from shared import ai, config, runlog, sec
from shared.sec.facts import Facts

KEY = "modeltest-key.json"


def one(src, ticker: str, model: str, run) -> tuple[list, str]:
    found = src.lookup(ticker)
    if not found:
        raise SystemExit(f"SEC does not know {ticker}")
    subs, facts = src.submissions(found["cik"]), Facts(src.facts(found["cik"]), src.submissions(found["cik"]))
    r = analyse(facts, ticker, Market())
    r.codes, r.closed = card.assign_codes(None, r.flags)
    source = _source(facts, r, found["cik"])
    text = src.filing_text(found["cik"], source["filing"], sec.primary_document(subs, source["filing"]))
    ctx = parts.Context(ticker=ticker, company=found["name"], run=run, model=model)
    return parts.ask_why(r, text, ctx), r.grade


def main(argv: list[str]) -> str:
    key_path = config.data_dir() / KEY
    if argv == ["--reveal"]:
        return key_path.read_text() if key_path.exists() else "No test has been run yet."
    if len(argv) < 2:
        raise SystemExit(__doc__)
    tickers, models = argv[:2], (argv[2:4] if len(argv) >= 4 else ["default", "gpt-6-sol"])
    src, rng, key, out = LiveSources(), random.Random(), {}, ["STRONG-MODEL TEST — which answers are clearer, better supported? Models are hidden (A / B)."]

    def work(run):
        for ticker in tickers:
            order = [0, 1]
            rng.shuffle(order)
            answers = {}
            for slot, idx in zip("AB", order):
                model = None if models[idx] == "default" else models[idx]
                why, grade = one(src, ticker, model, run)
                answers[slot] = why
                key[f"{ticker} {slot}"] = models[idx]
            out.append(f"\n=== {ticker} (grade {grade}) ===")
            for w in answers["A"]:
                b = next((x for x in answers["B"] if x.id == w.id), None)
                out.append(f"\n[{w.id}] {w.what}")
                for slot, x in (("A", w), ("B", b)):
                    if x is None:
                        out.append(f"  {slot}: (no answer)")
                    else:
                        out.append(f"  {slot}: {x.answer}" + (f'\n     quote: "{x.quote}"' if x.quote else "") + ("" if x.verified else "  [quote NOT in the filing]"))
        key_path.write_text(json.dumps(key, indent=1))
        out.append("\nWhich is better, A or B, per company? Then: uv run python -m agents.analysis.modeltest --reveal")
        return "\n".join(out)
    if models[0] == models[1]:
        raise SystemExit("choose two different models")
    return _with_run(work)


def _with_run(work) -> str:
    with runlog.run("modeltest") as r:
        return work(r)


if __name__ == "__main__":
    print(main(sys.argv[1:]))
