# AGENTS.md — investment-agents

A personal investment-advisor system: 4 agents read, research, analyze, and suggest.
**The user always makes the decision and places the trades.**

Names of fields, tables, grades, and folders follow `docs/GLOSSARY.md`.

## At the start of every session

1. Read `docs/YOL_HARITASI_v2.md` — purpose, rules, decisions, steps, and open topics are there.
2. Read the **Current status** section at the end of this file.
   When the talk is about the profile, the goal math, backtest results, lessons from the old system, or a card / score / technical rule, also read `docs/BAGLAM.md`.
3. Do not make the user explain the process again. If something is missing, ask one clear question.

## Fixed rules

1. Agents only **suggest**. A broker or bank password never enters the system.
2. Green list ≠ buy. A score is a ranking; every score has a required `reason` sentence next to it.
3. `card.md` is append-only. Old entries are not deleted; every entry is dated.
   One exception: the header shows the current state (`status`, `in_portfolio`, `lynch_type`, `grade`, `last_entry`) and only code updates it; every change is also appended as a dated note.
4. Agents do not know each other; they communicate only through files / SQLite.
5. A new feature is added only after the current step counts as "done".

## How to work

- Speak to the user in **Turkish**, plain, so a beginner can follow. No needless jargon.
- Documents, field names, and new code use the English names in `docs/GLOSSARY.md`.
- Do only the work that was asked. Do not add or remove a feature, and do not widen the scope. If you are unsure, ask.
- The decision is the user's: if there is a choice, state your recommendation and leave the decision to them.
- Simplicity first: if something feels complicated, simplify it before adding it.
- "Think fast, iterate faster": if version 1 of a rule is good enough, move on. Do not wait for perfect. Build it and fix it.
- Each agent is its own module. Code used by more than one agent goes under `shared/`.
- The code does not know Hermes. Each agent must also run by hand. Planned command: `python -m agents.<agent>`. New code lives under `agents/` and `shared/`; `ajanlar/` keeps only the archived prototype and backtests.
- At the end of the session, update the **Current status** section.

## Project map

Names follow `docs/GLOSSARY.md`. New code goes directly under `agents/` and `shared/` (decision: 2026-10-04); `ajanlar/` is an
archive. Do not move or rename the archive unless that is the task.

```text
Exists today:
ajanlar/analiz/prototip/   agent 3 rule trial (archive, not production)
ajanlar/teknik/backtest/   backtest scripts (archive)
docs/                      YOL_HARITASI_v2.md, IMPLEMENTATION_PLAN.md, BAGLAM.md, GLOSSARY.md, TASINANLAR.md, DIS_INCELEME_PROMPT.md, AIR_SETUP.md,
                           telegram_setcommands.txt; reviews/ (external reviews)
shared/                    phase 0: config, clock, db (tables + upgrade steps), backup, runlog, notify, drive, commands, ask
                           phase 1: sec (client, facts, synonyms), sectors, prices (job + yahoo), commands/stocks.py
agents/analysis/           phase 1: agent 3's numbers — measures, card, run; python -m agents.analysis KO | --weekly
tests/                     uv run pytest -q; sample data in tests/fixtures/ (sec/, yahoo/)
pyproject.toml, uv.lock, settings.yaml, .env.example

Planned (not created yet):
agents/eye/         1. Eye — reads Emtia Defteri + Dragonomi, writes one sentence (3 passes a day)
agents/counter/     1B. Counter — counts stocks / sectors / commodities over the last 7 days (code, no AI)
agents/research/    2. Research — reading + web search + score; opens the card (weekly, Sunday)
agents/portfolio/   4. Portfolio — my money: ledger, benchmark, total wealth, new money
shared/             still to come: AI, the auditor, the Sunday summary
```

## Technical

