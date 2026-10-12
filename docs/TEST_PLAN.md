# TEST PLAN — the real-world tests of phases 4, 5 and 6 (written 2026-10-11)

Everything that can be tested without the real world is tested (658 tests; the command-line entry points on a clean database; the
upgrade from version 5 to 10). **This plan covers what only the real world can show:** the two sites, a real model, web search, Yahoo's
symbols, Telegram and Hermes. We do it in one run, in this order, with a gate after each block.

## 1. Who does what

| Letter | Who | Does |
|---|---|---|
| **U** | You | what needs a person: logging in to the sites, copying the cookie, judging quality (A / B sentences, cards, the summary), looking at Telegram and Drive, the Hermes limits |
| **M** | Claude Code on your main Mac | commands that need the cookie or the Mac's network: it runs, observes and reports; it changes nothing |
| **H** | Hermes on the Air | commands that need the Air: its keys, its network, Drive, Telegram, scheduled jobs; always in the isolated copy `~/check-repo` until block D |
| **C** | Claude (the cloud session) | reads every RESULT block, marks pass / fail here, fixes what breaks, pushes the fix |

**Flow for every test:** you paste the prompt (or run the commands) → the helper answers with a RESULT block → you paste the block into the
cloud session → C decides: pass (next test), or fix (C pushes, you `git pull` where it matters, the test is repeated).

### Rules for M and H (every prompt repeats them)

1. **Run, observe, report. Do not change code, `settings.yaml` or documents.** A failure is reported, not fixed; C fixes it in the cloud.
2. **Never print, paste or log `.env`, a cookie or an API key.** Do not `cat .env`. To see whether a variable is set: `grep -c '^NAME=.' .env`.
3. **Only the data folders named in the test.** H never touches `~/Downloads/investment-agents` (production), `~/investment-agents-data` (the real
   database) or `~/investing-drive` (the real Drive folder) before block D. M uses the Mac's dev database and `Investing-dev/` only.
4. Stop at the gate. Do not start the next test on your own.
5. End with the RESULT block:

```
TEST <id>: PASS | FAIL | PARTIAL
Ran: <the commands, one line each>
Numbers: <counts, costs, times>
Problems: <exact error text, or none>
Paths: <files created>
```

## 2. The environments

