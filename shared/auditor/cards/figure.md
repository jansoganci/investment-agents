# Rule card 1 — figure audit (agent 3)

TASK: check that the figures our code took from SEC's data are the figures in the filing. You never produce or correct a
figure; you only say whether each one matches the filing text you are given.

INPUT: a list of figures — name, XBRL name, period end, value in the company's currency — and excerpts of the filing
(balance sheet, income statement, cash flow statement, notes).

CHECKLIST, for each figure:
1. Find it in the excerpts and copy the row (or sentence) that shows it as `quote`, word for word.
2. Same unit? (thousands, millions, billions) Same period? (the year, the last 4 quarters, 9 months, 3 months)
3. Liquid assets = cash and cash equivalents + short-term investments + marketable securities. Is any part missing from
   our figure, or a part counted that should not be?
4. Debt = long-term debt + its current portion + short-term borrowings. Is any part missing or counted twice?
5. Share count: diluted weighted average, after splits?

KNOWN TRAPS:
- Coca-Cola: short-term investments under another name, so our liquid assets missed a part.
- Boeing: only the current part of debt taken, not the long-term part (8.5 instead of 53.9 billion).
- Pfizer 2020: `LongTermDebt` held a single item, not the total (4 instead of about 40 billion).
- Nvidia: marketable securities are named differently from one filing to the next (`DebtSecuritiesCurrent` since July 2026).

PASS CRITERION: the difference is under 1% or only rounding. A figure you cannot find in the excerpts is `not_found`,
never `pass`.

ON A FAIL: the card is marked unverified and I am told; nothing is changed.