- Python, environment managed with `uv`. Example: `uv run --with pytest pytest -q`
- Development is on the main Mac. The system runs on the backup MacBook Air (Hermes). The bridge is GitHub. No code is written on the Air.
- SQLite lives on the Air's disk (`~/investment-agents-data/`). It does **not** go in the Drive folder (sync can corrupt it). A backup is copied to Drive at night. The main Mac has its own development database; the two never mix.
- Reports and the card are Markdown plus a header (`ticker`, `sector`, `opened`, `publish: no`). The format is roadmap section 3, "Card format". Figures live only in the YAML data block.
- On Telegram the user's only counterpart is Hermes. Hermes runs only the defined command list. It does not change code or rules.
- Model and budget settings live in one place: `settings.yaml` (renamed from `ayarlar.yaml` on 2026-10-04; the file is created with the first code). The AI budget is at most 25–30 $ / month.
- Secrets (API keys) are in `.env`. They are never committed.

## Old project

`../investment-intelligence` (git tag `v1-arsiv`) is only a source library.
Do not add it to the workspace. Do not apply its rules or documents to this project.
If a file is needed, read it by its full path, copy only the piece that is needed, and add a line to `docs/TASINANLAR.md`.

## Current status

- **Last update:** 2026-10-05 (phases 0 and 1 merged into `main`; Air setup through Drive and Telegram; Hermes limits are next)
- **Card heading:** `### Thesis` stays short. Under it: why it is owned (at most 3 points) and 3 things that would break the thesis. Record heading: `## <date> · <record> · <who> [· <source>]` (`source` only on `fundamental`). Locked in `GLOSSARY.md`, roadmap section 3, and `BAGLAM.md` section 7.
- **Glossary:** `docs/GLOSSARY.md` is the lock. Documents and new code use the right-hand column as the only name. Three names are approved: `card.md`, `Investing/`, Eye. Folders and the trial code are not renamed yet. English: `docs/TASINANLAR.md`, `docs/YOL_HARITASI_v2.md`, `docs/BAGLAM.md`, `docs/DIS_INCELEME_PROMPT.md`, this file. External reviews live in `docs/reviews/` (see its README: keep the original, translate into a separate file); a review is input, not a rule change.
- **Done:** The project was opened. The roadmap and `BAGLAM.md` were written. The backtest scripts were brought over.
  The decision order was set (roadmap section 9) and item 1, **overall frame**, is closed:
  the card is the stock card, "think fast, iterate faster", the site owner allowed reading,
  development on the main Mac / running on the Air.
  Item 2, **architecture**, is closed (roadmap section 3): flow, stock states (`candidate` / `watching` / `archived`,
  grade, `in_portfolio`), starting to watch is manual, solid → green list is automatic, agent 3 runs on an event,
  one counterpart on Telegram (Hermes) plus a command list, a trial-set test for agent 3.
  Item 3, **agent 1 (Eye)**, is closed (roadmap section 3, "Agent 1 rules"): 3 passes a day, a slow scan
  (~20 min / pass, stop on a block response), the full text is read and a cheap model writes one neutral sentence, the full text
  is saved to `articles`, a tag-mapping table (company / commodity / sector), glossary posts are not taken.
  Item 4, **agent 2**, is closed (roadmap section 3): 1B Counter (code, a rolling 7 days, a stock that already has a card
  does not enter the ranking), a fixed 2-level sector list (GICS 11 + an approved subsector), agent 2 once a week,
  at most 10 stocks, it does not visit the site, reading with quotes, a commodity link (company → commodity, role), the card is born in agent 2,
  a flat Drive layout `Investing/Stocks/<TICKER> - <Company name>/card.md`, **score rules** (5 criteria × 0–2,
  with thresholds; if the data is missing, `unclear` = 1 point). **Version 1 is US markets only (ADRs included)**; HK / A-shares are added later.
  Item 5, **agent 3**, is partly closed (roadmap section 3, "Agent 3 rules"): quality first, Lynch types,
  out of scope for now (`bank` / `insurance` / `reit` / `pre_revenue` / `utility`), valuation = Lynch PEG + free-cash-flow yield (no hidden-asset / intrinsic-value calculation for now), code measures and raises questions, the AI writes the reason with a quote, 10 measures,
  an SEC synonym list (year by year), a `missing_data` ledger, debt is a ⚠ research item, UAT ≥ 20 stocks.
  Research notes: `docs/BAGLAM.md` section 8.
  Agent 3's **thresholds, type rules (plus `unprofitable`), grade rule, and price line** were written and tried on 10 real companies
  (results and lessons: `BAGLAM.md` section 9). The trial code started in a scratchpad; it now lives in `ajanlar/analiz/prototip/`.
  The external-review prompt was written: `docs/DIS_INCELEME_PROMPT.md` (English master) and `docs/reviews/review_prompt_v1_EN.md` (the earlier wording given to models;
  the answer is in Turkish). SEC data is not committed; it is downloaded with `indir.sh`.
  Further decisions: PEG growth capped at 25% plus Lynch's dividend-adjusted ratio (no analyst estimates) · stock comp is subtracted from free cash (SEC, Yahoo as fallback) · card format (a YAML data block, fixed headings; the header includes `lynch_type`, `grade`,
  `last_entry`) · missing data is requested on Telegram (on the "analiz et" command and on Sunday; the message is plain).
  Two external reviews read and applied (`docs/reviews/`; `BAGLAM.md` section 9): liquid-asset extraction fixed in the rules,
  missing ≠ 0, capital return = worse of 3y / 5y (cyclical 5y), new margin-stability definition, new type order + cyclical SIC list,
  fast-grower safety, 20-F + IFRS, FCF yield on 3-year average, PEG on EPS growth, flags, the AI writes the first thesis.
  The reviews expected `solid` KO, NVDA · `mid` NKE, SBUX · `weak` PFE, INTC, BA, SNAP, DOW, RIVN; after the rerun KO is `mid` (below).
  Prototype updated to the post-review rules; golden set 10/10 (`ajanlar/analiz/prototip/altin_set.py`): `solid` NVDA · `mid` KO
  (borderline, user-approved), NKE, SBUX · `weak` PFE, INTC, BA, SNAP, DOW, RIVN. IFRS / 20-F works (NVO). Rivian rule: a sector /
  SIC cyclical needs at least 1 profit year in 5 (user-approved, may be revised).
  Item 6, **agent 4**, mostly closed (roadmap section 3, "Agent 4 rules", 2026-10-04): a weekly price watcher, not a trading signal —
  new-money ranking (no new money above 25% weight; above 25% is fine), drop alert (−20% from the 52-week high → agent 3 thesis
  check), valuation watch (PEG > 3 or FCF yield < 1%, 4 weeks), weights in the Sunday summary (`holdings` via Hermes); the
  SPY 40-week filter was tested, not used (option A, below). Agent 3 reads 10-Q too (last 4 quarters, TTM); sell-review triggers recorded. SPY filter tests (34 / 40 / 55,
  Fibonacci daily / weekly) in `BAGLAM.md` section 3: plateau 21–55 weeks, 40 is the robust middle.
  Insurance simulation with monthly buying (`BAGLAM.md` section 3): user chose **A — no market-filter selling**. Agent 4 never says
  "sell" (valuation watch = info + back of the new-money queue); sell suggestions come only from agent 3 (thesis broke, `weak`,
  `mid` 2 quarters in a row) plus my own call. Later idea: shrink, not sell, on a macro reason (e.g. rising rates).
  Added (2026-10-04): the crash rule ("I do not sell because the market fell"), the drop-alert check reads the latest filing **and
  the latest news** (news only says "watch"), every sell suggestion comes with its evidence and a "check the figure" warning when a
  `data_check` flag is open.
  **Agent 4 renamed Portfolio (2026-10-04; roadmap section 3, "Agent 4 rules"):** the only agent that looks at my money — a
  ledger (`holdings`: buy / sell via Hermes, dividends and splits by code; starts empty, no stocks held), weekly value and weights,
  a benchmark with SPY and gold shadow portfolios (total return for the first 12 months, then `xirr`), total wealth (stocks + gold +
  BES; `/gold` per purchase with grams and the TL price, `/bes` monthly with the payment and the BES total, into `other_assets`;
  weekly `snapshots`) against the 800 thousand $ goal, the new-money
  ranking weekly with a "Not suggested (25% rule)" line (`weight_cap`). Code only, no AI; all figures in USD; prices fetched
  every night at 03:00 Turkey time (the previous day's close).
  User-confirmed: emergency cash is not counted as wealth; dividend withholding 20%; the new-money list stays weekly; no
  staleness rule for gold / BES (I enter them every month).
  Item 7 started — roadmap section 10. **10.1 models and providers decided (2026-10-04):** all system output and commands in
  English; cheap = DeepSeek V4 Flash, strong = Claude Sonnet 5.5 (high) with GPT-6 Sol fallback, Hermes chat = ChatGPT/Codex
  subscription if possible else DeepSeek V4 Pro; provider order = my API credits (Anthropic 90 $ until 10-19, DeepSeek 10 $,
  OpenAI 5 $) then OpenRouter; model change from Telegram via an override in the Air database; only needed data goes to models.
  **10.2 Hermes command list decided (2026-10-04):** 10 information commands + actions (`/watch`, `/archive`, `/unarchive`,
  `/bought`, `/sold`, `/gold`, `/bes`, `/analyze`, `/closewarning`, `/thesis`, `/note`, `/data`, `/tag`, `/model`, `/subsector`, `/undo`) in the Telegram `/` menu;
  every change asks for confirmation, is logged and gets a number (`/undo` uses it; nothing is deleted, rows are marked `void`).
  **10.3 Air setup checklist written:** `docs/AIR_SETUP.md` (to prepare before it: `.env.example`, `/setcommands` text, Drive test script).
  **AI auditor decided (2026-10-04; roadmap section 3, "AI auditor"):** one auditor (DeepSeek V4 Pro, fallback GPT-6 Sol — a
  different family from the writer), used only in agent 3 (figure, reading, sell audits) and
  agent 2 (serious-negative events); code checks elsewhere; one rule card per place with known traps and an error test set; on a
  fail `unverified` + Telegram, a sell suggestion is held; a big review every 6 months.
  **Document audit (2026-10-04):** all documents and the prototype checked; no rule error; stale lines fixed (golden-set line,
  SPY filter line, project map, agent 1 cost, Turkish example messages → English, `ortak` → `shared`, `buy` / `sell` names, the
  review prompt marked historical). Decided: DeepSeek's own API is used directly — where data is processed does not matter to the
  user; no more comments on model choices · `/undo` added (a correction always waits for my `yes`) · `ayarlar.yaml` → `settings.yaml` ·
  Sunday order: Counter → agent 2 → agent 3 → agent 4 → summary · messages reach Telegram through Hermes, built and tested first
  (step 0) · one shared nightly price job (03:00) for all prices · new code under `agents/` and `shared/`, `ajanlar/` is an archive ·
  database so far: times in UTC (shown in Turkey time), TL entries keep the TL amount and the rate, the Air's and the development
  databases never mix, stock identity = internal number + CIK (the ticker is a label), price history is kept (never overwritten),
  nightly backup to `Investing/Backup/` (last 7 daily + 4 weekly).
  **Also decided (2026-10-04):** the missing tables are added (`card_entries`, `audits`, `command_log`, `settings`, `subsectors`,
  a status on `signals`) · free questions: Hermes answers any question I ask, reading the database and the cards read-only;
  changes only through the command list · a stock I add myself (e.g. the abi's): `/watch X` with no card → agent 2 runs at once
  for X alone (card + research entry, web search for news, label "added by me", `added_by: user`), then `watching` and agent 3;
  agent 2's weekly run is unchanged · writing at the same time (WAL + a wait time) and structure changes (version number +
  numbered upgrade steps; data is never lost) — closed.
  **Implementation plan approved (2026-10-04):** `docs/IMPLEMENTATION_PLAN.md` — phases 0–6 (foundation and the message
  path · agent 3 numbers · agent 3 AI and the auditor · Portfolio · Eye · Counter + Research · the Sunday chain and go-live); each
  phase: built in one session → audited in a separate session (Claude gives the prompt) → fixes → my Mac check (Cursor) → one
  squash-merge into main → the Air. The sector before the Eye exists: from the SEC industry code (SIC) through a fixed table, I
  can correct it (roadmap section 3, "Sector list").
- **Phase 0 built and audited (2026-10-04)** on branch `claude/phase-0-foundation-arj800`, PR #3 (merged into `main` 2026-10-05):
  `pyproject.toml` (uv), `settings.yaml`, `.env.example`; `shared/db` (all 18 tables, version 2, numbered upgrade steps; an
  upgrade takes the write lock, runs with the foreign-key check off, checks every link before it commits and saves a copy first;
  WAL + 5 s wait; UTC times; stock = internal number + CIK; triggers refuse DELETE on `holdings`, `other_assets`, `card_entries`,
  `command_log`, `prices` and UPDATE on `prices`; `init | upgrade | info`); `shared/backup` (SQLite backup command →
  `Investing/Backup/`, one self-contained file, 7 daily + the latest copy of each of the 4 weeks before them); `shared/runlog`
  (`runs` row: `running` → `ok` / `error`, dollars); `shared/notify` (title line + plain lines, cut at Telegram's 4,096);
  `shared/drive` (paths + the step-0 test script `python -m shared.drive test`); `shared/commands` (all 25 menu commands
  listed; `/help`, `/status`, `/undo` built; a change prints a preview and runs only with `--yes`; `command_log` number; `/undo`
  marks `void`); `shared/ask` (read-only: `mode=ro` + `query_only` + an authorizer + a 5 s limit); `shared/config` refuses a
  database inside Drive; `docs/telegram_setcommands.txt`. New names in `GLOSSARY.md` ("Kod ve veritabanı adları"). 85 tests pass.
  **Audit (separate session):** no blocker; all findings fixed except the ones below. **Decided (2026-10-04):** the lock on my
  `yes` is Hermes's own approval mode (fallback: a one-time code from the preview) — roadmap 10.2 rule 4, tested in
  `AIR_SETUP.md` phase 7 · the change number is shown when it is done · an `/undo` itself cannot be undone (roadmap 10.2).
  Accepted as they are: commands do not write `runs` (their log is `command_log`; `/analyze` writes `runs` through the agent it
  runs) · the backup prints nothing when all is well (Air test 8 checks Hermes does not forward stderr).
  **Left for later:** a real time for the backup in `settings.yaml` and `/status` warnings for a job stuck in `running` or a
  backup older than 36 hours (phase 6) · where the out-of-scope label (`bank`, `insurance`, `reit`, `pre_revenue`, `utility`)
  is stored (phase 1) · every new changing command also gets its `/undo` path. All of these are written into
  `docs/IMPLEMENTATION_PLAN.md` (sections 3 and 6, phases 1 and 6, marked "from phase 0").
- **Next — first thing (my note, 2026-10-05): limit Hermes (`AIR_SETUP.md` phase 5)** — I do it in the Air's terminal, not from
  Telegram (a limit set by a chat message is no limit): Hermes reads its own docs and proposes the settings, I apply them, then
  the tests (approval for `--yes`, another Telegram account gets no answer, `.env` is refused). Then phases 6–7 of the setup.
  Then: the Mac check of phases 0 and 1 together, on `main` (with `tests/fixtures/fetch_yahoo.py` once; a fix comes as a
  small PR) · finish the Air setup (`docs/AIR_SETUP.md`; at the latest before phase 4), then on the Air `git pull` +
  `uv run python -m shared.db upgrade` (version 2 → 3). Small open items: the subsector list (before phase 4) · the Anthropic API credit expires 2026-10-19 (phase 2's real-model runs
  before it) · a third external review is still running.
- **Exception to fixed rule 5 (my decision, 2026-10-04):** phase 1 is built before phase 0 is done (only its Mac and Air checks are left; the Air is not ready; phase 2's real-model runs must come before 2026-10-19) — Mac checks of phases 0 and 1 together, phase 0's Air check when the Air is ready (plan section 1).
- **Phase 1 built (2026-10-05)** on `claude/phase-1-analysis-numbers-arj800` (on top of phase 0; PR #4 went into the phase 0
  branch, PR #5 brought it to `main`, merged 2026-10-05). `shared/sec` (SEC client with `SEC_UA`; figures with their trace — tag + filing; synonym lists per year; liquid parts
  added; debt groups need all parts + candidate check; the last 4 quarters as the current year: annual + year-to-date − last
  year's same period; missing figures → `missing_data`); `shared/sectors` (SIC → sector table, corrections in `settings.yaml`
  `sector_overrides`; cyclical SIC list; out-of-scope SIC list); `shared/prices` (the price job, history kept, open day not
  stored, split and dividend events, Yahoo's market value, FX); `agents/analysis` (10 measures, type, grade with shrink and
  fast-grower safety, flags incl. debt > liabilities / debt to zero / gross ≠ revenue − cost / 10× revenue jump, price line;
  `card.md` with header by code only and append-only entries; `financials`, `card_entries`, `missing_data`, `stocks`; the weekly
  new-filing check); commands `/watch` `/archive` `/unarchive` `/analyze` `/card` `/green` `/missing` `/data` with `/undo` paths.
  DB version 3 (`stocks.out_of_scope`, price events, user figures, `card_entries.filing`, `command_log.before`). Golden set 10/10 on
  the annual reports **and** with the last 4 quarters; NVO (IFRS, DKK) works; 167 tests pass.
  **Audit (separate session, 2026-10-05):** no blocker; 29 findings. **My decisions (written into the roadmap):** a liquid part
  missing this year is still counted as not held, with a `data_check` + a `missing_data` row · the last 4 quarters take the place
  of the annual report they overlap · a 10× revenue jump is flagged, no year dropped · stock comp from Yahoo: not now (plan
  section 8) · a decisive measure not computed keeps the grade rule but adds a `data_check` with the reason · no Lynch dividend
  ratio when earnings growth ≤ 0. Approved code choices (roadmap): a stock analysed by hand is added as `candidate` · `/analyze`
  cannot be undone (fix a figure with `/data`, then `/analyze`) · type `unclear` when revenue growth cannot be computed.
  **Fixed:** Coca-Cola's `MarketableSecurities` (liquid 15.81 bn, not 13.87) · Boeing's gain on disposal flag · loss years for
  `unprofitable` (a missing year is not a loss) · tax / 5-year average per the rules · ticker change and share classes (identity by
  CIK) · SEC is never asked inside the write lock · the card is written at once and inside the database lock, last · the weekly
  check goes on after any error · unknown header fields kept · `free_cash.path_5y` · `financials` never deleted · the 10-year
  price history when only recent rows exist · Yahoo quotes read in tests · 36 rule tests + 11 fix tests. **216 tests pass.**
  **Golden set:** 10/10 on the annual reports; with the last 4 quarters Coca-Cola is now `solid` (the 2025 fairlife one-off is
  outside the window to 2026-04-03, so free cash covers the dividends again — BAGLAM.md section 9 said it would), the others
  unchanged. Deferred audit notes: plan section 8.
  **Not here:** Yahoo refused this cloud machine all day ("too many requests"), so the price job is tested on an answer built by
  hand in Yahoo's format, and the real Yahoo answers (prices, splits, market value) are checked on the Mac
  (`uv run python tests/fixtures/fetch_yahoo.py` once, then push). The data itself: `tests/fixtures/sec/` (13 companies).
- **Merged (2026-10-05, my decision, before the Mac check):** PR #3 (phase 0) and PR #5 (phase 1) are in `main`, as merge
  commits. The Mac check of both is still owed, on `main`.
- **Air real check and the no-debt rule (2026-10-06):** Hermes ran the phase 0 + 1 check on the Air in isolation — 216 tests,
  golden set 10/10 on live SEC, cards append-only, `/watch` previews only, a bank is out of scope; the one blocker is Yahoo (HTTP 429
  on the Air and on the cloud machine, cause not found yet; the test of the same `curl` on the main Mac is still to do). Found with
  real data and fixed (decision A, 2026-10-06; roadmap section 3 "A company with no debt"): a company with no debt (Palantir) is
  counted as debt 0 under 4 conditions instead of asking 7 questions; Nvidia's marketable securities moved to `DebtSecuritiesCurrent`
  (liquid 56.6 bn, matches the 10-Q). Palantir's type `cyclical` stays (a known limit of the type rule; revisit in the 20-stock test).
  Samples: PLTR added, NVDA refreshed. **223 tests pass.** Open: the Yahoo test on the main Mac · the NVDA debt (8.5 → 33.4 bn, a
  25 bn $ bond in June 2026) stays flagged "check the figure" — checked against the 10-Q by me.
- **Air setup started (2026-10-05):** clone at `~/projects/investment-agents` (the docs' example is `~/investment-agents`;
  scheduled jobs use the real full path). First check by Hermes (read-only, `sudo -n`, no password): time zone Istanbul,
  FileVault, firewall, no sleep (AC and battery), wake for network ✓ · setup phase 2 done: `uv` at
  `/Users/jans./.local/bin/uv` (full path for scheduled jobs), `uv sync`, 85 tests pass (before the pull), database created,
  `git pull` (phase 1) + `shared.db upgrade` → version 3 · not yet: `uv run pytest -q` after the pull (expect 216), `.env`; then
  setup phases 3–7 (Drive, Telegram, Hermes limits, OpenRouter, tests). **Decided (2026-10-05):** the system runs in my main
  account `jans.` (no `agents` user; iCloud off on the Air) · Remote Login and Screen Sharing off — Telegram is the remote path ·
  Hermes limited, not painful: plain words, questions without approval, a change after one "yes", no other terminal commands
  (`AIR_SETUP.md` phases 1 and 5) · the charger is on · **done 2026-10-05:** Drive (setup phase 3: `DRIVE_DIR` = `/Users/jans./Drive'ım/Investing`, Drive for desktop on a
  separate Gmail, Mirror files; the test file reached Drive on the web), Telegram bot connected (phase 4), `.env` filled, 216 tests
  pass on the Air · **running:** the phase 0 + 1 real check, done by Hermes on the Air in isolation (throwaway `DATA_DIR` and
  `DRIVE_DIR`, never the real database or `Investing/`; `fetch_yahoo.py` skipped because the Air writes no code) · Remote Login
  left on by my choice.
  **What is done, what waits, what we stay away from:** plan sections 7–8 (decision: 2026-10-05).
  **How to talk:** one topic at a time, one name per topic, short; no comments on model / provider choices (user, 2026-10-04).
- **Note:** PR #1 (agent 4, the document audit, the database decisions) was merged into main on 2026-10-04 as one commit; the
  implementation plan was merged the same day, also as one commit.
