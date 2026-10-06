---
doc: Implementation plan
date: 2026-10-04
status: approved (2026-10-04)
publish: no
---

# Implementation plan — investment-agents

Phase by phase. The rules live in `docs/YOL_HARITASI_v2.md` (the roadmap); this file only says **in which order** they are built,
**how** each phase is checked, and **when** it counts as done. Names follow `docs/GLOSSARY.md`. "I" = the user; "Claude" = the
builder. It replaces "10.4 coding order" (roadmap section 10).

## 1. How we work

Every phase goes through the same loop:

1. **Build** — Claude builds the whole phase in one autonomous session, on its own branch: tests first, then code, small commits,
   pushed to GitHub.
2. **Audit** — Claude gives me an audit prompt (section 4). I run it in a **separate session** and bring back the findings.
3. **Fix** — Claude fixes the findings; all tests pass.
4. **Mac check** — I run the phase's real check on my Mac (Cursor): real data, real services, about 10–30 minutes.
5. **Merge** — Claude updates the docs (`AGENTS.md` status; new names in `GLOSSARY.md`); I merge the pull request with
   **"Squash and merge"** → **one commit per phase on main**.
6. **Air** — once its Mac check passes, the phase goes to the Air (`git pull`, the setup command of that phase).

A new phase starts only when the previous one is done (`AGENTS.md`, fixed rule 5).

**Exception (my decision, 2026-10-04):** phase 1 is built before phase 0 is done — only phase 0's Mac and Air checks are left, the Air is not ready, and phase 2's real-model runs must happen before the Anthropic credit ends on 2026-10-19; phase 1 does not need the Air (tested here on sample data); the Mac checks of phases 0 and 1 are done together, phase 0's Air check when the Air is ready.

## 2. Where things run

| Where | Who | What | Data |
|---|---|---|---|
| Cloud session | Claude | builds the phase, runs the automated tests | saved sample data (`tests/fixtures/`), fake AI |
| My Mac (Cursor) | me | the real check (UAT): real SEC, Yahoo, AI, Drive, the sites | the development database · `Investing-dev/` in Drive |
| The Air (Hermes) | the system | runs everything 24/7 | the real database (`~/investment-agents-data/`) · `Investing/` in Drive |

- **Mac and Air never write to the same Drive folder (decision: 2026-10-04; roadmap section 5):** on the Mac `DRIVE_DIR` is
  `…/My Drive/Investing-dev`; only the Air writes to the real `Investing/`. Cards are append-only, so a Mac test card mixed into
  a real card could not be deleted.

- **The database file never goes to GitHub.** GitHub carries the code that creates it: the table structure and the numbered
  upgrade steps. On the Mac and on the Air one command creates or upgrades it (`uv run python -m shared.db init`); no data is
  lost on an upgrade.
- The cloud environment blocks Yahoo Finance (network setting) and SEC is untested there. Automated tests therefore use saved
  sample data; anything that needs the real service is part of the Mac check. The one-time download of that sample data:
  section 6.

## 3. Rules for every phase

- **Tests first, then code.** Each rule the phase relies on gets a test or, if it needs a real service, a line in the Mac check.
  The audit checks that every listed rule has one.
- **Saved sample data:** small trimmed copies of real answers (SEC, Yahoo, site pages, AI answers) in `tests/fixtures/`, each with
  its source and date. No secrets.
- **AI in tests is fake** (fixed answers). Real AI calls happen only in Mac checks and on the Air.
- **Names:** `GLOSSARY.md` is the lock. A new name is added to it in the same phase that creates it.
- **Rules live in the roadmap.** If building shows a gap or a needed decision, Claude stops and asks; the roadmap changes first
  (with my OK), then the code. No rule is invented in code.
- **Stop rules:** the same error 3 times → stop and report · a test that needs the real service → move it to the Mac check, never
  fake a pass · a test is never weakened to make it pass.
