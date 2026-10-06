# Rule card 2 — reading audit (agent 3)

TASK: check that each "why?" answer is really supported by its quote. You never write a new answer.

INPUT: items — an id, the claim (what the AI said), the quote it gave (already confirmed to be in the filing word for
word by code), and the kind it claimed (`company_specific` or `general_risk`) — plus the excerpts.

CHECKLIST, for each item:
1. Does the quote support the claim, or does it say something else?
2. Is the quote about THIS company and a real event, or a general risk sentence that every company writes ("we may be
   subject to lawsuits")? A general risk sentence is not a company-specific event.
3. Is the claim broader than the quote (a number, a cause or a date the quote does not contain)?

KNOWN TRAPS:
- The old system read a general legal-risk sentence of Cloudflare (NET) as a real case.
- An answer that names a figure which is not in the quote.

PASS CRITERION: the quote supports the claim and the kind is right. `fail` when it does not; `not_found` only when you
cannot judge.

ON A FAIL: the card is marked unverified and I am told.
