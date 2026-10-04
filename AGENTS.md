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
- Each agent is its own module. Code used by more than one agent goes under `ortak/` (planned name `shared/`).
- The code does not know Hermes. Each agent must also run by hand. Planned command: `python -m agents.<agent>`. Until the folders are renamed, the code that exists is under `ajanlar/`.
- At the end of the session, update the **Current status** section.

## Project map

Today's folders. The locked future names are in `docs/GLOSSARY.md` (`agents/eye`, `shared/`, and the rest). Do not rename folders unless that is the task.

```text
ajanlar/goz/        1. Eye — reads Emtia Defteri + Dragonomi, writes one sentence (3 passes a day)
ajanlar/sayac/      1B. Counter — counts stocks / sectors / commodities over the last 7 days (code, no AI)
ajanlar/arastirma/  2. Research — reading + web search + score; opens the card (weekly, Sunday)
ajanlar/analiz/     3. Analysis — SEC / PDF → card.md (quarterly / annual); prototip/ = a rule trial (not production)
ajanlar/teknik/     4. Portfolio (was Technical) — my money: ledger, benchmark, total wealth, new money; backtest/ is here
ortak/              AI, SEC, price, Drive paths, SQLite
ayarlar.yaml        models, budget, hours, stock list
docs/               YOL_HARITASI_v2.md, BAGLAM.md, GLOSSARY.md, TASINANLAR.md, DIS_INCELEME_PROMPT.md, AIR_SETUP.md; reviews/ (external reviews)
```

## Technical

- Python, environment managed with `uv`. Example: `uv run --with pytest pytest -q`
- Development is on the main Mac. The system runs on the backup MacBook Air (Hermes). The bridge is GitHub. No code is written on the Air.
- SQLite stays on the Mac disk. It does **not** go in the Drive folder (sync can corrupt it). A backup is copied to Drive at night.
- Reports and the card are Markdown plus a header (`ticker`, `sector`, `opened`, `publish: no`). The format is roadmap section 3, "Card format". Figures live only in the YAML data block.
- On Telegram the user's only counterpart is Hermes. Hermes runs only the defined command list. It does not change code or rules.
- Model and budget settings live in one place: `ayarlar.yaml`. The AI budget is at most 25–30 $ / month.
- Secrets (API keys) are in `.env`. They are never committed.

## Old project

`../investment-intelligence` (git tag `v1-arsiv`) is only a source library.
Do not add it to the workspace. Do not apply its rules or documents to this project.
If a file is needed, read it by its full path, copy only the piece that is needed, and add a line to `docs/TASINANLAR.md`.

## Current status

- **Last update:** 2026-10-04
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
  Expected golden set: `solid` KO, NVDA · `mid` NKE, SBUX · `weak` PFE, INTC, BA, SNAP, DOW, RIVN.
  Prototype updated to the post-review rules; golden set 10/10 (`ajanlar/analiz/prototip/altin_set.py`): `solid` NVDA · `mid` KO
  (borderline, user-approved), NKE, SBUX · `weak` PFE, INTC, BA, SNAP, DOW, RIVN. IFRS / 20-F works (NVO). Rivian rule: a sector /
  SIC cyclical needs at least 1 profit year in 5 (user-approved, may be revised).
  Item 6, **agent 4**, mostly closed (roadmap section 3, "Agent 4 rules", 2026-10-04): a weekly price watcher, not a trading signal —
  new-money ranking (no new money above 25% weight; above 25% is fine), drop alert (−20% from the 52-week high → agent 3 thesis
  check), valuation watch (PEG > 3 or FCF yield < 1%, 4 weeks), weights in the Sunday summary (`holdings` via Hermes), optional
  SPY 40-week filter. Agent 3 reads 10-Q too (last 4 quarters, TTM); sell-review triggers recorded. SPY filter tests (34 / 40 / 55,
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
  `/bought`, `/sold`, `/gold`, `/bes`, `/analyze`, `/closewarning`, `/thesis`, `/note`, `/data`, `/tag`, `/model`, `/subsector`) in the Telegram `/` menu;
  every change asks for confirmation and is logged.
  **10.3 Air setup checklist written:** `docs/AIR_SETUP.md` (to prepare before it: `.env.example`, `/setcommands` text, Drive test script).
  **AI auditor decided (2026-10-04; roadmap section 3, "AI auditor"):** one auditor (DeepSeek V4 Pro, fallback GPT-6 Sol — a
  different family from the writer), used only in agent 3 (figure, reading, sell audits) and agent 2 (serious-negative events);
  code checks elsewhere; one rule card per place with known traps and an error test set; on a fail `unverified` + Telegram, a sell
  suggestion is held; a big review every 6 months.
- **Next (after the break, 2026-10-04):** 10.4 coding order — the last planning item (the auditor is already decided). Then the
  implementation plan and the UAT plan, building + tests (golden set, auditor error sets, the two model tests, 20-stock UAT),
  step 0 on the Air, then a few months of real use without changing the rules.
  Small open items: the subsector list (needed for tag mapping) · prepare `.env.example`, the `/setcommands` text and the Drive
  test script before the Air setup · the Anthropic API credit expires 2026-10-19 (use it for agent 3's AI parts and the tests) ·
  a third external review is still running · the agent 4 changes are on the branch `claude/agent4-portfolio`, not yet merged into main.
- **Pending questions:** None.
- **Note:** main is on GitHub. The agent 4 (Portfolio) changes of 2026-10-04 are on the branch `claude/agent4-portfolio` (pushed),
  waiting to be merged into main.