- **Always true:** append-only where the rules say so (cards, ledgers; `/undo` marks `void`, never deletes) · missing ≠ 0 · every
  job writes a `runs` row · messages are printed text that Hermes delivers · each agent also runs by hand
  (`uv run python -m agents.<agent>`) · all system output in English · secrets only in `.env` · every new changing command
  also gets its `/undo` path (roadmap 10.2; phase 0's `/undo` handles only rows with `void`).
- **Git:** one branch per phase (e.g. `claude/phase-0-foundation`); small commits during the phase; one squash-merge at the end.

## 4. Audit prompt (template)

At the end of each phase Claude fills this in and gives it to me:

```text
You are auditing phase <N> ("<name>") of the repo jansoganci/investment-agents, branch <branch>.
Read AGENTS.md, docs/IMPLEMENTATION_PLAN.md (phase <N>) and the roadmap sections listed under "Relies on".
Do not change anything; only report.

Check, item by item:
1. Every item under "Builds" exists and works as described.
2. Every rule under "Relies on" is implemented: name the code and the test (or the Mac-check line) that covers it.
   List every rule with no code, or no test.
3. Run `uv run pytest -q` and report failures.
4. Names follow docs/GLOSSARY.md; every new name was added to it.
5. Nothing outside the phase was added; no rule was changed in code without a matching roadmap change.
6. Data safety: append-only where required, nothing deleted or overwritten, missing ≠ 0, no secret in the repo.
7. Anything that would break on my Mac or on the Air (paths, the time zone, missing setup steps).

Answer in Turkish. Output: a table — # · severity (blocker / should-fix / note) · rule or item · file:line · what is wrong ·
suggested fix. Then a short list "Not checked" with the reason.
```

## 5. Phases at a glance

| # | Phase | Main result | Real check |
|---|---|---|---|
| 0 | Foundation and the message path | database, settings, backup, commands, Drive + Telegram path | Air step 0; a test message reaches Telegram |
| 1 | Agent 3 — the numbers | SEC → 10 measures → type → grade → price line → `card.md` | golden set on live data; cards for 3–5 stocks in Drive |
| 2 | Agent 3 — AI answers and the auditor | "why?" answers with quotes, first thesis, sell suggestions, auditor | the 20-stock acceptance test |
| 3 | Agent 4 — Portfolio | ledger, value, SPY / gold shadows, total wealth, new money, drop alert | ledger test against my spreadsheet |
| 4 | Agent 1 — Eye | both sites read 3 times a day; one sentence; tags | one week of passes without a block |
| 5 | 1B Counter + agent 2 — Research | ranking, scores with reasons, card birth, "added by me" | one real Sunday report |
| 6 | The Sunday chain and go-live | everything scheduled on the Air, the summary, alerts | one full Sunday end to end |

**Why this order:** the database first — it is the contract between the agents (they talk only through it) · agent 3 next — the
core, already prototyped, and its real-model runs fall before 2026-10-19 (my note on the API credit) · Portfolio before the Eye —
code only, testable here, needed from my first purchase · the Eye needs my site login and the real sites, so it comes when the
base is stable · agent 2 needs the Eye's articles.

## Phase 0 — Foundation and the message path

**Purpose:** one base that every agent uses, and a proven path from our code to Drive and Telegram.

**Relies on:** `AGENTS.md` (folders, settings, secrets) · roadmap section 4 · section 5 (storage, database decisions) · section 3
"Telegram and Hermes" (how messages travel, free questions) · section 3 "Rules that prevent spending" (`runs`) · section 10.2
rules (confirmation, log, number, `/undo`) · `docs/AIR_SETUP.md`.

**Builds:**
- Project files: `pyproject.toml` (uv), `settings.yaml` (hours, paths, the 800,000 $ goal, dividend withholding 20%, the model
  and provider lists of section 10.1 copied as they are), `.env.example`.
- `shared/db`: every table of section 5 (stock identity = an internal number + CIK); a version number and numbered upgrade steps;
  WAL + a wait time; times in UTC; `uv run python -m shared.db init | upgrade | info`.
- `shared/backup`: the nightly copy with SQLite's own backup command into `Investing/Backup/`; keeps 7 daily + 4 weekly.
- `shared/runlog`: every job writes a `runs` row (start, end, `ok` / `error`, dollars).
- `shared/notify`: the format of the text a job prints; Hermes delivers it to Telegram.
- `shared/drive`: the `Investing/` paths (`Inbox/`, `Weekly/`, `Backup/`, `Stocks/<TICKER> - <Company name>/card.md`).
- `shared/commands`: what Hermes calls (`uv run python -m shared.commands <name> …`). A changing command first prints exactly what
  will change (preview) and runs only after my `yes`; it writes `command_log` with a number. `/undo` marks `void`, never deletes.
  First commands: `/help`, `/status`, `/undo`.
- `shared/ask`: the read-only way for my free questions (a read-only database connection + reading the cards).
- Step-0 helpers (`AIR_SETUP.md`, "Prepared by Claude"): the Drive test script (writes a dated file into `Inbox/` and prints a
  message), the `/setcommands` text.

**Tests (here):** `init` creates every table · an upgrade step keeps every row · WAL is on · a backup copy opens and retention
keeps 7 + 4 · a command writes `command_log`; `/undo` marks `void` and deletes nothing · `shared/ask` cannot write.

**Mac check:** `uv sync` · `.env` with `DRIVE_DIR` = `…/My Drive/Investing-dev` (never the real `Investing/`) ·
`uv run python -m shared.db init` → the development database appears · `uv run pytest -q` passes.
**Air:** `AIR_SETUP.md` phases 1–7 — Hermes answers on Telegram; the scheduled test script's file shows up in Drive and its
message arrives on Telegram.

**Done when:** the tests pass, the audit has no blocker, the Mac and Air checks pass.

**Not in this phase:** agent logic, AI calls, prices.

**Result (2026-10-04):** built; audited in a separate session — no blocker; fixes pushed to PR #3 (85 tests). The audit added:
upgrade steps that take the write lock and check every link (a table can be rebuilt) · the database itself refuses deletes in
`holdings`, `other_assets`, `card_entries`, `command_log`, `prices` and overwrites in `prices` (version 2) · a 5 s limit on free
questions · no database inside Drive · the backup as one file · the time zone from `settings.yaml`. Decided with it (roadmap
10.2): the lock on my `yes` is Hermes's approval mode (rule 4; Air test 7) · the number is shown when the change is done · an
`/undo` cannot itself be undone. Moved to later phases: marked "from phase 0" in phases 1 and 6.

## Phase 1 — Agent 3: the numbers (no AI)

**Purpose:** from SEC filings to a card with the 10 measures, the Lynch type, the grade, the flags and the price line — all
computed by code.

**Relies on:** roadmap section 3 "Agent 3 rules" (approach 1–2 and 6, the 10 measures and formulas, thresholds, debt, type rules,
decisive measures, grade rule, flags, price line, valuation, SEC synonym method, quarterly updates) · "Card format" · "Stock
states" · section 5 (one price job, price history) · `BAGLAM.md` section 9 (golden set and its lessons).

**Builds:**
- `shared/sec` (shared because agent 2's quick health uses it too): companyfacts + submissions (SIC) with the SEC contact from
  `.env`; synonym lists per figure for `us-gaap` and `ifrs-full`, tried year by year; debt groups (all parts required) + the
  candidate check; liquid assets = the parts added; missing → `not_computed` + a `missing_data` row; 10-K / 20-F annual and the
  last 4 quarters from 10-Q (Q4 by subtraction); the trace (tag + filing) of every figure.
- `shared/prices`: the one price job (03:00 Turkey time) — the previous day's closes for my stocks, the green list, SPY, gold,
  USD/TRY, the 11 sector funds and the linked commodities; split and dividend history; one ticker on demand; history kept.
- `agents/analysis`: the 10 measures, the type, the decisive measures, the grade (shrink rule, fast-grower safety), the flags, the
  price line (PEG with growth capped at 25%, Lynch's dividend ratio, FCF yield on the 3-year average) → `financials`,
  `card_entries`, `stocks`; the card writer (`card.md`: header updated only by code, the YAML data block, fixed headings,
  append-only); a bare card when a stock has none yet (until agent 2 exists); the weekly "is there a new filing?" check for
  watched stocks (archived stocks are never analyzed); `uv run python -m agents.analysis KO`.
- Commands: `/watch` (state only for now), `/archive`, `/unarchive`, `/analyze` (numbers), `/card`, `/green`, `/missing`, `/data`
  (plausibility check, `source: user`). Each changing one gets its `/undo` path (a state change goes back with a dated card
  note — roadmap 10.2). `/analyze` writes no `runs` row itself; the agent it runs does.
- Saved sample data: trimmed SEC and Yahoo data for the golden set, Novo Nordisk and the trap cases.

**Decided first (from phase 0; my decision 2026-10-05):** the out-of-scope label lives in a field of its own,
`stocks.out_of_scope`, set by code from the SIC code (roadmap section 3, "Agent 3 rules", approach 2); a new upgrade step adds the
field. Market value = Yahoo's ready-made value; if it is missing, the price line stays `not_computed` (roadmap section 3,
"Valuation"). For the Mac check, one of my 3 stocks can be a bank (e.g. JPM) to see the out-of-scope path.

**Tests (here):** the golden set — all 10 get the expected grade and type (`BAGLAM.md` section 9) · Novo Nordisk works (IFRS,
DKK in the price line) · KO liquid assets = cash + short-term investments · Boeing's debt group needs all parts · Pfizer 2020 debt
· Nvidia's ×10 split confirmed by Yahoo · a reverse split · the IPO year skipped · missing ≠ 0 everywhere · the last 4 quarters
from cumulative 10-Q figures · a second run appends a dated entry and deletes nothing.

**Mac check:** live SEC + Yahoo for KO, NVDA and 3 stocks I choose — the cards open in Drive (`Investing-dev/`) and read well;
the golden set on live data (a changed grade must be explained by a new filing). How: `uv run python -m shared.prices --ticker KO` ·
`uv run python -m agents.analysis KO`. Also once: `uv run python tests/fixtures/fetch_yahoo.py` (Yahoo refused the cloud
machine), then push the saved files.

**Done when:** the tests pass, the audit has no blocker, the Mac check passes.

**Not in this phase:** AI answers, the auditor, sell suggestions (phase 2) · the portfolio (phase 3).

## Phase 2 — Agent 3: AI answers and the auditor

**Purpose:** the card explains itself — "why?" answers with quotes, the first thesis, the thesis check, sell suggestions with
their evidence — and the auditor checks the expensive parts.

**Relies on:** roadmap section 3 "Agent 3 rules" (approach 3–5) · "When to consider selling" (triggers, the crash rule, evidence,
the `data_check` warning) · "AI auditor" (cards 1–3, when it runs, on a fail, error test sets) · "Telegram and Hermes"
(missing-data requests) · section 10.1 (models, provider order, costs to `runs`, the strong-model test) · section 10.2.

**Builds:**
- `shared/ai`: one client with the ordered provider list from `settings.yaml` (my credits first, then OpenRouter), the `/model`
  override (`settings` table), every call's cost into `runs`, a fake mode for tests.
- Agent 3's AI parts: the "why?" answers (a quote from the filing for every ❌ and every flag); the first thesis (at most 3 reasons
  + 3 things that would break it); the thesis check on later entries (`thesis_status`: `intact` / `broken` / `watch`); the
  drop-alert check (the latest filing + the latest news; news only says "watch") — it takes a `drop_alert` signal from
  `pending` to `done`.
- Code checks first: every quote must appear word for word in its source.
- `shared/auditor` with rule cards 1–3 in `shared/auditor/cards/` (figure, reading, sell-suggestion audits): runs on a first card,
  an open `data_check`, before every sell suggestion, on `solid` ↔ `weak`, and on a random 1 in 5 updates; on a fail →
  `unverified` on the card + a message, a sell suggestion held; results in `audits`.
- Sell suggestions: the thesis broke / the grade fell to `weak` / `mid` 2 quarters in a row after `solid` → a "consider selling"
  message with its evidence and, if a `data_check` flag is open, "check the figure before acting".
- Missing-data requests: the plain message (stock, figure, year, why, where to find it, how to answer).
- Commands: `/closewarning`, `/thesis`, `/note`, `/model`, `/spend`; `/analyze` shows the estimated cost in its confirmation.
- The strong-model test (section 10.1): two companies' "why?" answers side by side, without model names; I choose.

**Tests (here, fake AI):** each card's error test set is caught (KO and NVDA liquid assets, Boeing debt, Pfizer 2020 debt; NET's
general risk sentence; an invented quote) · a quote missing from the filing is rejected by code · a sell suggestion is held when
the audit fails · costs land in `runs`.

