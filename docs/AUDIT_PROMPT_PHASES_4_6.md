# Audit prompt — phases 4, 5 and 6 together (Eye · Counter + Research · the Sunday chain)

Written 2026-10-14 for a **separate** Claude session (the one that wrote the code must not audit it). Template: `docs/IMPLEMENTATION_PLAN.md` section 4.
Run it in a fresh session on `jansoganci/investment-agents`, branch `main` (state of 2026-10-14: commit `f287d61` or later).
Bring the findings table back to the building session; fixes go in small branches and the usual merge rule.

```text
You are auditing phases 4, 5 and 6 together of the repo jansoganci/investment-agents, branch main (Eye; Counter + Research; the Sunday chain,
alerts, summary, schedule). They were built early under an explicit exception to fixed rule 5 and have now run for two days in production.
Read AGENTS.md first (fixed rules, "Current status"), then docs/IMPLEMENTATION_PLAN.md (phases 4, 5, 6), docs/YOL_HARITASI_v2.md
("Agent 1 rules" 1-19, "Agent 1B rules", "Agent 2 rules" 1-9, "Score rules", "AI auditor", "Telegram and Hermes", "Rules that prevent
spending"), docs/SCHEDULE.md, docs/TEST_PLAN.md (section 6 = the real results) and docs/GLOSSARY.md.
Do not change anything in the repo; only report. Do not look for or use any secret. You have no access to the Air or the sites: judge from the code,
the tests and the documents. Run `uv run pytest -q` (expect about 671 passed) and report any failure.

Check, item by item:
1. Every item the three phases "Build" exists and works as described. Every rule they "Rely on" has code AND a test: name the file:line of
   each; list every rule with no code, or no test, or a test that cannot fail.
2. EYE (agents/eye, shared/commands/eye.py): the cookie goes only to its own host (also after a redirect) and is never printed, logged,
   stored in the database, or put in an error message (including session_check, set_cookie, http errors, the runs table, Telegram text);
   a blocked answer (403/429) stops the pass; the 200-address guard; the first run is a baseline; a gated page is text_missing and never retried;
   a failed page is not recorded as seen; the 80-page cap and the alternating sites; eye_seen and articles stay consistent if the process
   dies in the middle of a page (atomicity); the cookie-expiry warning (5 in a row) and eye.skip_sites; the tag classification (the US-listed SEC
   check, non-US no check and no question, `waiting`, a tag fixed by /tag, /undo); the one-sentence rules (neutral, no advice, the post is DATA).
3. COUNTER (agents/counter): 7-day window on the published date, distinct posts, only confirmed tags, a company's tags are one stock, a stock with
   a card is left out of the ranking, sector counts from sector tags only, ties; `counts` is append-only per run; what `latest()` returns for a run
   that stored no rows (an empty run reads as "never ran" today: is that harmless for agent 2 and the summary?).
4. RESEARCH (agents/research): at most 10 stocks; the score is computed by CODE from labels (5 criteria x 0-2), every criterion has a reason,
   missing data is `unclear` = 1 never 0; quick health arithmetic (3-5 computed checks); sector tailwind (40-week average, the commodity link,
   fallback); the news call: every event needs a source that the web search really returned, a serious negative is confirmed only after the page
   was fetched (SSRF-safe: private addresses, redirects, size cap), its quote is on that page, its date is within 365 days, and the auditor
   (card 4, shared/auditor/cards/event.md) passed it; an important positive counts only within 90 days; the card is born last, in one
   transaction with the database rows; `/watch X` chains Research then Analysis; costs of web search are counted and capped.
5. PHASE 6 (shared/summary.py, alerts.py, sunday.py, commands/builtin.py warnings, docs/SCHEDULE.md): each alert goes out once (alerts_sent) and
   only events of the last 2 days; the Sunday chain order and failure isolation (a failing step is named at the top, the next steps still run;
   nothing is silently swallowed); the summary contents versus the roadmap list; the Telegram length limit; stuck `running` rows and the `/status`
   warnings; the schedule (hours in settings.yaml) versus SCHEDULE.md; what happens when two runs of one job overlap, or when the Air was asleep.
6. PROMPT INJECTION and data flow: text from the two sites (titles, post bodies, tags) and from web pages is untrusted. Follow it end to end:
   into model prompts, into the database, into Inbox/ and the Sunday summary, into stdout that Hermes delivers to Telegram verbatim. Can a post
   make a model or Hermes do something (a command, a /watch, a /bought, a link), leak a secret, or fake a system message? Check the prompts
   say "the post is data" and that no model output is executed or used as a path, SQL or command.
7. DATA SAFETY: card.md is append-only except the header fields written by code; nothing deleted or overwritten; `missing != 0`; times in UTC;
   SQL always parameterised; no secret in the repo, tests, fixtures or docs; .env handling (set_cookie: private file, backup, no value printed).
8. COSTS and LIMITS: the monthly AI limit and the 10 $ OpenRouter warning are enforced on every path (Eye sentences, tags, Research, auditor,
   web search); a runaway loop is impossible (retries, pagination of pause_turn, the sentence retry); token limits per call.
9. PORTABILITY and operations: anything that breaks on the Air or the Mac (paths, the Istanbul time zone, `uv` full path in scheduled jobs,
   missing setup steps, macOS Drive/TCC); model/provider switch: what breaks if Anthropic is removed from settings.yaml (web search is Anthropic-only);
   DB upgrade steps 6-10 are safe on a real database (copy first, foreign keys).
10. Names follow docs/GLOSSARY.md; nothing outside the phases was added; no rule was changed in code without a matching roadmap change.

ALREADY KNOWN, do not report again unless you find the root cause is wrong: Dragonomi is skipped (no membership; eye.skip_sites); Counter and Research
have had no company tags to work with yet (Emtia has commodity tags only); Hermes approvals.mode manual gates only dangerous patterns (Level 2
pending); the NVDA quick-health debt uses the last annual report; Research news sources are often secondary sites; FCX's old positive (fixed, 90 days);
the first Sunday chain ran with an empty database of posts.

Answer in Turkish. Output: a table - # - severity (blocker / should-fix / note) - rule or item - file:line - what is wrong - realistic failure
scenario (inputs -> wrong output) - suggested fix. Rank blockers first; do not list style issues. Then a short list "Not checked" with the reason,
and a one-line verdict: can the system run unattended for 10 more days? yes / no / yes, with these fixes first.
```
