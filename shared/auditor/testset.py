"""The error test sets of the rule cards (roadmap, "AI auditor": "an error test set per card"): cases built from the errors we
really met, with the verdict the auditor must give. Run against the real auditor on the Mac (and after any card change):

    uv run python -m shared.auditor testset

It is also the test of "is DeepSeek V4 Pro enough?" — if it misses a case, switch the job to GPT-6 Sol (`/model auditor gpt-6-sol`).
The texts are short stand-ins written for the traps, not real filings."""

from __future__ import annotations

from shared import auditor

KO = ("Cash and cash equivalents $ 10,270\nShort-term investments 3,602\nMarketable securities 1,934\nTotal current assets 28,000\n"
      "Long-term debt 40,125\nLoans and notes payable 2,500")
BOEING = ("Current portion of long-term debt 8,460\nLong-term debt 45,388\nTotal debt 53,848\n"
          "Total liabilities 160,000")
PFIZER = ("Short-term borrowings, including current portion of long-term debt 3,500\nLong-term debt 36,500\n"
          "Total debt 40,000 at year end.")
NET = ("We may become subject to claims, lawsuits or regulatory proceedings that could be costly and harm our business.\n"
       "Revenue increased 28% year over year, driven by new large customers and expansion of existing customers.")
REV = "Revenue increased 12% to $4.1 billion in the quarter, driven by higher volumes. Management expects growth to continue."

CASES = [
    # (card, name, text, items, the verdict required for the item)
    ("figure", "Coca-Cola liquid assets: a part missing", KO,
     [{"id": "liquid", "claim": "liquid assets = Cash and cash equivalents 10,270 = 10,270 (nothing else counted), in millions",
       "terms": ["cash and cash equivalents", "short-term investments", "marketable securities"]}], "fail"),
    ("figure", "liquid assets: all parts present", KO,
     [{"id": "liquid", "claim": "liquid assets = cash 10,270 + short-term investments 3,602 + marketable securities 1,934 = 15,806, in millions",
       "terms": ["cash and cash equivalents", "short-term investments", "marketable securities"]}], "pass"),
    ("figure", "Boeing debt: only the current part", BOEING,
     [{"id": "debt", "claim": "debt = Current portion of long-term debt 8,460 = 8,460, in millions", "terms": ["debt"]}], "fail"),
    ("figure", "Pfizer 2020 debt: one item, not the total", PFIZER,
     [{"id": "debt", "claim": "debt = Long-term debt 4,000 = 4,000, in millions", "terms": ["debt", "borrowings"]}], "fail"),
    ("figure", "debt: the right total", BOEING,
     [{"id": "debt", "claim": "debt = Current portion 8,460 + Long-term debt 45,388 = 53,848, in millions", "terms": ["debt"]}], "pass"),
    ("reading", "NET: a general risk sentence taken as a real case", NET,
     [{"id": "U1", "claim": "The company faces an active lawsuit that is hurting its business.", "kind": "company_specific",
       "quote": "We may become subject to claims, lawsuits or regulatory proceedings that could be costly and harm our business.",
       "terms": ["lawsuits"]}], "fail"),
    ("reading", "a claim the quote supports", NET,
     [{"id": "U2", "claim": "Revenue grew 28% on new large customers.", "kind": "company_specific",
       "quote": "Revenue increased 28% year over year, driven by new large customers and expansion of existing customers.",
       "terms": ["revenue"]}], "pass"),
    ("sell", "a sell suggestion whose evidence says the opposite", REV,
     [{"id": "sell", "claim": "the thesis broke — revenue fell 30% — \"Revenue increased 12% to $4.1 billion in the quarter\"",
       "terms": ["revenue"]}], "fail"),
]


def run(model: str | None = None) -> list[dict]:
    out = []
    for card, name, text, items, want in CASES:
        res = auditor.audit(card, items, text, model=model)
        got = res.items[0]["verdict"] if res.items else "no_answer"
        out.append({"card": card, "case": name, "want": want, "got": got, "ok": got == want, "reason": (res.items or [{}])[0].get("reason", res.error)})
    return out


def report(results: list[dict]) -> str:
    lines = ["AUDITOR TEST SET"] + [f"{'OK  ' if r['ok'] else 'MISS'} · card {r['card']} · {r['case']} → {r['got']} (want {r['want']})"
                                    + ("" if r["ok"] else f" — {r['reason']}") for r in results]
    missed = [r for r in results if not r["ok"]]
    lines.append("All caught." if not missed else f"{len(missed)} missed: if this repeats, switch the auditor to GPT-6 Sol.")
    return "\n".join(lines)