**Mac check:** **the 20-stock acceptance test** (roadmap section 8, step 1): figures compared by hand with the 10-K / 20-F — liquid
assets and total debt against the balance sheet, flagged rows first; the trap examples classified correctly; 3 cards readable in
Drive; the strong-model test. The real-model runs happen before 2026-10-19.

**Done when:** the tests pass, the audit has no blocker, the acceptance test passes.

**Not in this phase:** agent 2's event audit (card 4, phase 5).

## Phase 3 — Agent 4: Portfolio

**Purpose:** my money in one place — the ledger, value and weights, the SPY and gold comparison, total wealth against the goal,
where new money could go.

**Relies on:** roadmap section 3 "Agent 4 rules" (rules 1–9, storage, output, test) · section 5 (one price job, TL entries keep the
amount + the rate, price history) · section 10.2 (`/bought`, `/sold`, `/gold`, `/bes`, `/portfolio`, `/undo`) · the "AI auditor"
table rows for agent 4 and the Hermes commands.

**Builds:**
- `agents/portfolio`: the ledger from `holdings` (buy, sell; dividends with 20% withholding and splits added by code); value,
  weights in the stock portfolio, gain / loss; the SPY and gold shadows; the return (total for the first 12 months, then `xirr`);
  total wealth (stocks + gold + BES from `other_assets`) against 800,000 $; weekly `snapshots`; the new-money list (weekly; the
  25% rule with the "Not suggested" line, `weight_cap`); the drop alert (−20% from the 52-week high weekly close → a `pending`
  signal for agent 3; none in a split week); the valuation watch (PEG > 3 or FCF yield < 1% for 4 weeks); the portfolio block.