| Name | Where | Code | Data (database) | Drive folder |
|---|---|---|---|---|
| Mac dev | your main Mac | the repo, `main` | `~/investment-agents-data` (dev) | `…/Investing-dev` (`DRIVE_DIR` in the Mac's `.env`) |
| Air check | the Air | `~/check-repo` (a throwaway clone) | throwaway folders named in each test | throwaway folders |
| Air production | the Air | `~/Downloads/investment-agents` | `~/investment-agents-data` (real) | `~/investing-drive` → `Investing/` (real) |

## 3. The order at a glance

The Anthropic credit (90 $) **expires on 2026-10-19**, so the real-model tests come first (block A) and need no login.
Costs are estimates; everything together should stay under about 8 $.

| ID | Who | Test | Needs | Time | Cost | Gate (go on only if) |
|---|---|---|---|---|---|---|
| **A — no login needed** | | | | | | |
| A1 | M | Mac baseline: pull, 658 tests, dev database at version 10 | — | 5 min | 0 | 658 pass |
| A2 | H | Air check baseline: pull, 658 tests, fresh database at version 10 | — | 5 min | 0 | 658 pass |
| A3 | H | Upgrade rehearsal: a copy of the real Air database, version 5 → 10 | A2 | 5 min | 0 | every old row still there, integrity ok |
| A4 | H | Real models: `ai ping`, the auditor test set (with the 5 new event cases) | A2 | 10 min | ~0.2 $ | no unexpected misses |
| A5 | H | Research with web search on 3 real stocks: NVDA, FCX (copper producer), DAL (oil user) | A4 | 30 min | ~1–2 $ | web search answers, JSON accepted, 3 cards born |
| A6 | H | Yahoo: every commodity symbol and sector fund returns prices | A2 | 5 min | 0 | no symbol fails (or the failing ones are listed) |
| A7 | U | Read the three cards from A5: are the story, the reasons and the events believable? | A5 | 10 min | 0 | you would trust them as a first look |
| **B — the sites (cookie), on the Mac** | | | | | | |
| B1 | U | Log in to both sites, put the cookies into the Mac's `.env`, note their expiry | — | 10 min | 0 | — |
| B2 | M | `session_check` for both sites | B1 | 3 min | 0 | both say `OK` |
| B3 | M | Eye baseline on the Mac dev database, run twice | B2 | 5 min | 0 | ~11k + ~15k addresses recorded, nothing read; the second run is quiet |
| B4 | M | Un-see the 8 newest addresses of each site, run a pass: it reads them | B3 + AI keys | 15 min | ~0.1 $ | 16 posts read, sentences and tags written |
| B5 | M + U | Look at what B4 stored: texts, sentences, tags, `Inbox/` | B4 | 10 min | 0 | sentences are neutral English, tags are sensible, glossary posts absent |
| B6 | M + U | The cheap-model test: 20 posts, hidden A / B, you choose | B5 | 20 min | ~0.3 $ | you can name the better model |
| B7 | M | Counter, then Research for one stock the Counter listed | B5 | 15 min | ~0.5 $ | a ranking appears; the card is born |
| B8 | M + U | The Sunday chain once (`shared.sunday`), alerts, `/summary`, `/candidates` | B7 | 20 min | ~2 $ | the summary reads well |
| **C — the Air reads the sites** | | | | | | |
| C1 | U | Put the cookies into `~/check-repo/.env` on the Air (by ssh, not through Telegram) | B2 | 5 min | 0 | — |
| C2 | H | Eye on the Air: baseline, un-see 5 per site, one pass (throwaway folders) | C1, A2 | 15 min | ~0.1 $ | it reads the posts from the Air's network |
| C3 | H | Telegram path of the new jobs: one-off script-only jobs for `shared.commands status` and `shared.alerts` | A2 | 10 min | 0 | both messages reach your Telegram |
| **D — production** | | | | | | |
| D1 | H (+U) | Back up the real database, `git pull`, upgrade to version 10 in production | A3, C2, C3 | 10 min | 0 | version 10, old rows intact |
| D2 | U + H | Cookies into the production `.env`; the Eye baseline in production | D1 | 10 min | 0 | addresses recorded; `Inbox/` appears in Drive |
| D3 | H | Register the five scheduled jobs one by one (`docs/SCHEDULE.md`), fire each once | D2 | 30 min | small | each job's message arrives |
| D4 | U | **Hermes limits** (`AIR_SETUP.md` phase 5) and its tests | D3 | 30 min | 0 | the limits hold |
| **E — the week** | | | | | | |
| E1 | U | Every day, 2 minutes: `/status`, `/spend`, a look at `Inbox/` | D3 | — | — | no block, no error |
| E2 | M or H | Day 3: statistics; fix the waiting tags with `/tag` | E1 | 15 min | — | few waiting tags |
| E3 | U | Sunday: read the summary and two cards | E1 | 20 min | ~2 $ | the first real Sunday works |
| E4 | C | The audit sessions of phases 4, 5, 6 (prompts from C) | E3 | — | — | no blocker |

Already verified in the cloud (do **not** repeat): the 658 unit and integration tests; every command-line entry point on a clean database; the
version 5 → 10 upgrade with rows; static analysis of the code.

## 4. The tests, one by one

### A1 · Mac baseline (M)
Run: `git checkout main && git pull && uv sync && uv run pytest -q`; check the Mac's `.env` points at the dev Drive folder
(`grep '^DRIVE_DIR=' .env` must end with `Investing-dev`); `uv run python -m shared.db init` and `info`.
**Pass:** 658 passed; `DRIVE_DIR` ends with `Investing-dev`; database version 10. **If `DRIVE_DIR` is the real `Investing/` — stop and tell me.**

### A2 · Air check baseline (H)
Run in `~/check-repo`: `git pull --ff-only`, `uv sync`, `uv run pytest -q`; then with fresh throwaway folders
(`export DATA_DIR=~/check-data DRIVE_DIR=~/check-drive`, `rm -rf` and recreate) `uv run python -m shared.db init`.
**Pass:** 658 passed; version 10.

### A3 · Upgrade rehearsal (H)
The Air's real database is at version 5 with real rows (the cards of NVDA and PLTR and so on). Make a safe copy
(`sqlite3 ~/investment-agents-data/investment-agents.sqlite ".backup '$HOME/check-data2/investment-agents.sqlite'"`; the original is only read),
count the rows of every table in the copy, run `DATA_DIR=~/check-data2 uv run python -m shared.db upgrade`, count again, run
`PRAGMA integrity_check` and `PRAGMA foreign_key_check`.
**Pass:** the version is 10; every table that existed has the same row count; the checks say `ok` and nothing. **Fail → the real upgrade (D1) must not run.**

### A4 · Real models and the auditor (H)
Run in `~/check-repo` with the throwaway folders: `uv run python -m shared.ai ping` (which models answer, what each costs);
`uv run python -m shared.auditor testset` (the old cases plus **5 new event cases**: a real CFO departure must pass; a competitor's
investigation, a general risk sentence, a 2021 event and a planned retirement must fail).
**Pass:** ping answers for the first model of each job; the test set catches all, or the misses are listed (a miss is information, not a crash).

### A5 · Research with web search (H)
Run `uv run python -m agents.research NVDA`, then `FCX`, then `DAL` (throwaway folders; each is one stock "added by me").
Then read the database: `uv run python -m shared.ask sql "SELECT job, provider, model, cost_usd FROM ai_calls ORDER BY id DESC LIMIT 12"` and
`... "SELECT ticker, class, scope, status, note, source_url FROM news_events"` and `... "SELECT * FROM commodity_links"`.
**Pass:** the web search call is in `ai_calls` with the Anthropic model; each stock got a score with five reasons; FCX has a copper link as
`producer` and DAL has a crude oil link as `user`; every event has a source address; the cards exist in the throwaway Drive folder; the cost is under 1 $ a stock.
**What to look for:** an `unclear — the news could not be checked` reason means the web search or its JSON failed — paste the error text.

### A6 · Yahoo symbols (H)
Run the script in appendix B (H6): it asks Yahoo for every commodity symbol of `settings.yaml` and the 11 sector funds and prints OK / FAIL with
the number of rows. **Pass:** all OK. Failing symbols are listed; C replaces them (for example `LBR=F`, `LE=F`, `HE=F`, `PL=F`, `PA=F` are the doubtful ones).

### A7 · You read the three cards (U)
H pastes the research entry of each card. Read them as an investor: does the story say what the company sells? Are the reasons specific (a
quote, a number, a source) or vague? Does an event you know about appear, or a wrong one? Say "believable" or what was wrong.

### B1 · Cookies into the Mac `.env` (U)
For each site: log in in your browser with the e-mail link → open any post → developer tools → Network → reload → click the request of the
post → Request Headers → copy the whole value of `cookie`. Write it into `.env` with the commands in appendix C (U2) — the value is never shown.
Also open Application → Cookies and write down the expiry date of the login cookie (it tells us how often you must renew).

### B2 · `session_check` (M)
`uv run python -m agents.eye.session_check emtia` and `... dragonomi` (three requests each, six seconds apart). **Pass:** both end with `OK` and the
first 200 characters of the cookie page are real text. **Fail:** the output says why (still gated, no body found); paste it in full.

### B3 · Eye baseline (M)
`uv run python -m agents.eye` twice. The first run records every address of both sitemaps as seen and reads nothing. Then
`uv run python -m shared.ask sql "SELECT site, how, count(*) FROM eye_seen GROUP BY 1,2"`. **Pass:** about 11,000 (Emtia) and 15,000 (Dragonomi)
`baseline` rows; the second run prints nothing or only a few new posts.

### B4 · Read some real posts (M)
Make 8 recent posts per site "new" with the snippet in appendix B (M4), then `uv run python -m agents.eye` (about 7 minutes: it waits 20–30 s per page).
Needs the cheap model's key (`DEEPSEEK_API_KEY` or `OPENROUTER_API_KEY`) and `SEC_UA` in the Mac's `.env`.
**Pass:** the pass ends without a block; 16 rows in `articles`; their `full_text` is long (not the paywall's 900 characters); most have a `sentence`.

### B5 · Look at what was stored (M + U)
M prints: per site the number of posts, the average text length, how many are `text_missing`, 6 titles with their sentences, the tags table
by `kind` and `status` (10 examples), the `Inbox/` file. You judge: are the sentences neutral and correct? Is a Chinese company tag stored as a
non-US company without a question? Is a US company confirmed with the right ticker? Were glossary posts skipped?

### B6 · The cheap-model test (M + U)
First make about 14 more posts per site "new" and read them (B4 again), so that 20+ readable posts exist. Then
`uv run python -m agents.eye.modeltest 20 default sonnet-5.5`. You read 20 posts with two hidden sentences each (A / B). Pick the better
model overall and say why; then `... modeltest --reveal`. If the default (DeepSeek V4 Flash) is clearly worse, C changes the order in `settings.yaml`.

### B7 · Counter and one Research (M)
`uv run python -m agents.counter`, then `uv run python -m agents.research <a ticker from the Counter's list>`. **Pass:** a ranking prints; the
stock gets a score and a card under `Investing-dev/Stocks/`. (With only 16–40 posts the ranking is thin; that is expected.)

### B8 · The Sunday chain once (M + U)
`uv run python -m shared.sunday`, then `uv run python -m shared.alerts`, then `/summary` and `/candidates` (`uv run python -m shared.commands summary`).
You read the summary: is it clear, is anything missing, is it too long? Check that it stays within one Telegram message (about 4,000 characters).

### C1 · Cookies on the Air (U)
By ssh from your Mac, into `~/check-repo/.env` only (appendix C, U4). Never through Telegram or Hermes.

### C2 · The Eye on the Air (H)
Same as B3 and B4, in `~/check-repo` with throwaway folders and 5 posts per site. **Pass:** the Air reads the sites with the cookie (the Air's network may be treated differently).

### C3 · Telegram path (H)
Create two one-off script-only jobs for the check copy: one runs `uv run python -m shared.commands status`, one runs `uv run python -m shared.alerts`.
Fire them and look at your Telegram, then delete the jobs. With nothing new, the alerts job prints nothing and no message should arrive (that is the
correct result). **Pass:** the status message arrives intact, and the alerts job sends nothing.

### D1 · Production upgrade (H, with your yes)
In `~/Downloads/investment-agents`: `uv run python -m shared.backup`, then `git pull --ff-only`, `uv sync`, `uv run python -m shared.db upgrade`, `uv run python -m shared.db info`.
(Do **not** run the test suite in production; A2 did.) **Pass:** version 10; the row counts match A3's rehearsal.

### D2 · Production cookies and baseline (U + H)
You put the cookies into the production `.env` (appendix C, U4). H runs `uv run python -m agents.eye` once (the baseline). **Pass:** `eye_seen` is
filled; `/status` shows the `eye` job `ok`.

### D3 · The five scheduled jobs (H)
From `docs/SCHEDULE.md`: prices 03:00, backup 04:00, Eye 07:00 / 13:00 / 20:00, alerts hourly at :05, the Sunday chain at 09:00 on Sunday. Register them
one at a time as Hermes script-only jobs with the full path of `uv`; fire each once by hand; confirm the message (or silence) is right. **Pass:** all five registered, `/status` shows them.

### D4 · Hermes limits (U) — last, as decided
`docs/AIR_SETUP.md` phase 5, done in the Air's terminal; then its tests (approval for `--yes`, another Telegram account gets no answer, `.env` is refused).

### E1–E4 · The week
Every day: `/status` (no `WARNING`), `/spend`, one look at the day's `Inbox/` file. Day 3: M or H prints statistics (posts per day, `text_missing`
share, cost per day, waiting tags); you fix waiting tags with `/tag`. Sunday: the first full chain; you read the summary and two cards. Then C writes the
audit prompts for phases 4, 5 and 6.

## 5. Where I expect trouble (so it is no surprise)

1. **The real pages differ from my hand-made test pages** (B2–B5): selectors, the cookie page's markup, a different gate. The fix is a selector in `sites.py`.
2. **Web search** (A5): this is the first real call of `web_search_20260209`; the model may answer in a shape the parser rejects, or take long. The fix is small.
3. **Yahoo symbols** (A6): lumber, cattle, hogs, platinum and palladium futures may not exist under those names.
4. **Sentence quality** (B5, B6): the cheap model may add opinion or mistranslate; the fix is the prompt or the model order.
5. **Tags** (B5): the model may mark a US company non-US or miss a ticker; those wait for your `/tag`, which is the safe direction.
6. **Time and cost**: a pass is slow on purpose; the web search turns may run a minute or two each.
7. **Telegram length** (B8, C3): the summary is cut at 4,096 characters; the full text is in Drive.

## 6. Results log (C fills it in as the RESULT blocks arrive)

**Decision (U, 2026-10-11): Dragonomi is postponed.** U has no Dragonomi membership yet, so no Dragonomi cookie. Blocks B and C run on Emtia Defteri only; every step
that names two sites is done for Emtia now and for Dragonomi later (one short extra round: cookie, `session_check dragonomi`, baseline, one read pass). The Eye already
copes: a site without a cookie is not read and its new addresses stay "waiting" (`EMTIA_COOKIE is not set` style note). Watch: waiting addresses of both sites count
toward the 200-address guard, so a long postponement needs `--accept-many` or a "skip this site" setting (not built; decide when it matters).

| ID | Who | Date | Result | Notes |
|---|---|---|---|---|
| A1 | M | 2026-10-11 | SKIPPED | The main Mac is away; A2 ran the same 658 tests on the Air check copy. Not needed for the next blocks. |
| A2 | H | 2026-10-11 | PASS | `~/check-repo` at fb76bd2: 658 passed in 42 s (the throwaway `db init` step was skipped; A3 covers the upgrade). Run by U in the Air terminal. |
| A3 | H | 2026-10-11 | PASS | Copy of the real Air database (version 5) upgraded to 10 (steps 6–10) in `~/check-data2`. All 20 old tables kept their row counts (stocks 5, prices 4382, financials 576, card_entries 6, ai_calls 22, runs 13 …); 5 new tables, all empty. `integrity_check` ok, `foreign_key_check` empty. D1 may run. Run by U in the Air terminal. |
| A4 | U | 2026-10-11 | PASS | `ai ping` 8/8. Auditor test set (42e5eed) **21/21 caught**, incl. the 5 new event cases and the GE cases; month spend 0.22 $. (First attempt was stopped by Ctrl-C because the run printed nothing until the end; it now prints a line per case.) |
| A5 | U | 2026-10-11 | PASS (with 2 findings) | `~/check-repo` 42e5eed, throwaway folders. NVDA 5/10, FCX 4/10, DAL 3/10 (the five parts add up). NVDA 2:28, FCX 0:37, DAL 0:47; cost 0.43 / 0.15 / 0.20 $ (month so far 0.86 $). FCX: copper + gold links as `producer`; DAL: crude oil as `user`; 3 cards in `~/check-drive/Stocks/`. NVDA: Bloomberg page refused (HTTP 403) → `not_confirmed` (right); the France-regulator case confirmed → news 0. DAL: guidance cut of 2026-10-09 confirmed. **Finding 1:** an `important_positive` event has no age limit and its page is not read: FCX got news 2 for an item dated 2026-02-18 whose source is the generic news-release list page. **Finding 2:** sources are often secondary sites (pymnts, asktraders) although the company's own 8-K was in the search results (DAL). Both are proposals for U to decide, nothing built. |
| A6 | U | 2026-10-11 | PASS | All 30 symbols OK (17 commodity futures, URA, 11 sector funds, SPY). The doubtful ones work: LBR=F has only 1,050 rows (from 2022-08, enough for a 40-week average), LE=F, HE=F, PL=F, PA=F have full history. CT=F ends 2026-10-08 (one day behind, harmless). |
| A7 | U | 2026-10-11 | PASS | NVDA, FCX, DAL cards read by U: "ok for now". Open small item (not a blocker): the Research `quick_health` debt check for NVDA uses the last annual year (cash and investments 10.61 bn, debt 8.47 bn) while agent 3 on the last 4 quarters has debt 33.4 bn; the result (`pass`) is the same, the shown figures are older. Decisions pending from U: positive events within 90 days (C proposes yes), secondary sources (C proposes leave). |
| B1 | U | 2026-10-12 | PASS (Emtia only) | Cookie copied from Chrome (`Copy as cURL`), written by `agents.eye.set_cookie emtia` (313 characters). Expiry date of the login cookie: not yet noted. The cookie was pasted into the cloud chat by mistake: after the tests, log out of Emtia and log in again. Dragonomi: no membership yet. |
| B2 | U (on the Air) | 2026-10-12 | PASS (Emtia only) | `session_check emtia`: without the cookie the page is gated, 0 characters; with it not gated, 833 characters, body found by `article.ghost-content`, tags read (Alüminyum, Sanayi Metalleri, Asya). The extractor and the gate check work on the real site. A leftover broken `DRAGONOMI_COOKIE` line in `~/check-repo/.env` causes a harmless dotenv warning; to be deleted. |
| B3 | U (on the Air) | 2026-10-12 | PASS | Eye baseline in throwaway folders: Emtia 11,126 and Dragonomi 14,906 addresses recorded as `baseline`, nothing read, 28 s. Second run: quiet (only the note that `DRAGONOMI_COOKIE` is not set), 29 s. |
| B4 | U (on the Air) | 2026-10-12 | PASS (Emtia only) | 10 newest Emtia posts un-seen and read in 5 min 28 s (20–30 s pause per page, no block): 10 rows in `articles`, average text 815 characters (short flash posts, `text_missing` 0), 10 sentences, none empty; cost 0.01 $ (11 DeepSeek calls). A quiet pass prints nothing for the site that was read fine (by design). |
| B5 | U | 2026-10-12 | PARTIAL | Sentences are neutral English, factual ("The post says …"), no advice words (0 hits for should / bullish / bearish). Tags: 10 commodity, 3 region, 1 sector (Fosil Enerji → Energy), 1 other (Rapor Özetleri), all `confirmed`. Not testable with Emtia alone: company tags, the SEC check, a non-US company without a question, glossary posts (Emtia's 10 posts carry commodity tags, no company tag). `Inbox/2026-10-12.md` exists; U to read it. Watch for B7: the Counter counts company tags, so with Emtia only it may list no stock; Dragonomi's tags are the company ones. |
| B6 | M+U | | — | |
| B7 | M | | — | |
| B8 | M+U | | — | |
| C1 | U | | — | |
| C2 | H | | — | |
| C3 | H | | — | |
| D1 | H | | — | |
| D2 | U+H | | — | |
| D3 | H | | — | |
| D4 | U | | — | |
| E1–E3 | U | | — | |
| E4 | C | | — | |

---

## Appendix A — prompts for Hermes (paste into Telegram, one at a time)

Every Hermes prompt starts with the same block. It is repeated here once; **paste it at the top of each prompt**.

```
COMMON RULES (every task): You work on the Air in the isolated copy ~/check-repo with throwaway data folders only. NEVER touch
~/Downloads/investment-agents, ~/investment-agents-data or ~/investing-drive. Do not change code, settings or documents: run, observe, report.
Never print, paste or log .env, cookies or API keys (do not cat .env). If a command fails, stop that step and report the exact error text.
Stop at the end of the task; do not start another. Answer in at most 3 Telegram messages of under 3500 characters, ending with:
TEST <id>: PASS | FAIL | PARTIAL / Ran: / Numbers: / Problems: / Paths:
```

**H-A2 — baseline**
```
TASK A2. In ~/check-repo: git pull --ff-only; uv sync; uv run pytest -q (expect 658 passed; report the count and any failure).
Then: rm -rf ~/check-data ~/check-drive; mkdir -p ~/check-data ~/check-drive; export DATA_DIR=~/check-data DRIVE_DIR=~/check-drive;
uv run python -m shared.db init (expect version 10).
```

**H-A3 — upgrade rehearsal on a copy of the real database**
```
TASK A3. Rehearse the upgrade on a COPY; the original is only read. Steps:
1. rm -rf ~/check-data2; mkdir -p ~/check-data2
2. sqlite3 ~/investment-agents-data/investment-agents.sqlite ".backup '$HOME/check-data2/investment-agents.sqlite'"
3. Count rows of every table in the copy (read-only), saving the list as "before". Use:
   python3 - <<'EOF'
   import sqlite3, os
   p = os.path.expanduser("~/check-data2/investment-agents.sqlite")
   c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
   print("version", c.execute("pragma user_version").fetchone()[0])
   for (t,) in c.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by 1").fetchall():
       print(t, c.execute(f'select count(*) from "{t}"').fetchone()[0])
   EOF
4. cd ~/check-repo; DATA_DIR=~/check-data2 DRIVE_DIR=~/check-drive uv run python -m shared.db upgrade
5. Run the same counting script again ("after"), then PRAGMA integrity_check and PRAGMA foreign_key_check on the copy.
Report: version before/after; for every table that existed before, whether the count is the same; the new tables; the two checks.
```

**H-A4 — real models and the auditor**
```
TASK A4. export DATA_DIR=~/check-data DRIVE_DIR=~/check-drive; cd ~/check-repo.
1. uv run python -m shared.ai ping  → report which models answered and the cost.
2. uv run python -m shared.auditor testset  → report every line that says MISS with its reason, and the final line. There are 5 new
   "event" cases; say separately whether each of them was caught as expected.
Then: uv run python -m shared.commands spend  → the cost so far.
```

**H-A5 — Research with web search**
```
TASK A5. export DATA_DIR=~/check-data DRIVE_DIR=~/check-drive; cd ~/check-repo. Run these three, one after the other, and report how long each took:
  uv run python -m agents.research NVDA
  uv run python -m agents.research FCX
  uv run python -m agents.research DAL
Then run these read-only questions and paste the results (shorten long cells to 160 characters):
  uv run python -m shared.ask sql "SELECT id, job, provider, model, cost_usd, outcome FROM ai_calls ORDER BY id DESC LIMIT 15"
  uv run python -m shared.ask sql "SELECT ticker, class, scope, status, note, source_url FROM news_events"
  uv run python -m shared.ask sql "SELECT s.ticker, l.commodity, l.role, l.source FROM commodity_links l JOIN stocks s ON s.id = l.stock_id"
  uv run python -m shared.ask sql "SELECT s.ticker, c.score, c.mentions, c.tone, c.sector_tailwind, c.news_flow, c.quick_health FROM scores c JOIN stocks s ON s.id = c.stock_id"
Finally print, for each of the three, the research entry of its card (uv run python -m shared.ask card NVDA, and so on) — only the part from the line
"## … · research · agent_2" to the end. If any reason says "unclear", copy that reason in full.
```

**H-A6 — Yahoo symbols**
```
TASK A6. export DATA_DIR=~/check-data DRIVE_DIR=~/check-drive; cd ~/check-repo. Run this script and paste its output unchanged:
uv run python - <<'EOF'
from shared import config, db as dbmod, prices
from shared.prices import SECTOR_FUNDS
dbmod.init(); conn = dbmod.connect()
symbols = list(config.settings()["commodity_symbols"].values()) + list(SECTOR_FUNDS.values()) + ["SPY"]
for sym in symbols:
    try:
        prices.ensure_history(conn, sym)
        n, first, last = conn.execute("SELECT count(*), min(date), max(date) FROM prices WHERE symbol=?", (sym,)).fetchone()
        print("OK  " if n > 200 else "THIN", sym, n, first, last)
    except Exception as e:
        print("FAIL", sym, type(e).__name__, str(e)[:120])
EOF
```

**H-C2 — the Eye on the Air (after C1)**
```
TASK C2. rm -rf ~/check-data3 ~/check-drive3; mkdir -p ~/check-data3 ~/check-drive3; export DATA_DIR=~/check-data3 DRIVE_DIR=~/check-drive3; cd ~/check-repo.
1. uv run python -m shared.db init
2. uv run python -m agents.eye   (the first run only records addresses; say how many per site: uv run python -m shared.ask sql "SELECT site, how, count(*) FROM eye_seen GROUP BY 1,2")
3. Make 5 recent posts per site new again:
   uv run python - <<'EOF'
   from agents.eye import http, sitemap
   from agents.eye.sites import SITES
   from shared import db as dbmod
   conn = dbmod.connect()
   for key, site in SITES.items():
       entries = sitemap.posts(site, http.fetch(site.posts_sitemap, timeout=90).body)
       newest = sorted(entries, key=lambda e: e.lastmod)[-5:]
       conn.executemany("DELETE FROM eye_seen WHERE url = ?", [(e.url,) for e in newest])
       print(key, "un-seen", len(newest))
   conn.commit()
   EOF
4. uv run python -m agents.eye  (about 5 minutes; do not interrupt)
5. uv run python -m shared.ask sql "SELECT site, count(*), round(avg(length(full_text))), sum(text_missing), sum(sentence IS NOT NULL) FROM articles GROUP BY site"
Report the numbers and anything the pass printed.
```

**H-C3 — the Telegram path**
```
TASK C3. Create two ONE-OFF script-only jobs (no model), fire each once, tell me exactly what arrived on my Telegram, then delete both jobs:
  job 1: cd ~/check-repo && DATA_DIR=~/check-data DRIVE_DIR=~/check-drive /Users/jans./.local/bin/uv run python -m shared.commands status
  job 2: cd ~/check-repo && DATA_DIR=~/check-data DRIVE_DIR=~/check-drive /Users/jans./.local/bin/uv run python -m shared.alerts
Job 2 should print nothing when there is nothing new; say whether Hermes sent an empty message or none.
```

**H-D1 — production upgrade (only after my "yes D1")**
```
TASK D1 (production; I said yes). In ~/Downloads/investment-agents: uv run python -m shared.backup; git pull --ff-only; uv sync;
uv run python -m shared.db upgrade; uv run python -m shared.db info. Do not run the test suite here. Report the version and the row counts of stocks,
card_entries, holdings, articles, tags, counts, eye_seen.
```

## Appendix B — prompts for Claude Code on your Mac

Start it in the repo: `cd <your repo> && claude`. It reads `CLAUDE.md` and `AGENTS.md` by itself (and answers you in Turkish). **Paste this at the top of each task:**

```
COMMON RULES: You are doing a real-world test, not development. Run, observe, report. Do not change code, settings.yaml or documents, and do not
commit. NEVER print, paste or log .env, a cookie or an API key (do not cat .env; to check a variable use grep -c '^NAME=.' .env). Use only the
Mac's dev database (the default ~/investment-agents-data) and the dev Drive folder whose name ends with Investing-dev; if DRIVE_DIR does not end with
Investing-dev, stop and tell me. Stop at the end of the task. End with:
TEST <id>: PASS | FAIL | PARTIAL / Ran: / Numbers: / Problems: / Paths:
```

**M-A1 — baseline**
```
TASK A1. git checkout main && git pull && uv sync && uv run pytest -q (expect 658 passed). Check: grep '^DRIVE_DIR=' .env | sed 's/.*\///' must print Investing-dev.
Show which keys are set without showing them: for N in ANTHROPIC_API_KEY DEEPSEEK_API_KEY OPENAI_API_KEY OPENROUTER_API_KEY SEC_UA EMTIA_COOKIE DRAGONOMI_COOKIE;
do echo $N $(grep -c "^$N=." .env); done. Then uv run python -m shared.db init and info.
```

**M-B2 — session check**
```
TASK B2. uv run python -m agents.eye.session_check emtia ; then uv run python -m agents.eye.session_check dragonomi. Paste both outputs in full
(they never print the cookie). Add one line per site: the final OK / NOT OK verdict.
```

**M-B3 — the baseline**
```
TASK B3. uv run python -m agents.eye   (the first run only records addresses). Then
uv run python -m shared.ask sql "SELECT site, how, count(*) FROM eye_seen GROUP BY 1,2"
Run uv run python -m agents.eye a second time; paste what it printed (it should print nothing, or a few new posts) and the same count again.
```

**M-B4 — read real posts**
```
TASK B4. Make the 8 newest posts of each site new again, then run a pass:
uv run python - <<'EOF'
from agents.eye import http, sitemap
from agents.eye.sites import SITES
from shared import db as dbmod
conn = dbmod.connect()
for key, site in SITES.items():
    entries = sitemap.posts(site, http.fetch(site.posts_sitemap, timeout=90).body)
    newest = sorted(entries, key=lambda e: e.lastmod)[-8:]
    conn.executemany("DELETE FROM eye_seen WHERE url = ?", [(e.url,) for e in newest])
    print(key, "un-seen", len(newest))
conn.commit()
EOF
time uv run python -m agents.eye     # about 7 minutes; do not interrupt
Report what the pass printed and: uv run python -m shared.ask sql "SELECT site, count(*), round(avg(length(full_text))), sum(text_missing), sum(sentence IS NOT NULL), sum(sentence = '') FROM articles GROUP BY site"
```

**M-B5 — what was stored**
```
TASK B5. Print (read-only, via uv run python -m shared.ask sql "..."), shortening cells to 200 characters:
1. SELECT site, title, sentence FROM articles ORDER BY id LIMIT 6
2. SELECT kind, status, count(*) FROM tags GROUP BY 1,2
3. SELECT tag, kind, maps_to, exchange, country, us_listed, status, note FROM tags ORDER BY id DESC LIMIT 15
4. SELECT count(*) FROM articles WHERE sentence LIKE '%should%' OR sentence LIKE '%bullish%' OR sentence LIKE '%bearish%'
Then show the newest file in the dev Drive folder's Inbox/ (cat it; it is a public summary, no secrets) and the cost: uv run python -m shared.commands spend.
```

**M-B6 — the cheap-model test** (after reading about 30 posts: run M-B4 twice more with 14 instead of 8)
```
TASK B6. uv run python -m agents.eye.modeltest 20 default sonnet-5.5 — paste its whole output so I can judge A against B. Do NOT run --reveal.
```
Then, after you have chosen: `uv run python -m agents.eye.modeltest --reveal`.

**M-B7 — Counter and one Research**
```
TASK B7. uv run python -m agents.counter  (paste it). Then pick the top US stock of its list and run uv run python -m agents.research <TICKER>; paste the message
and the card's research entry (uv run python -m shared.ask card <TICKER>, from the "· research · agent_2" line on). Report the cost.
```

**M-B8 — the Sunday chain**
```
TASK B8. uv run python -m shared.sunday   (about 10–30 minutes). Paste the whole summary. Then uv run python -m shared.alerts and
uv run python -m shared.commands candidates ; uv run python -m shared.commands summary ; uv run python -m shared.commands status. Say how many characters the summary has.
```

## Appendix C — the terminal commands for you

**Read first.** (1) zsh does **not** treat `# text` after a command as a comment, so the blocks below have no comments; if you ever paste a line with one,
run `setopt interactive_comments` once in that window. (2) Check which machine you are on: `hostname` and `ls -d ~/investment-agents ~/Downloads/investment-agents ~/check-repo`.
On the **Air** the production copy is `~/Downloads/investment-agents` and the throwaway check copy is `~/check-repo`; there is no `~/investment-agents`.
On the **main Mac** use the folder where you cloned the repo (the examples say `~/investment-agents`; replace it).

**U1 — the Mac, once** (replace the folder name with yours):
```bash
cd ~/investment-agents
git checkout main && git pull
uv sync
test -f .env || cp .env.example .env ; chmod 600 .env
grep '^DRIVE_DIR=' .env | sed 's/.*\///'
for N in ANTHROPIC_API_KEY DEEPSEEK_API_KEY OPENAI_API_KEY OPENROUTER_API_KEY SEC_UA; do echo $N $(grep -c "^$N=." .env); done
```
The `DRIVE_DIR` line must print `Investing-dev` on the main Mac. A `0` next to a key means it is missing; add it by hand with an editor (`nano .env`). `SEC_UA` looks like `"Your Name you@mail.com"`.

**U2 — the cookies into `.env` (the value is never shown on the screen).** In Chrome open the post, then `Cmd+Option+I` → Network → reload the page (`Cmd+R`) → in the list click the row of the post (type `document`) → right-click it →
**Copy → Copy as cURL (bash)**. (Or copy the `cookie` header value from Request Headers.) Then run the helper — it reads the clipboard, replaces the site's old line, removes broken lines left by earlier tries (the old file stays as
`.env.bak`), makes the file private and empties the clipboard. It prints only the name and the length:
```bash
cd ~/investment-agents
uv run python -m agents.eye.set_cookie emtia
```
For the second site copy its cookie value and run `uv run python -m agents.eye.set_cookie dragonomi`. Do **not** use `read -s -p` (in zsh `-p` means
something else; it wrote an empty line on 2026-10-11) and do not build the line with `printf`: a copy with several lines broke `.env` on 2026-10-11.
Check: `uv run python -m agents.eye.session_check emtia`. When all is well: `rm .env.bak`.

**U3 — session check yourself** (instead of M, if you prefer):
```bash
uv run python -m agents.eye.session_check emtia
uv run python -m agents.eye.session_check dragonomi
```

**U4 — the cookies on the Air.** Sitting at the Air itself (the case since 2026-10-11), do U2 with `cd ~/check-repo` (and later `cd ~/Downloads/investment-agents` in
block D). By ssh the helper would read the Air's clipboard, not your Mac's, so avoid ssh for this. The check copy also needs the Air's keys (already
there on 2026-10-11); if ever missing, copy them once with `grep -E '^(ANTHROPIC|DEEPSEEK|OPENAI|OPENROUTER)_API_KEY=|^SEC_UA=' ~/Downloads/investment-agents/.env >> ~/check-repo/.env`.

**U5 — what you look at in Telegram:** `/status` (no `WARNING` lines), `/spend`, `/candidates`, `/summary`, `/tag` (the tags that wait for you).

## Appendix D — style and flow (the advice)

1. **One test, one RESULT block, one decision.** Paste the helper's RESULT block into the cloud session as it is; C answers with "pass, next" or a fix. Do not
   stack three tests before reporting; a failure in test 2 changes test 3.
2. **Block A first, today.** It needs no login and spends the credit that expires on the 19th; it also tests the riskiest unproven piece (web search).
   While H works on A, you do B1 (the cookies) in parallel — they do not depend on each other.
3. **Keep the machines apart.** M never writes to the Air; H never touches production before D1; the cookie goes into each `.env` by your own hands.
4. **When something fails, do not retry it ten times.** One retry to rule out the network, then paste the error. A fix usually takes minutes, and
   after it you only `git pull` in the place where the test runs.
5. **Pass criteria are the contract.** If a result is "kind of fine", say what is odd; I would rather adjust a threshold on purpose than discover it in week 2.
6. **Expect two fix rounds.** My guess: blocks A and B each produce 2–5 small findings (a selector, a symbol, a prompt, a message length). Block D is
   mostly paperwork. The whole run is about two evenings, with the one-week watch afterwards.
