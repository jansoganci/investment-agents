# SCHEDULE — what runs when on the Air (Turkey time)

Decided 2026-10-11 (roadmap, "Agent 2 rules" 9; times in `settings.yaml` `hours`). Hermes runs these as **script-only jobs** (no model
involved; `docs/AIR_SETUP.md` phase 7). A job's printed text is delivered to Telegram; **no output = no message**. Our code does not
know Hermes: every line below also runs by hand.

Every command is run from the production folder `~/Downloads/investment-agents` with the full path of `uv`
(`/Users/jans./.local/bin/uv run python -m …`).

| # | Job | When | Command | Prints (so reaches Telegram) |
|---|---|---|---|---|
| 1 | Prices | every day 03:00 | `python -m shared.prices` | only an error |
| 2 | Backup | every day 04:00 | `python -m shared.backup` | nothing when all is well |
| 3 | Eye | 07:00, 13:00, 20:00 | `python -m agents.eye` | the first-run baseline, pages cut by the paywall, **"the login cookie has probably expired" when the last 5 pages in a row were cut (decision 2026-10-12)**, failures, a block |
| 4 | Alerts | every hour at :05 | `python -m shared.alerts` | only new alerts (grade drop of a holding, new solid, drop alert, auditor disagreement, OpenRouter spend) |
| 5 | Sunday chain | Sunday 09:00 | `python -m shared.sunday` | the Sunday summary |
| 6 | Morning bulletin (`docs/BULLETIN_PLAN.md`) | weekdays **08:10** (`10 8 * * 1-5`; it takes about 3.5 minutes, so the text arrives about 08:14) | `python -m shared.bulletin` | the bulletin in Turkish, about 6–9 thousand characters: the scheduler delivers it as 2–3 messages with (n/N) labels, a header and a footer (Air test T1). A second run on the same day prints the saved text again (`--force` builds it anew); a failed writer sends the figures with a warning and saves nothing. About 0.105 $ a day |

**Lengths:** the bulletin about 3–4 minutes (the writer model thinks for about 2.5 of them); the Eye takes up to about 35 minutes (it waits 20–30 seconds between pages); the Sunday chain about 30–60 minutes (Research
reads and searches for up to 10 stocks, agent 3 asks SEC). The Eye's 07:00 pass ends before 09:00. Do not start the chain by hand while
another pass of the same job runs.

**Order inside the Sunday chain:** Counter → Research (agent 2) → Analysis (agent 3, new filings) → Portfolio (agent 4) → the summary. A step
that fails is named at the top of the summary and the next ones still run. The agents' own messages are not sent separately.

## Before the first scheduled run (once)

1. On the Air: `git pull`, then `uv run python -m shared.db upgrade` (the database must reach version 10).
2. `.env`: `EMTIA_COOKIE`, `DRAGONOMI_COOKIE` (checked on a computer with `python -m agents.eye.session_check` first), `ANTHROPIC_API_KEY`
   (Research's web search runs only on Anthropic), `SEC_UA`, `DRIVE_DIR`.
3. Run each job by hand once and read what it prints: prices, backup, **the Eye (the first run only records the sites' addresses as seen
   and reads nothing)**, alerts, then the Sunday chain after a week of Eye passes (the Counter and Research need posts).
4. Only then register the five jobs with Hermes. After a restart of the Air check that the jobs start again, and that `/status` shows a job
   left `running` for more than an hour and a backup older than 36 hours.

## What needs real data before it can be judged

The Counter and Research have only been tested on stand-in data. After the first week of Eye passes: `python -m agents.counter`, then
`python -m agents.research` (it spends about 0.1–0.3 $ a stock), then read a card and the weekly report in Drive. The score thresholds are
starting values (`settings.yaml` `counter:`; roadmap "Score rules"); adjust them after the first weeks.
