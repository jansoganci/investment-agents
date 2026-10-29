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
   One exception: the header shows the current state (`status`, `in_portfolio`, `lynch_type`, `grade`, `last_entry`, `sector`) and only code updates it; every change is also appended as a dated note.
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
- **Merging (my standing permission, 2026-10-09):** when a change is finished and all tests pass, push the branch, merge it into
  `main` locally with `--no-ff`, run the tests again and push `main` — without asking. (`gh` is not installed, so no PR.) A phase
  still gets its separate audit session before it counts as done.

## Project map

Names follow `docs/GLOSSARY.md`. New code goes directly under `agents/` and `shared/` (decision: 2026-10-04); `ajanlar/` is an
archive. Do not move or rename the archive unless that is the task.

```text
Exists today:
ajanlar/analiz/prototip/   agent 3 rule trial (archive, not production)
ajanlar/teknik/backtest/   backtest scripts (archive)
docs/                      YOL_HARITASI_v2.md, IMPLEMENTATION_PLAN.md, BULLETIN_PLAN.md (the morning bulletin, 2026-10-28), TEST_PLAN.md (the real-world tests of phases 4–6), SCHEDULE.md, BAGLAM.md, GLOSSARY.md, TASINANLAR.md, DIS_INCELEME_PROMPT.md, AIR_SETUP.md,
                           telegram_setcommands.txt; reviews/ (external reviews)
shared/                    phase 0: config, clock, db (tables + upgrade steps), backup, runlog, notify, drive, commands, ask
                           phase 1: sec (client, facts, synonyms), sectors, prices (job + yahoo), commands/stocks.py
                           phase 3: commands/portfolio.py (/bought /sold /gold /bes /portfolio)
                           phase 4: commands/eye.py (/tag /subsector)
                           phase 5–6 (built early): commands/research.py (/candidates /summary), summary, alerts, sunday (python -m shared.sunday | shared.alerts)
agents/analysis/           phase 1: agent 3's numbers — measures, card, run; python -m agents.analysis KO | --weekly
agents/portfolio/          phase 3: agent 4 — ledger, marketdata, value, watch, block, run; python -m agents.portfolio [--show]
agents/counter/            phase 5 (built early): 1B — count; python -m agents.counter [--show]
agents/research/           phase 5 (built early): agent 2 — health, tailwind, score, reading, news, page, run; python -m agents.research [TICKER]
agents/eye/                phase 4: agent 1 — sites, http, sitemap, extract, store, run, sentence, inbox, tags, modeltest, session_check, set_cookie;
                           python -m agents.eye [--accept-many] · .session_check emtia|dragonomi · .modeltest
tests/                     uv run pytest -q; sample data in tests/fixtures/ (sec/, yahoo/)
pyproject.toml, uv.lock, settings.yaml, .env.example

Planned (not created yet):
shared/             still to come: AI, the auditor, the Sunday summary
shared/bulletin/    the morning bulletin — docs/BULLETIN_PLAN.md (exists: market.py, gather.py, write.py, check.py, translate.py, render.py, run.py; shared/search.py = the DeepSeek web search; shared/prices/mof.py = Japan 10Y)
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

- **Last update:** 2026-10-28 (morning bulletin decided, plan drafted) · 2026-10-19 (production at `3d54db1` + docs up to `7f3caee`; first automatic Sunday chain healthy; models DeepSeek-first; Telegram in plain words; **list for when I am home, below**) · 2026-10-14 (auditor test set 21/21 after the event-card fix) · 2026-10-12 (real-world tests of phases 4–6 mostly done, production running, see the bullet below; Hermes limits: what Hermes can enforce and levels 1–2 written in `AIR_SETUP.md` phase 5; done at `TEST_PLAN.md` D4 unless I choose earlier) · 2026-10-11 (phase 4 code done, the Counter built early — see the Phase 4 entry and the rule 5 exception) · 2026-10-09 (**phase 3 (Portfolio) done** — built, audited, real-checked, the block approved; the Air update (`git pull` + `shared.db upgrade`, 4 → 5) given to Hermes; next: Hermes limits, then phase 4)
- **Phase 3 built (2026-10-09)** on `feat/phase-3-portfolio` (merged into `main` under my standing permission; the audit is still
  owed): `agents/portfolio` (ledger with code dividends and splits worked out again each week · values in today's share basis ·
  SPY shadow from a total-return index of stored closes + dividends · gold shadow · return, `xirr` after 12 months · total wealth ·
  drop alert · valuation watch with the weekly `valuations` table · new-money ranking with the 25% line · the block) and
  `/bought` `/sold` `/gold` `/bes` `/portfolio` with their `/undo`. Database version 5. **My decisions (2026-10-09; roadmap,
  "How phase 3 builds it"):** new money = 3 conditions counted (below the high · thesis `intact` · price line not `expensive`),
  tie → the bigger fall; a shadow may go below zero; a drop alert once per fall (again only after a new 52-week high). The
  hand-checked ledger (two buys, a sale, a dividend, a split) is `tests/portfolio/test_ledger.py`. **396 tests pass.** Next: the
  my Mac check (`uv run python -m shared.commands bought 10 KO 85.65` ·
  `uv run python -m agents.portfolio`) → on the Air `git pull` + `uv run python -m shared.db upgrade` (version 4 → 5).
  **Audit of phase 3 (Hermes on the Air, `~/check-repo`, 2026-10-09):** 396 pass; rules 1–9 have code and tests; the hand
  ledger recomputed ✓. Its one blocker was wrong: it said Yahoo's `Close` (with `auto_adjust=False`) is never split-adjusted —
  checked live: NVDA 2024-06-07 comes as 120.89 $ (the real close was ~1,209 $), so stored history is already adjusted and
  `marketdata` is right. Not done (my decision): an UPDATE trigger on `holdings` (code only sets `void` / `voided_by`). Known
  small item: if the 03:00 price job misses a split night and is run by hand after the US open that day, the day before the
  split could be divided twice (rare; not fixed).
  **Real check (Hermes on the Air, `~/check-repo`, throwaway data, live Yahoo + SEC, 2026-10-09):** KO + V ledger, gold,
  BES, the refusals and `/portfolio` all right (figures checked by hand: put in $2,009, got back $348, KO 6 left, a real KO
  dividend $4.24 added by code). **Found:** the weekly run stopped with a TypeError — Visa's card has `peg: not_computed` and
  the valuation watch multiplied the text. Fixed on `fix/phase-3-not-computed` (a card figure that is not a number is None;
  the test cards now write `not_computed` as the real card does; one test). **397 pass.** **Second run (6d869e4) passed:** the
  weekly run finished twice (the second "already recorded"); week 2026-10-02: value $1,596, return −3.3%, SPY $1,691, KO
  dividend $4.24 — checked by hand. Gold and BES entered on 10-09 are not in the 10-02 snapshot (right). **Phase 3 done (my
  decision, 2026-10-09):** the block reads well. `/portfolio` on the real database: empty (no real buy entered yet) — right.
  The Air's production copy is `~/Downloads/investment-agents` (macOS asked once for Downloads access).
- **Phase 4 (Eye) started (2026-10-11)** on `feat/phase-4-eye`. **Site probe** (Hermes on the Air, no login, files in `~/eye-probe/`): both
  sites are Ghost; Emtia Defteri shows nothing without a login, Dragonomi a cut preview; `lastmod` jumps on thousands of old posts, so
  a post is new when its address is not in the database (first run = baseline, a pass with > 200 new addresses reads none);
  a post's own tags come from the page meta as display names; Dragonomi's tags are mostly Chinese companies. Written into the roadmap,
  "Agent 1 rules" 10–18. **My decisions (2026-10-11):** a pass with > 200 new addresses reads none · a gated page is `text_missing`,
  never forced or retried, no "log-in ended" alert · a company listed in the US (ADR too) gets the SEC check, a non-US one gets none
  and no question · `Inbox/` = one file a day, `YYYY-MM-DD.md` · the subsector list is drafted from the first passes' tags · login by my
  cookie header over plain HTTP, no Playwright for now (Ghost has no password; I never give the system my e-mail password). **Built:** `agents/eye` (`http`, `sites`, `extract`, `session_check`; slices A + B: `sitemap`, `store`, `run`, `python -m agents.eye [--accept-many]`; slice C: `sentence`, `inbox`, `modeltest`; slice D: `tags`, `/tag`, `/subsector`; database version 6 = `eye_seen`, version 7 = tags `region` / `other`, state, `subsectors.void`), 100+ more tests, `.env.example`
  `EMTIA_COOKIE` / `DRAGONOMI_COOKIE`. **Next, my part (main Mac):** `git pull` → log in to each site in my browser → copy the request's
  `cookie` header into `.env` → `uv run python -m agents.eye.session_check emtia` and `... dragonomi` → send the output to Claude
  (the cookie is never printed; do not send it to Telegram or Hermes). **All the code that can be written without the sites is written** (slices A–D). Left, all needing the real sites: the Mac
  `session_check` (does the cookie give the full text? how long does it live?), then on the Air `git pull` + `shared.db upgrade`
  (5 → 7), the cookies in its `.env`, the 20-post cheap-model test (`python -m agents.eye.modeltest`, after a few real passes),
  then the phase 4 audit session and the one-week check.
- **Exception to fixed rule 5 (my decision, 2026-10-11):** the Counter (1B, phase 5) is built before phase 4 is done (phase 4 waits for the
  Mac `session_check`, the Air and the one-week check). **Counter decisions (roadmap "Agent 1B rules" 6):** the 7 days count on the
  published date · posts cut by the paywall count · only confirmed tags count (waiting tags are one line of note) · tags of one company
  are one stock, a post counts once · a stock with a card is "mentioned a lot" at 6 posts in 7 days · sector counts come from sector
  tags only · order: 7-day posts, then 30-day posts, then ticker · the result goes to the table `counts` (database version 8; agent 2
  reads the latest run) · numbers in `settings.yaml` `counter:`. **Built (same day):** `agents/counter` (`count`, `block`, `python -m agents.counter [--show]`), database version 8 (`counts`), 23 tests, **514 tests pass**. On the Air it needs `shared.db upgrade` (7 → 8) and real posts. Agent 2 (Research) waits for real posts.
- **Phase 5 Research and phase 6 built early (my instruction, 2026-10-11: "write all the code that can be written, then test it"):** decisions are in
  the roadmap, "Agent 2 rules" 8 and 9 (Claude's proposals where I had not decided: the web-search tool, the quick-health arithmetic for 3–4
  computed checks, the summary contents, the alert list, the schedule) — change any by saying so. Slices: R1 web search in `shared/ai` + database
  version 9 · R2 quick health, sector tailwind, score · R3 reading, news, events audit · R4 Research run, cards, `/candidates`, `/watch` · S1 summary,
  `/summary`, `/status` warnings · S2 alerts · S3 the Sunday chain and `docs/SCHEDULE.md`. **Built so far (2026-10-11):** R1 (web search in `shared/ai`: `ai.call(..., web_search=N)`, Anthropic's `web_search_20260209`, sources and the $0.01
  per search counted; database version 9: `readings`, `news_events`, `stocks.commodity_checked`) · R2 (`agents/research`: `health`, `tailwind`, `score`;
  `settings.yaml` `commodity_symbols`, `research:`; the price job also fetches linked commodities; agent 3's `Result.series`) · R3 (`reading`, `news`
  — one web-search call returns the story, the events and the commodity links —, `page`, auditor card 4 `event.md` + 5 test-set cases) · R4
  (`run`, `python -m agents.research [TICKER]`, `/candidates`, `/watch` for a new stock runs agent 2 then agent 3). The auditor test set (now with
  the event cases) and the web search have not met a real model yet: that is the Air test. **S1–S3 built:** `shared/summary` (the Sunday summary, saved in
  `Weekly/`, `/summary`), `/status` warnings (a job `running` over 1 h, a backup over 36 h; `settings.yaml` `warnings:`), `shared/alerts` (hourly, each alert once,
  database version 10 `alerts_sent`), `shared/sunday` (the chain), `docs/SCHEDULE.md` (the five Hermes jobs), `settings.yaml` `hours`. **Nothing of phases 4–6 has met the real
  sites, a real model or Hermes yet.** Next, only with real data: the Mac `session_check`, the Air update (`git pull`, `shared.db upgrade` → 10, cookies in `.env`), the Eye baseline,
  a week of passes, the model tests, then `docs/SCHEDULE.md` "Before the first scheduled run", the audits.
- **Real-world tests of phases 4–6 (2026-10-11):** the plan, the order, who does what (U me · M Claude Code on the Mac · H Hermes on the Air · C the cloud
  session), the prompts and the terminal commands are in `docs/TEST_PLAN.md`; its section 6 is the results log. Block A (no login: baseline, upgrade rehearsal
  on a copy of the real database, real models, the auditor test set, Research with web search, Yahoo symbols) comes first because the Anthropic credit ends
  on 2026-10-19. Hermes' limits stay the last step (D4).
- **Real-world tests, state on 2026-10-12 (I am travelling until about 2026-10-23; Hermes on Telegram is my only channel, Remote Login stays off):**
  `docs/TEST_PLAN.md` section 6 has every result. **Passed:** block A (baseline, upgrade rehearsal, `ai ping` 8/8, auditor test set 21/21, Research with web
  search on NVDA / FCX / DAL, Yahoo symbols, the three cards read) · B1–B4 and B6 on **Emtia only** (Dragonomi has no membership yet) · C1–C3 · D1 (production
  database 5 → 10, backup first) · D2 (cookie copied inside the Air, Eye baseline in production: Emtia 11,140, Dragonomi 14,916 addresses) · the first Sunday chain by hand
  (11 s, summary reached Telegram, saved in `Weekly/`). **Partial:** B5 (no company tags in Emtia, so the SEC check and the non-US tag rule are untested) · B7 / B8 (Counter and
  Research had nothing to do) · D3 (five script-only Hermes jobs registered: prices 03:00, backup 04:00, eye 07 / 13 / 20, alerts hourly :05, sunday Sunday 09:00; `backup`,
  `prices` and `sunday` fired by hand; `eye` and `alerts` not yet seen) · D4 (Hermes `approvals.mode manual` gates only dangerous patterns; Level 2 waits). **Found and fixed on
  the way:** the sentence call was cut at 2,000 tokens (now 8,000) · `set_cookie` helper (clipboard / cURL, repairs a broken `.env`) · the auditor test set and `modeltest` print progress ·
  the Eye warns on Telegram when the last 5 pages in a row were cut by the paywall (the cookie has probably expired; roadmap Agent 1 rule 19) · `settings.yaml` `eye.skip_sites: [dragonomi]`.
  **My decisions:** Dragonomi postponed · cheap model stays DeepSeek V4 Flash (B6; the A / B answer could not be mapped, C compared the pairs) · Hermes keeps its own skills and notes but
  my rules win (standing rules stored in its memory) · positive news older than 90 days should not count (proposed, not built, waiting for my yes). **To do when I am home:** the login
  cookie's expiry date (Chrome → Application → Cookies) · Hermes Level 1 in the Air's terminal and Level 2 · the other-Telegram-account test · Dragonomi cookie, then remove it from
  `eye.skip_sites` · answer TMDX's missing debt (`/data`) · read `investment-agents-ops` (Hermes's own skill, 30 auto-patches) · the 90-day rule for positive news · the audit sessions of phases 4–6 ·
  the Anthropic credit ends 2026-10-19 (web search works only through Anthropic).
- **Audit of phases 4–6 (separate session, 2026-10-14):** no blocker, 22 findings (full list in `TEST_PLAN.md` E4); verdict: the system can run unattended. Fixed the same day (677 tests):
  one cut sentence no longer stops the others · `--accept-many` no longer leaves a backlog that trips the 200 guard at every scheduled pass · a bad cookie value never appears in an
  error · the Sunday chain runs agent 3's drop-alert check · reading token limit raised · `.env.*` ignored by git · dead `running` rows are closed. **Decided:**
  #20 (the SEC name check uses only the tag's own text, built 2026-10-14); #7 (no sector / no price = `unclear` = 1 point, built 2026-10-14). Later the same day (2026-10-14) most of the remaining notes were fixed too (#5, #9, #12, #13, #15, #16, #18, #19, #21); open: #10, #11, #22 (`TEST_PLAN.md` E4). The auditor prompt changed: the auditor test set must be rerun on the Air. **Rerun on the Air (2026-10-14, 0.11 $): 20/21** — the CFO event case came back `not_found` because the page says only "today" (no date); rule card 4 item 4 now says a page with no date is no reason to refuse (code already checks the 12-month window; a page showing an old date still fails). **Rerun at `fbda269` (production updated to it): 21/21, "All caught." — the auditor test set is closed.** Production runs 5 Hermes jobs; first automatic Sunday chain 2026-10-18 09:00. **First scheduled-job failure (2026-10-15 07:00, `eye`):** the cheap model returned an empty `choices`; fixed so it counts as a provider error and the next model is tried (TEST_PLAN F1). **From the old-system comparison (2026-10-16, my yes to item 1 only):** a `finance_arm` warning for makers with a lending arm (Deere, Caterpillar, Ford, GM …; list in `settings.yaml`, roadmap rule 49); nothing recomputed. Three more ideas (return-trend warning, a thesis-prompt hint, reverse DCF) are only **notes** in roadmap 10.5 — my decision: not now, one at a time, after 4 clean Sunday chains. **Models (2026-10-18, my decision):** no Anthropic top-up this month → `strong` / `auditor` order DeepSeek V4 Pro → GPT-6 Sol → Sonnet 5.5 (last); the auditor test set must be rerun on the Air; the ChatGPT / Codex subscription through Hermes waits for a talk at home (roadmap 10.1). **Telegram finding (2026-10-19):** Hermes' gateway intercepts every `/…` message; our commands work only **without the slash** (and `/help` `/status` `/model` `/undo` are Hermes' own, `/undo` does not undo our change) — see roadmap 10.2; **decision 2026-10-19: Telegram stays in plain words, no development** (roadmap 10.2; read each preview before saying yes; BES in TL, gold with grams + TL price per gram). The first automatic Sunday chain ran 2026-10-18 and was healthy (all jobs `ok`). **Model trial plan (my decision, 2026-10-19):** no model change for now; DeepSeek V4 Pro runs the heavy jobs and the auditor for the coming week(s); at home (about 2026-10-23) a week with Codex / ChatGPT, then I choose the best model per job (roadmap 10.1). The fair way to compare: the same stocks side by side with `modeltest` (blind A / B), not only the weekly outputs, because the scheduled weeks rarely call the heavy models (few new stocks).
- **Morning bulletin decided (2026-10-28):** weekdays 08:15 on Telegram, Turkish (everything behind it English), a fixed template, neutral, figures with the 1-month change (incl. Brent, DXY, Japan 10Y), my stocks with the thesis tag, SEC lines, interests (macro direction, AI infrastructure), DeepSeek web search, ~2–3 $ / month; changes nothing in the system. Rule 5 exception (my decision). Dragonomi is added now by the one-time login link sent to Hermes ("Yol B"). Rules: roadmap "Morning bulletin"; plan: `docs/BULLETIN_PLAN.md` (approved 2026-10-28; ⚠ items stay, the `search` answer is Turkish, the 8 interest topics stand). DeepSeek's Search API details came from DeepSeek itself (official docs). **Built (2026-10-28):** slice 0 (glossary, `settings.yaml` `bulletin:` / `hours.bulletin` / the search price, SCHEDULE job 6 planned) · slice 1 `shared/search.py` (`python -m shared.search "…"`; `lang:en`, `after:`; each search with hits = one `ai_calls` row at 0.00075 $; 15 tests) · a fix: Research's "Counter run is N days old" compared a Turkey date with a UTC date (failed between 00:00 and 03:00). **709 tests pass.** **Air test T3 passed (2026-10-28, Hermes, `~/check-repo`):** two searches, 5 hits each, 0.00075 $ each. **Slice 2 built (2026-10-28):** the nightly price job also fetches the bulletin's 9 Yahoo figures (3 months the first time) and Japan's 10Y yield from the Ministry of Finance's CSV (`shared/prices/mof.py`, symbol `JP10Y`); `shared/bulletin/market.py` + `python -m shared.bulletin --market` (last close, 1-month and day change, bp for yields, Turkish text); checked live on Yahoo from the cloud session (`^TNX` is already in percent). The Ministry file could not be reached from the cloud; **its first real read (Air T4, 2026-10-28)** showed the layout is right but refused Japan's negative 2016 yield — fixed (negative allowed, plausibility checked only on the kept 120 days), then a second finding: the Ministry's history file ends on 09-30, so the first read takes the current file too. Japan 10Y now prints on the Air (with its date marker); the Air reruns T4 once more. **T4 passed** (all 10 figures, Japan 10Y %2,83 with its date marker 27.10: the Ministry's file is a day behind). **T1 passed** (a real script-only job: 8,453 characters arrived as 3 messages with (n/3) labels, a header and a footer from the scheduler; the bulletin stays one job). 745 tests pass. **Slice 3 built (2026-10-28):** `shared/bulletin/gather.py` (window = the last weekday's bulletin time; posts with full text for the first 40; my stocks with their cards' 3 thesis breaks; SEC filings by acceptance time; Yahoo earnings dates (`yahoo.next_earnings`); DeepSeek searches with a budget and failure notes) and `python -m shared.bulletin --gather [--no-search]`. **Air T5a (2026-10-28, a copy of the production database):** gather found 40 posts and 18 web hits from 8 searches; **my stocks 0** (the production database has no stock I hold or watch, so the stocks section stays empty until I `watch` one). **Slice 4 built (2026-10-28):** `write.py` (the strong model's JSON items with sources, thesis point and top-3 rank; drops items without a source, advice, ratings, price targets), `check.py` (numbers read the English and the Turkish way; years and ordinals ignored), `translate.py` (the cheap model; a translation whose numbers differ is not shown) and `python -m shared.bulletin --draft`; 783 tests pass; **Air T5b passed (2026-10-28, first real model run, 0.095 $):** 15 items, neutral, sourced, numbers right, Turkish natural; one false ⚠ ("2-year" read as a number) → tenors ("10-year", "2 yıllık") are now ignored by the number check; `--draft` also lists the pieces nobody cited ("NOT USED"): only 5 of 40 posts were cited and 9 of 15 items came from web hits, to be looked at. **Slice 5 built (2026-10-29):** `render.py` (the approved template in Turkish: figures, top 3, calendar with 📌 earnings and SEC lines, macro, my stocks with the thesis tag and "Haber yok", interests, sources with `[ED1, W2]` tags and numbered links, ⚠ and ℹ️ lines), `run.py` (the job: saved once a day in the new table `bulletins` — **database version 11** — and in Drive `Bulletin/`; a second run prints the saved text; the window continues from the last saved bulletin; a failed writer sends the figures with a warning and is not saved), commands `--force --dry --show`; 800 tests pass. **The Air needs `git pull` and `shared.db upgrade` (10 → 11) before job 6; Air test T5c: `--dry` on a copy of the production database.** **Air T5c (2026-10-29, `--dry` on a copy of the production database): the first real bulletin read** — neutral, sourced, natural Turkish, 6 of its sources from Emtia; findings: the figures table was mostly "veri yok" (production has not yet run the new price job: update production and run `shared.prices` once), DeepSeek returns some shortened addresses (`sk-hyn...2029`; now shown without a link), the ⚠ now names the number it could not verify, `--dry`/`--draft` print their time and cost; a second long command in the same Hermes call hit its 300 s tool limit (run long checks one at a time or in the background). **I have read the bulletin and I am happy with it (2026-10-29).** Measured: 3 min 16 s and 0.105 $ a bulletin (writer 44k tokens, mostly its thinking), about 2.3 $ a month. **Live (2026-10-29):** production at `6414bcb`, database 10 → 11, `shared.prices` run once by hand, all 10 figures filled (Japan 10Y included; gold's 1-month change shows "—" until its history is backfilled: `python -m shared.prices --ticker GC=F`), and Hermes job 6 `bulletin` registered (id `42a55c482478`, script-only, delivers to Telegram, weekdays `10 8 * * 1-5`, arrives about 08:14); the first real bulletin is the one of 2026-10-29 08:10. Next after that: slice 6 (`search`), slice 7 (Dragonomi login link).
- **When I am home (about 2026-10-23), in this order (2026-10-19):** (1) Dragonomi: membership → cookie with `set_cookie` in the Air's terminal (never through Telegram / Hermes) → `session_check dragonomi` → remove it from `eye.skip_sites` · (2) read Hermes' skill `investment-agents-ops` (it patches itself) and check my rules still win · (3) Hermes limits: Level 1 in the terminal, Level 2, the other-Telegram-account test · (4) models: a week with Codex / ChatGPT, `modeltest` blind A / B on the same 3–4 stocks, then choose per job; the ChatGPT / Codex subscription needs a bridge decision (roadmap 10.1) · (5) the login cookie's expiry date (Chrome → Application → Cookies; never log out of Emtia) · (6) optional: TSLA 2022 marketable securities (`/data`), TMDX debt · (7) open audit notes #10, #11, #22 · (8) roadmap 10.5 ideas only after 4 clean Sunday chains. Daily until then: nothing needed; `status` / `spend` in plain words if curious.
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
- **Phase 2 built (2026-10-06)** on `claude/phase-2-agent3-ai-arj800` (from `main` after PR #8; second exception to rule 5: before the Mac check
  of phases 0 and 1 and before the Air setup is done; the real-model runs must come before 2026-10-19). `shared/ai` (ordered providers,
  `/model` override, costs into `ai_calls` and `runs`, monthly limit, fake mode), `shared/auditor` (cards 1–3 in `cards/`, `testset`),
  `shared/sec/filing` (quote check word for word), agent 3's AI parts (why answers with quotes, first thesis, thesis check,
  drop-alert check, sell suggestion for held stocks, held back when an audit fails, `unverified`), stable warning codes, missing-data
  requests (once, reminded once), commands `/spend` `/model` `/note` `/thesis` `/closewarning` and `/analyze KO [model]` with its cost.
  Database version 4. `python -m agents.analysis KO --ai` · `--weekly --ai` · `--drop-alerts` · `python -m shared.ai ping` ·
  `python -m shared.auditor testset` · `python -m agents.analysis.modeltest KO NVDA`. Build choices written in the roadmap
  (section 3, "Agent 3's AI parts — how phase 2 builds them") for my approval after the audit. **Not tried with a real model yet:**
  the Mac check (plan, phase 2) does that. Pricing for DeepSeek and GPT-6 Sol models is empty in `settings.yaml` (shown as unpriced).
  **Not here:** news in the drop-alert check (phase 5) · the card's 2-sentence story · `absent` marking.
  **Audit of phase 2 (separate session, 2026-10-06):** 1 blocker (a sell suggestion went out although the auditor confirmed nothing) and
  8 should-fix, all fixed on the same branch; my decisions: no audit threshold (every item must pass; any fail marks `unverified`;
  otherwise "could not confirm") · price list given by me (DeepSeek, GPT-6 Sol) and a cautious default price for unknown models ·
  agent 3 may write a dated `note · agent_3` for a checked drop alert. Also fixed: balance-sheet rows kept in the excerpts, the auditor is never
  of the writer's model family, warning identity keeps years, billed-but-rejected calls logged, `ping` and the test set logged, strong-model
  test records who answered. **342 tests pass.**
  **First real-model run on the Air (2026-10-06, in an isolated worktree `~/check-repo` with throwaway `DATA_DIR` / `DRIVE_DIR`):** `ping` 8/8 ✓;
  auditor test set 8/10 (the 2 misses were correct passes whose quote spanned several rows → rule 22: several rows allowed, each checked);
  strong-model test (A / B, B looked better; I still choose and `--reveal`) · no "why?" for `borderline` flags (rule 23) · **Yahoo 429 solved by
  `yfinance`** (rule 24; prices, splits, market value live: NVDA share count and price line now computed) · OpenRouter's dotted model names find
  their price. Open: the 10-K for multi-year "why?" (rule 25, later). **Rule for me: tests and trials run only in an isolated worktree on the Air or on the main
  Mac, never in `~/Downloads/investment-agents` (the Air's production copy stays on `main`).**
- **GE + SBUX real check (Hermes, Air, isolated; 2026-10-06) and the three P1 fixes** on `claude/p1-fixes-ttm-stockid-debt`
  (roadmap section 3, rules 28–31): the figure claim says its period and a last-4-quarters figure is audited by its two
  year-to-date parts (GE's correct 9.8 bn operating cash was failed against a 6-month row) · a new stock gets its number before
  its AI parts, so `ai_calls.stock_id` is never empty for it (GE's 5 calls were) · debt group
  `LongTermDebtAndCapitalLeaseObligations` + `DebtCurrent` (GE 19.157 bn; changes no other sample company) — GE becomes `solid` on
  2 of 3 decisive measures. **354 tests pass.** Still to do: `python -m shared.auditor testset` with the real auditor (rule card 1
  changed; 2 new GE cases), then a GE rerun on the Air. Not fixed (P2, from the same review): `GE` sector override
  (`settings.yaml` `sector_overrides`, old SIC 3600 → IT) · the missing-data message says "SEC's data does not have" when our
  names did not find it · the first AI thesis escapes the reading audit when a card had an AI-less entry · rule card 1 on liquid
  parts that have no balance-sheet line (GE's time deposits).
- **Second GE check (2026-10-06), analysed, nothing built:** 5 findings. **My decisions** (roadmap rules 32–34): liquid = separate
  balance-sheet lines only (option A) · restricted cash counts · a sector change goes to the card as a dated note. **Next (tomorrow):**
  (1) on the Air, read GE's latest figure audit (`audits.detail`) to find why `op_cash` is `not_found` · (2) build rules 32–34 + the
  thesis-check fix (tell the model NEW NUMBERS are current; show mark-only measures without `None`) · stuck `running` rows wait for
  phase 6. Roles: Cursor builds from the handoff, Claude checks.
- **Rules 32–34 built (2026-10-07, Cursor)** on `claude/decisions-liquid-sector`, one commit each, not pushed: rule card 1 + the liquid note + 2 GE test-set cases (no-line parts, restricted cash) · a sector change updates `stocks.sector`, the card header and adds one dated note (`card.change_sector`); `sector_overrides` GE and MMM (SIC 3841 → Health Care) → Industrials. 356 pass. The reminder test's date failure is fixed on `fix/ge-audit-excerpts` (below). Next: the real auditor `testset`, then GE on the Air.
- **Figure audit rows by value (2026-10-09, rule 41)** on `feat/audit-rows-by-value` (from `main` after `fix/ge-audit-excerpts`, merged locally, not pushed): `filing.rows_with` finds the rows that print our figures (TTM by its two year-to-date parts, liquid and debt by total and parts) with their period headers; they go first in the figure audit's prompt, the word excerpts fill the rest of 12,000; rule card 1 updated. GE 8/8 rows (was 0/8), Nvidia all. **364 tests pass.** Next: on the Air the auditor test set + a GE rerun (most figure items should pass), then merge, then the 20-stock acceptance test before 2026-10-19.
- **Acceptance test round 2 passed (2026-10-09):** fresh `~/uat3-data`, Sonnet writer and auditor, 20 stocks, 1.44 $ — all 4 conditions hold (roadmap, after rule 47). 3 cards read; `capital_return` misread as cash paid to owners → rule 48 (each measure's meaning in the thesis prompt), rerun NVDA / KO fine. **Agent 3 closed (my decision, 2026-10-09).** Next: phase 3 (Portfolio). Hermes limits still open.
- **Acceptance done line (my decision, 2026-10-09):** agent 3 passes round 2 when the 10 trial grades are right, no liquid / debt figure is off by > 5%, every `unverified` is for a real reason, and the bank path works; the rest is a "known small items" list in the roadmap (after rule 47). Then phase 3 (Portfolio).
- **Auditor = Sonnet 5.5 high too (my decision, 2026-10-09)**: the auditor job has the writer's order (Sonnet → DeepSeek V4 Pro → GPT-6 Sol); the "different family" rule is dropped in code, `/model` and the roadmap. 373 tests pass. Round 2 batch 1 ran with DeepSeek as auditor.
- **Acceptance test round 1 (2026-10-09)** on the Air (fresh `~/uat-data`, 20 stocks, 1.59 $): trial-set grades all as expected, JPM out of scope; fixes on `fix/uat-round-1` — rules 43–47 (stale-data warning, Intel's short-term investments, debt from the long-term line alone, one decimal in millions, option A for the reading audit). **373 tests pass**. Still open: Novo's 20-F exhibit, Boeing / Visa / zero-debt / Microsoft items (roadmap, after rule 42). Next: the real auditor test set, then the 20 stocks again.
- **Strong model order (2026-10-09)** on `feat/strong-model-order`: Sonnet 5.5 high → DeepSeek V4 Pro → GPT-6 Sol high, then the same through OpenRouter (roadmap 10.1); `effort` now reaches OpenAI and OpenRouter; DeepSeek prices updated (V4 Pro 1.32 / 3.96, Flash 0.30 / 1.20, peak). **367 tests pass.**
- **A quote may span lines (2026-10-09, rule 42)** on `fix/quote-rows-by-line`: GE's Air check of rule 41 found every row, but 5 of 7 quotes (header + row, copied on separate lines) were refused as a whole; `quote_ok` now checks each line word for word. **365 tests pass.** **Checked on the Air (2026-10-09, Hermes, check-repo):** GE's figure audit 7 of 7 `pass` (was 2 of 7). Next: the 20-stock acceptance test before 2026-10-19.
- **GE excerpts measured (2026-10-07, Cursor)** on `fix/ge-audit-excerpts`, not pushed: GE's real 10-Q is saved; all 8 statement rows miss the 12,000-character excerpts and GE's labels do not fix it (rule 40, chooser unchanged) · the thesis check is told NEW NUMBERS are current and a mark with no value shows as `debt: good, decisive` · the reminder test freezes the clock.
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
- **First real run on the Air (2026-10-06):** after PR #8 (`git pull`), Hermes ran `agents.analysis` for PLTR (mid / cyclical, no flags, no
  missing figures) and NVDA (solid / cyclical, flags only from Yahoo and the real debt jump) against the real database
  (`~/investment-agents-data`, version 3) and the real `Investing/Stocks/` (cards `NVDA - Nvidia Corp`, `PLTR - Palantir Technologies Inc.`).
  `.env` `DRIVE_DIR` is the symlink `~/investing-drive` → `/Users/jans./Drive'ım/Investing`. `/status` shows a `prices` run stuck in
  `running` (a price job killed on purpose; the `/status` warning for stuck jobs is phase 6 — leave it). Still open: Yahoo 429, and
  that I see the two cards in Drive on the web.
- **Air setup started (2026-10-05):** clone at `~/Downloads/investment-agents` (corrected 2026-10-09; the docs' example is `~/investment-agents`;
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
