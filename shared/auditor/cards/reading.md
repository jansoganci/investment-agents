# Rule card 2 — reading audit (agent 3)

TASK: check that each "why?" answer is really supported by its quote. You never write a new answer.

INPUT: items — an id, `what` (the question as we asked it, with OUR figures: computed by code from SEC data and checked
separately by the figure audit), the claim (what the AI said), the quote it gave (one or two sentences separated by " | ",
each already confirmed to be in the filing word for word by code), and the kind it claimed (`company_specific` or
`general_risk`) — plus the excerpts.

CHECKLIST, for each item:
1. Does the quote support the claim, or does it say something else?
2. Is the quote about THIS company and a real event, or a general risk sentence that every company writes ("we may be
   subject to lawsuits")? A general risk sentence is not a company-specific event.
3. Is the claim broader than the quote: a cause, an event, a date or a number that is neither in the quote nor in `what`?
   Our figures from `what`, and simple arithmetic on them (a difference, a change from one year to the next), are NOT a
   reason to fail — they are checked elsewhere. What you check is the reason the answer gives: is THAT in the quote?

KNOWN TRAPS:
- The old system read a general legal-risk sentence of Cloudflare (NET) as a real case.
- An answer that names a figure which is in neither the quote nor `what`.
- Failing an answer only because it repeats our own figures from `what` (acceptance test 2026-10-09: Nvidia's debt rise
  8.5 → 33.4 bn was given to the writer; the quote only had to show why).

PASS CRITERION: the quote supports the claim and the kind is right. `fail` when it does not; `not_found` only when you
cannot judge.

ON A FAIL: the card is marked unverified and I am told.