- Commands: `/bought`, `/sold` (cannot exceed what I hold; a price more than 20% from that day's close → "are you sure?"),
  `/gold`, `/bes`, `/portfolio`.

**Tests (here):** the hand-checked ledger (two buys, a sale, a dividend, a split) equals a spreadsheet · the shadows follow the
same money on the same days · no yearly figure before 12 months · the 25% line appears · no drop alert in a split week · `/undo`
of a wrong buy, with the right one added after my `yes`.

**Mac check:** my own test ledger against my own spreadsheet; `/portfolio` reads well. How:
`uv run python -m shared.commands bought 10 KO 85.65` · `uv run python -m agents.portfolio`.

**Done when:** the tests pass, the audit has no blocker, the Mac check passes.

**Not in this phase:** any sell suggestion (never from agent 4).

## Phase 4 — Agent 1: Eye

**Purpose:** both sites read three times a day, slowly, with one neutral English sentence per post and tags mapped to stocks,
commodities and sectors.

**Relies on:** roadmap section 3 "Agent 1 rules" (1–9) · "Sector list" · the "AI auditor" table row for agent 1 · section 4 (site
reading, permission) · section 10.1 (the cheap model and its test).

**Builds:**
- `agents/eye`: new posts since the last pass from the sitemap; Playwright with my stored login; 20–30 seconds between pages, at
  most ~80 pages a pass; stop at once on "too many requests" / "access denied" + a message; plain text only; glossary posts
  skipped; `articles` (full text, `read_deep`, `text_missing`); one neutral English sentence (cheap model); the daily list in
  `Inbox/`.
- Tag mapping (`tags`): a new tag is classified once (company / commodity / sector); a company tag counts only if the ticker is in
  SEC's company list and the name is close, otherwise it waits and the Sunday summary asks me; subsectors only from the approved
  list (`subsectors`; `other` → "add a new subsector?").
- Commands: `/tag`, `/subsector`.
- The cheap-model test (section 10.1): 20 real posts, the sentences side by side; I choose.

**Input needed first:** the first subsector list.

**Tests (here):** saved sitemap and post pages · only new posts are taken · the stop-on-block rule · glossary posts skipped · text
extraction · tag mapping and the SEC name check.

**Mac check, then the Air:** one login; one week of passes fills `articles` with no block (roadmap section 8, step 2).

**Done when:** the tests pass, the audit has no blocker, the one-week check passes.

## Phase 5 — 1B Counter + agent 2: Research

**Purpose:** every Sunday the most-mentioned US stocks are read, scored with reasons and get a card; a stock I add myself goes the
same way at once.

**Relies on:** roadmap section 3 "Agent 1B rules" · "Agent 2 rules" (1–7, including "a stock I add myself") · "Score rules" (5
criteria, thresholds, the serious-negative list, quick health, `unclear` = 1) · "AI auditor" card 4 · section 10.2 (`/candidates`,
`/watch` for a stock with no card).

**Builds:**
- `agents/counter`: a rolling 7 days, distinct posts, only US-listed stocks in the ranking (ADRs included), the 30-day count
  beside it, stocks with a card left out with the "mentioned a lot" line, the non-US information line.
- `agents/research`: at most 10 stocks; reading against set questions with a quote for every claim (`read_deep`); tone per post;
  news flow (web search, a source for every event, `company_specific` / `general_risk`, serious negatives checked by the auditor,
  card 4); sector tailwind from `prices`; quick health from `shared/sec`; the commodity link (one web search, `commodity_links`);
  the score computed by code from the labels, a reason for every criterion → `scores`; the card is born (research entry),
  status `candidate`; the `Weekly/` report.
- "Added by me": `/watch X` with no card → agent 2 for X alone (web search; `mentions` = 0, `tone` = 1) → `added_by: user` →
  `watching` → agent 3.
- Commands: `/candidates`; `/watch` completed.

**Tests (here):** the counting rules on saved articles · the score arithmetic from labels · `unclear` = 1 · the event audit's error
set (another company's news, a 3-year-old event) · the "added by me" path.

**Mac check, then the Air:** one real Sunday run — the weekly report in Drive and on Telegram, candidate cards open (roadmap
section 8, step 3); one stock I add myself, end to end.

**Done when:** the tests pass, the audit has no blocker, the Sunday check passes.

## Phase 6 — The Sunday chain and go-live

**Purpose:** everything runs on its own on the Air, in the decided order, and reaches me on Telegram.

**Relies on:** roadmap section 3 "Flow" and "Sunday order" · "Telegram and Hermes" (when a message arrives) · "Rules that prevent
spending" · section 5 (backup) · section 6 (spend limit, the 10 $ warning) · section 8.

**Builds:**
- The schedule on the Air (Hermes script-only jobs): 03:00 prices · the backup after it · the Eye at 07:00 / 13:00 / 20:00 ·
  Sunday: Counter → agent 2 → agent 3 (new filings) → agent 4 → the summary.
- `shared/summary`: the Sunday summary from the database (new candidates, card changes, stocks with a card mentioned a lot,
  non-US names, data still `unclear`, missing-data requests, subsector questions, archive reminders, the portfolio block, spend);
  `/summary`.
- Immediate messages: a holding's grade drops, an agent error, a new `solid` (green list), a drop alert, an auditor disagreement,
  the 10 $ spend warning.
- From phase 0 (audit, 2026-10-04): a real time for the backup in `settings.yaml` (today `after prices`; set once the price
  job's length is known) · `/status` warnings for a job stuck in `running` and for a backup that is too old — the limits are
  my decision then (suggested: 1 hour and 36 hours).

**Tests (here):** the summary from a saved database · when one step fails, the rest still runs and reports the error.

**Air check:** one full Sunday end to end; a forced error reaches Telegram; after a restart everything starts again; a job
left stuck on purpose shows in `/status`.

**Done when:** the checks pass. Then: a few months of real use without changing the rules (`AGENTS.md`).

## 6. Open inputs

- **The subsector list** — needed before phase 4.
- ~~**Where the out-of-scope label is stored**~~ — decided 2026-10-05: `stocks.out_of_scope`, set by code from the SIC code
  (roadmap section 3, "Agent 3 rules", approach 2).
- ~~**Where the market value comes from**~~ — decided 2026-10-05: Yahoo's ready-made market value (USD); if it is missing → `not_computed`
  for now (roadmap section 3, "Valuation"; the fallback is in section 8).
- **Sample data for phase 1** — needed before phase 1. The build session downloads real SEC and Yahoo answers once. Claude's
  recommendation: I allow these hosts in the cloud environment's network setting (environment menu in the session's title bar
  → Edit → Network access → Custom, keeping the default package-manager list): `data.sec.gov`, `www.sec.gov`,
  `query1.finance.yahoo.com`, `query2.finance.yahoo.com`, `fc.yahoo.com`. Otherwise Claude writes a download script that I run
  on my Mac and push. SEC also asks for a contact line (`SEC_UA`); the phase 1 session asks me for it.
  **Decided (2026-10-04): the network setting** — the five hosts are open since 2026-10-05; `SEC_UA` given (local `.env`
  only). SEC data downloaded (`tests/fixtures/sec/`, 13 companies). Yahoo refused the cloud machine ("too many requests") →
  its sample answers come from my Mac (section 8).
- ~~**The sector before the Eye exists**~~ — decided 2026-10-04 (roadmap section 3, "Sector list"): taken from the SEC
  industry code (SIC) through a fixed table; I can correct it. The Eye's tag mapping takes over in phase 4.
- **The third external review** — if it arrives before phase 1 is merged, its accepted points go into phase 1; later, into a fix of
  its own.

## 7. Phase status

✅ done · ⏳ waiting (the note says on what) · — not started. The steps are the loop of section 1.

| Phase | Build | Audit | Fixes | Mac check | Merge | Air | Branch / PR | Note |
|---|---|---|---|---|---|---|---|---|
| 0 | ✅ | ✅ no blocker | ✅ | ⏳ | ✅ | ⏳ | `claude/phase-0-foundation-arj800` · PR #3 (merged 2026-10-05) | merged before the Mac check (my decision, 2026-10-05): the Mac check runs on `main`, a fix comes as a small PR · Air setup started 2026-10-05 (`AIR_SETUP.md`) |
| 1 | ✅ | ✅ no blocker | ✅ | ⏳ | ✅ | ⏳ | `claude/phase-1-analysis-numbers-arj800` · PR #4 → PR #5 (merged 2026-10-05) | built and audited 2026-10-05 (exception, section 1) · PR #4 went into the phase 0 branch, PR #5 brought it to `main` · Mac check together with phase 0's, on `main` (incl. the real Yahoo answers, section 8) · on the Air: `git pull` + `uv run python -m shared.db upgrade` (version 2 → 3) |
| 2 | — | — | — | — | — | — | — | real-model runs before 2026-10-19 |
| 3 | — | — | — | — | — | — | — | |
| 4 | — | — | — | — | — | — | — | needs the Air (one week of passes) and the subsector list |
| 5 | — | — | — | — | — | — | — | needs the Air (a real Sunday) |
| 6 | — | — | — | — | — | — | — | runs on the Air |

## 8. Not now — on purpose (2026-10-05)

What we deliberately do not do now, why, and when it comes back. Claude does not start any of these on its own; taking an item
off this list is my decision.

**Waiting — the next step depends on something else:**

| What | Why not now | Comes back when |
|---|---|---|
| Saved Yahoo answers for the tests (`tests/fixtures/yahoo/`) | Yahoo answered "too many requests" to the cloud machine for hours; the price job is tested on an answer built by hand in Yahoo's format | the Mac check runs `uv run python tests/fixtures/fetch_yahoo.py` once and pushes the files |
| Yahoo answers HTTP 429 on the Air and on the cloud machine (2026-10-06) | cause not found (not our request headers; the Air has no VPN); until it works there is no price line and Nvidia's share count cannot be confirmed (a split) | the same `curl` test on the main Mac; if Yahoo is blocked for good, I choose another price source |
| The Mac check of phases 0 and 1 | both are merged into `main` (2026-10-05, before the check — my decision); the check is still owed, on `main` | next, on my Mac; a fix comes as a small PR |
| Finishing the Air setup (`AIR_SETUP.md`) and phase 0's Air check | started 2026-10-05; done: tools, project, Drive, Telegram, `.env`, 216 tests, the real data check (2026-10-06). **First next: limit Hermes (phase 5, in the Air's terminal)**, then OpenRouter and the tests (phases 6–7) | at the latest before phase 4 |
| The third external review | it has not arrived | it arrives: before phase 1 is merged → into phase 1; later → a fix of its own |

**Moved to a later phase (from phase 0's audit):**

| What | Why not now | Phase |
|---|---|---|
| A real time for the backup in `settings.yaml` (today `after prices`) | the price job does not exist yet and its length is unknown; scheduling is phase 6's work | 6 |
| `/status` warnings: a job stuck in `running`, a backup that is too old | they matter only when jobs run on their own; the limits are a new rule I decide then (suggested: 1 hour, 36 hours) | 6 |
| `/undo` for the other commands | phase 0's `/undo` handles rows with `void` only; each phase adds the path for its own commands (section 3) | each phase |
| The subsector list | only the Eye uses it | before 4 |
| What to do when Yahoo has no market value | rare; until then the price line says `not_computed` (null) | my decision, later |
| Stock comp from Yahoo when SEC has none (roadmap "Free cash") | decision 2026-10-05: not now; the gap goes to `missing_data` and I can enter it with `/data` | later |
| The IPO year from the first S-1 / F-1 instead of the first annual report in SEC's data | phase 1 audit note; today NVO's share count spans 3 years, not 5 | later |
| Fixed warning codes (U1 stays U1 on every entry) and `flag_kind` | needed by `/closewarning` and the AI reading | phase 2 |
| A line when a new filing's figures have not reached SEC's data for 2+ weeks | the weekly check waits silently today | phase 6 |
| `absent` for a figure a company never reports (the ledger asks again each quarter) | comes with the Telegram requests for missing data | phase 2 |
| A guard that the Mac never writes into the real `Investing/` | today only `.env` keeps them apart (optional idea) | later |
| Small UAT items: info line for debt held for sale, a flag for a margin outside 0–100%, Coca-Cola's short-term borrowings name | each under 1%; checked in the 20-stock acceptance test | phase 2 |

**Not in version 1 — roadmap decisions; we stay away:**

| What | Why | Decided in |
|---|---|---|
| Hong Kong / China A-shares (and reading their PDFs) | US markets first; added once the system is settled | roadmap sections 1 and 9 |
| Lynch types `turnaround`, `asset_play` | kept out of version 1 → `unclear` | roadmap section 3, "Agent 3 rules" (approach 1) |
| Analysing banks, insurers, REITs, `pre_revenue`, utilities | the 10 measures do not fit them → "unclear — out of scope" | roadmap section 3, "Agent 3 rules" (approach 2) |
| Hidden assets; a company's real value vs its market value | hard and error-prone for an AI; would make version 1 harder | roadmap section 3, "Not in version 1" |
| Selling on a market filter; "shrink, not sell" on a macro reason | the backtests: it costs return; option A chosen; the macro idea is for later | roadmap section 3, agent 4 rule 8 |
| A web interface / blog | Markdown with a `publish` header is enough for now | roadmap section 4 |
