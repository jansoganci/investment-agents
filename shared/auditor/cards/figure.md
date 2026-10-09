# Rule card 1 — figure audit (agent 3)

TASK: check that the figures our code took from SEC's data are the figures in the filing. You never produce or correct a
figure; you only say whether each one matches the filing text you are given.

INPUT: a list of figures — name, XBRL name, period end, value in the company's currency — and two parts of the filing:
"FILING ROWS THAT PRINT OUR FIGURES" (rows our code found by searching the filing for our numbers, each with the period or
date header above it) and "FILING EXCERPTS" (paragraphs chosen by words: balance sheet, income statement, cash flow
statement, notes).
A row was found by its number, not by its meaning: still check that its label is the figure named, its column is the right
period and its unit is right. A row about something else that happens to print the same number proves nothing.

CHECKLIST, for each figure:
1. Find it in the rows or the excerpts and copy the row (or sentence) that shows it as `quote`, word for word.
2. Same unit? (thousands, millions, billions) Same period? (the year, the last 4 quarters, 9 months, 3 months) The claim
   says its period in a code after the date: `(FY)` = the fiscal year (12 months) · `(Q)` = the 10-Q's period (the latest
   quarter, or the year to date) · `(BS)` = the balance sheet on that date · `(TTM)` = **the last 4 quarters**, a sum our
   code made; no filing shows it. A `TTM` item's note gives the parts (the last annual report + this year to date − the
   same period a year before): check the two year-to-date parts against the filing (copy both rows); the annual part is in the
   10-K, not in this filing — never fail for that. Never compare a `TTM` total with a 3-, 6- or 9-month figure.
3. Liquid assets = cash and cash equivalents + short-term investments + marketable DEBT securities. Is any part missing from
   our figure, or a part counted that should not be? Marketable EQUITY securities and stakes in other companies are left out on
   purpose (our rule): never fail a figure for leaving them out. Only parts with a balance-sheet line of their own count: a
   part with no line of its own (e.g. GE's time deposits over 3 months inside "other current assets") is not counted (our
   rule) — never fail liquid assets for leaving it out. Restricted cash counts when the filing reports cash and restricted
   cash as one line (`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`; GE, SBUX) — never fail for that.
4. Debt = long-term debt + its current portion + short-term borrowings. Is any part missing or counted twice?
5. Share count: diluted weighted average, after splits?

KNOWN TRAPS:
- Coca-Cola: short-term investments under another name, so our liquid assets missed a part.
- Boeing: only the current part of debt taken, not the long-term part (8.5 instead of 53.9 billion).
- Pfizer 2020: `LongTermDebt` held a single item, not the total (4 instead of about 40 billion).
- GE, 2026: operating cash for the last 4 quarters (9.8 bn = 8.537 + 5.018 − 3.755) was failed against the 6-month row
  (5.0 bn) of the 10-Q. A 4-quarter total is checked by its parts, never against one column.
- Nvidia: it also holds tens of billions in equity securities (stakes); they are not liquid assets by our rule. Its marketable
  securities are named differently from one filing to the next (`DebtSecuritiesCurrent` since July 2026).

PASS CRITERION: the difference is under 1% or only rounding. A figure you cannot find in the rows or the excerpts is
`not_found`, never `pass`.

ON A FAIL: the card is marked unverified and I am told; nothing is changed.
