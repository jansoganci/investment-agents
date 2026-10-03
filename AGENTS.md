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
ajanlar/teknik/     4. Technical — weekly state + market filter; backtest/ is here
ortak/              AI, SEC, price, Drive paths, SQLite
ayarlar.yaml        models, budget, hours, stock list
docs/               YOL_HARITASI_v2.md, BAGLAM.md, GLOSSARY.md, TASINANLAR.md, DIS_INCELEME_PROMPT.md; reviews/ (external reviews)
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

- **Last update:** 2026-10-03
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
- **Next:** update the prototype (`ajanlar/analiz/prototip/`) to the new rules and rerun the golden set; then item 6 **agent 4
  (Technical)**, then item 7 **implementation plan**. An AI auditor is last. A third external review is still running.
- **Pending questions:** None.
- **Note:** Commits have not been pushed to GitHub yet. The user wants to push them all together at the end.
