"""The error test sets of the rule cards (roadmap, "AI auditor": "an error test set per card"): cases built from the errors we
really met, with the verdict the auditor must give. Run against the real auditor on the Mac (and after any card change):

    uv run python -m shared.auditor testset

It is also the test of "is the auditor model enough?" — if it misses a case, try another (`/model auditor gpt-6-sol`).
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
NVDA = ("Cash and cash equivalents $ 22,443 $ 10,605\nMarketable securities 34,143 31,238\nTotal cash, cash equivalents and marketable "
        "securities $ 56,586 $ 41,843\nLong-term debt 32,366 7,469")
GE = ("Six months ended June 30 2026 2025\nNet cash provided by operating activities 5,018 3,755\n"
      "Capital expenditures (742) (580)\n(In millions)")
GE_BS = ("Cash, cash equivalents and restricted cash $ 12,450\nInvestment securities 5,830\nCurrent receivables 9,620\n"
         "Other current assets 2,914\nTotal current assets 41,200\n(In millions)\n"
         "Other current assets include time deposits with original maturities of more than three months of $1,010 million.")
GE_TTM = ("the two year-to-date figures against this filing; never fail the total for differing from one column")
REV = "Revenue increased 12% to $4.1 billion in the quarter, driven by higher volumes. Management expects growth to continue."
NOTES = ("In June 2026 we issued $25.0 billion of senior notes to fund general corporate purposes.\n"
         "As of July 26, 2026, we had $33.5 billion aggregate principal amount of senior notes outstanding.")

CASES = [
    # (card, name, text, items, the verdict required for the item)
    ("figure", "Coca-Cola liquid assets: a part missing", KO,
     [{"id": "liquid", "claim": "liquid assets = Cash and cash equivalents 10,270 = 10,270 (nothing else counted), in millions",
       "terms": ["cash and cash equivalents", "short-term investments", "marketable securities"]}], "fail"),
    ("figure", "liquid assets: all parts present", KO,
     [{"id": "liquid", "claim": "liquid assets = cash 10,270 + short-term investments 3,602 + marketable securities 1,934 = 15,806, in millions",
       "terms": ["cash and cash equivalents", "short-term investments", "marketable securities"]}], "pass"),
    ("figure", "Nvidia liquid assets: the securities under a new name are missed", NVDA,
     [{"id": "liquid", "claim": "liquid assets = Cash and cash equivalents 22,443 = 22,443 (no marketable securities found), in millions",
       "terms": ["cash and cash equivalents", "marketable securities"]}], "fail"),
    ("figure", "Nvidia liquid assets: cash + marketable securities", NVDA,
     [{"id": "liquid", "claim": "liquid assets = cash 22,443 + marketable securities 34,143 = 56,586, in millions",
       "terms": ["cash and cash equivalents", "marketable securities"]}], "pass"),
    ("figure", "Boeing debt: only the current part", BOEING,
     [{"id": "debt", "claim": "debt = Current portion of long-term debt 8,460 = 8,460, in millions", "terms": ["debt"]}], "fail"),
    ("figure", "Pfizer 2020 debt: one item, not the total", PFIZER,
     [{"id": "debt", "claim": "debt = Long-term debt 4,000 = 4,000, in millions", "terms": ["debt", "borrowings"]}], "fail"),
    ("figure", "debt: the right total", BOEING,
     [{"id": "debt", "claim": "debt = Current portion 8,460 + Long-term debt 45,388 = 53,848, in millions", "terms": ["debt"]}], "pass"),
    ("figure", "GE: a correct 4-quarter total is not failed against the 6-month column", GE,
     [{"id": "op_cash", "claim": "op_cash = 9,800 (NetCashProvidedByUsedInOperatingActivities), period end 2026-06-30 (TTM), in millions",
       "note": "TTM = the last annual report's 8,537 (in the 10-K, not in this filing) + this year to date 5,018 − the same period a "
       "year before 3,755. Check " + GE_TTM, "terms": ["operating activities"]}], "pass"),
    ("figure", "GE: a 4-quarter total built on a wrong year-to-date part", GE,
     [{"id": "op_cash", "claim": "op_cash = 10,800 (NetCashProvidedByUsedInOperatingActivities), period end 2026-06-30 (TTM), in millions",
       "note": "TTM = the last annual report's 8,537 (in the 10-K, not in this filing) + this year to date 6,018 − the same period a "
       "year before 3,755. Check " + GE_TTM, "terms": ["operating activities"]}], "fail"),
    ("figure", "GE liquid assets: time deposits inside other current assets are not counted", GE_BS,
     [{"id": "liquid", "claim": "liquid assets = cash 12,450 + investment securities 5,830 = 18,280, period end 2026-06-30 (BS), in millions",
       "note": "only parts with a balance-sheet line of their own count: a part with no line of its own (e.g. time deposits inside "
       "other current assets) is not counted — never fail liquid assets for leaving it out",
       "terms": ["cash and cash equivalents", "investment securities", "time deposits"]}], "pass"),
    ("figure", "GE liquid assets: cash including restricted cash as one line counts", GE_BS,
     [{"id": "liquid", "claim": "liquid assets = CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents 12,450 = 12,450, "
       "period end 2026-06-30 (BS), in millions",
       "note": "restricted cash counts when the filing reports cash and restricted cash as one line — never fail for that",
       "terms": ["cash, cash equivalents and restricted cash"]}], "pass"),
    ("reading", "NET: a general risk sentence taken as a real case", NET,
     [{"id": "U1", "claim": "The company faces an active lawsuit that is hurting its business.", "kind": "company_specific",
       "quote": "We may become subject to claims, lawsuits or regulatory proceedings that could be costly and harm our business.",
       "terms": ["lawsuits"]}], "fail"),
    ("reading", "a claim the quote supports", NET,
     [{"id": "U2", "claim": "Revenue grew 28% on new large customers.", "kind": "company_specific",
       "quote": "Revenue increased 28% year over year, driven by new large customers and expansion of existing customers.",
       "terms": ["revenue"]}], "pass"),
    ("reading", "Nvidia: our own figures repeated from `what` are not a reason to fail (acceptance test 2026-10-09)", NOTES,
     [{"id": "U1", "what": "flag data_check: debt 8.5 → 33.4 bn (2026)", "kind": "company_specific",
       "claim": "Debt rose from 8.5 to 33.4 bn, about 24.9 bn more, because the company issued senior notes in June 2026.",
       "quote": "In June 2026 we issued $25.0 billion of senior notes to fund general corporate purposes.",
       "terms": ["senior notes"]}], "pass"),
    ("reading", "a cause in neither the quote nor `what` (Coca-Cola's Nigeria sale, acceptance test 2026-10-09)", NOTES,
     [{"id": "U1", "what": "flag data_check: debt 8.5 → 33.4 bn (2026)", "kind": "company_specific",
       "claim": "Debt rose from 8.5 to 33.4 bn because the company borrowed to pay for the acquisition of a chip designer.",
       "quote": "In June 2026 we issued $25.0 billion of senior notes to fund general corporate purposes.",
       "terms": ["senior notes"]}], "fail"),
    ("sell", "a sell suggestion whose evidence says the opposite", REV,
     [{"id": "sell", "claim": "the thesis broke — revenue fell 30% — \"Revenue increased 12% to $4.1 billion in the quarter\"",
       "terms": ["revenue"]}], "fail"),
]


def run(model: str | None = None, run=None) -> list[dict]:
    out = []
    for card, name, text, items, want in CASES:
        res = auditor.audit(card, items, text, model=model, run=run)
        got = res.items[0]["verdict"] if res.items else "no_answer"
        out.append({"card": card, "case": name, "want": want, "got": got, "ok": got == want, "reason": (res.items or [{}])[0].get("reason", res.error)})
    return out


def report(results: list[dict]) -> str:
    lines = ["AUDITOR TEST SET"] + [f"{'OK  ' if r['ok'] else 'MISS'} · card {r['card']} · {r['case']} → {r['got']} (want {r['want']})"
                                    + ("" if r["ok"] else f" — {r['reason']}") for r in results]
    missed = [r for r in results if not r["ok"]]
    lines.append("All caught." if not missed else f"{len(missed)} missed: if this repeats, switch the auditor to GPT-6 Sol.")
    return "\n".join(lines)
