# Rule card 4 — serious-negative event audit (agent 2)

TASK: check that a news event the writer called a SERIOUS NEGATIVE really happened, is about THIS company, and is recent. You
never write a new claim.

INPUT: one item — the claim (the event as the writer put it: what happened, the company and ticker, the kind of event, the date),
and the quote it gave from the source page (already confirmed to be on the page word for word by code) — plus excerpts of the page.

CHECKLIST:
1. Does the quote (and the page around it) say that this happened? Not "may", "could" or "might happen" — it happened or was
   announced.
2. Is it about THIS company, not a competitor, a supplier, a customer, a namesake or the whole industry?
3. Is it company-specific, not a general risk sentence ("we may be subject to investigations") or a sector-wide worry?
4. Is the date within the last 12 months? An old event repeated in a new article does not count.
5. Is it one of the five serious kinds: an accounting or auditor problem · bankruptcy risk or debt restructuring · an official
   investigation of the company · a profit warning together with a cut outlook · a sudden departure of the CEO or CFO? A dip in the
   share price, a lawsuit that is routine, a missed quarter without a cut outlook, or a planned succession is NOT one of them.

KNOWN TRAPS:
- The old system read a general legal-risk sentence (Cloudflare, NET) as a real case.
- News about another company that the page also mentions (a competitor's investigation).
- An event from years ago summarised in a recent article.
- A planned CEO retirement taken as a sudden departure.

PASS CRITERION: all five answers are yes. `fail` when any is no; `not_found` only when you cannot judge from the page.

ON A FAIL: the event is not counted, a note says why, and the stock's news flow is judged without it.
