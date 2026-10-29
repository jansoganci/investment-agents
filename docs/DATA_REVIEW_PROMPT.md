# Data review prompt — what do two weeks of collected data tell us about improving the system?

Written 2026-10-29. Use it when the database has about two weeks or more of real passes (Eye, Counter, bulletins).
It is a prompt for a Claude Code session on a **copy** of the database. It produces a ranked list of proposals; it changes nothing.

## Where to run it

1. On the Air, make a copy: `sqlite3 ~/investment-agents-data/investment-agents.sqlite ".backup '/tmp/review.db'"` (the real database is never opened by the review).
2. Copy `review.db` to the main Mac (AirDrop / Drive, not Telegram). Never copy `.env`.
3. On the Mac, open Claude Code in this repository and paste the prompt below. Put the copy's path where the prompt says `<PATH>`.

Why the Mac and not Hermes: the full text is about 10 MB (roughly 2.5 million tokens), Hermes' tool limit is 300 s, and a review needs many queries.

## The prompt

```text
You are reviewing the first two weeks of real data of this project (read AGENTS.md and docs/YOL_HARITASI_v2.md first; the fixed rules there win over anything below).

DATA: a read-only copy of the production SQLite database at <PATH>. Open it with `sqlite3 -readonly`. Never write to it, never open .env, never call a paid model or the internet.
Main tables: articles (the Eye's posts: site, title, published_at, tags, sentence, full_text, text_missing), tags (tag -> company / commodity / sector mapping), counts (the Counter's weekly result),
stocks, scores, readings, news_events, signals, prices, bulletins (day, english items with sources, turkish text, sources, notes, cost_usd), ai_calls (every model call: job, model, tokens, dollars), runs (every job: status, errors), alerts_sent, command_log.

GOAL: find what the data says we should improve, add, remove or stop doing. I am an independent investor running this alone; the system only suggests, the decision is mine.
Speed and simplicity first ("think fast, iterate faster"): prefer a one-line setting change over new code, and new code over a new agent.

METHOD (do it in this order; the full text is too big to read whole):
1. PROFILE with SQL only: rows per table; posts per site per day; share of text_missing; share of posts with a mapped tag; unmapped tags (top 30 by count);
   the date range; runs by job and status (every error and its text); ai_calls dollars and tokens by job and model; bulletins per day (cost_usd, the sources JSON, the number of items in `english`, `notes`, how many items carried a "rakam doğrulanamadı" warning in `turkish`).
2. THEN SAMPLE: read a stratified sample of full_text (at most 40 posts: some from each site, some text_missing, some most-mentioned, some never-cited). Do not paste whole posts into your answer.
3. THEN ANSWER the questions below. Every claim needs its evidence: the SQL you ran and the numbers it returned. If the data is too thin for a claim (state the n), say "too thin" rather than guess.

QUESTIONS
A. Reading: What fraction of the posts did any bulletin ever cite? What do the never-cited posts have in common (site, tag, length, topic, day)? Is the bulletin's "NOT USED" problem (few posts cited, most items from web search) real across the whole period, and what would fix it?
B. Themes: Which themes, sectors, companies and macro topics come up again and again in the posts but are NOT in settings.yaml `bulletin.interests`, not on a card and not in the Counter's top list? Propose additions or removals to `interests` (max 8 topics stay the rule; say which one to drop for each one added).
C. Discovery: The Counter ranks stocks by mentions. Which stocks were mentioned most in the period? How many already have a card? Is the "mentioned a lot" line (6 posts in 7 days) too high or too low for this data? Would a different line have caught something earlier? Show the table.
D. Signal check (descriptive only, no advice): for each stock the posts named, use `prices` to compute the return 1, 5 and 10 trading days after the first mention versus SPY. Report n, average, spread and the plain statement "two weeks cannot show a signal" if that is what the numbers say. The aim is a measuring method we can repeat monthly, not a conclusion.
E. Quality: Read the Eye's one-sentence summaries against their posts for 20 posts: how many are wrong, vague or not neutral? Do the same for 10 bulletin items vs their sources. Where do they fail (numbers, names, tense, opinion leaking in)? Is the cheap model good enough for the sentence step?
F. Tags and sectors: Which unmapped or "other" tags should become company, commodity or sector tags? Which subsectors are missing from the subsector list? List the exact rows to add (tag, kind, value) so I can approve them with one command each.
G. Cost and speed: Where do the dollars and the minutes go (by job)? Is anything paid for but never used (a search whose hits were never cited, a model call whose output was dropped)? What can be cut without losing what I read each morning? Current budget: 25-30 $ a month all-in.
H. Reliability: Every failed or warned run, every paywall cut, every missing figure, every false warning in the bulletin. Which are one-offs and which repeat? Which repeats should become a fix?
I. What am I NOT collecting that the data shows I should (a field, a source, a timestamp, a log line)? Fields we store but never read?
J. What would you remove? Anything in the system that two weeks of data show nobody uses.

OUTPUT (English; keep it short and plain; no invented numbers):
1. "What the data says" - 5 bullets at most, each with its number.
2. A table of at most 10 proposals, ranked by (benefit / effort): # | proposal | evidence (query + result) | type (setting / data row / small code / new feature) | effort (S/M/L) | monthly cost change | risk | how to test it in one week.
3. "Settings and rows I can apply today" - ready to paste: YAML for settings.yaml and the exact rows or commands for tags/subsectors. Nothing else.
4. "Too thin to say yet" - what to measure again in two more weeks and the SQL to rerun it.
5. A list of anything in the data that looks wrong or contradicts AGENTS.md or the roadmap.

RULES: do not edit any file, do not change the database, do not give investment advice or say buy/sell (describe, rank, measure); the Sunday chain, the bulletin and the cards stay as they are until I say which proposal to build. If a proposal would break a fixed rule in AGENTS.md, say which rule instead of proposing it.
```

## After the review

Pick proposals one at a time (AGENTS.md: one change at a time, the user decides). Settings and rows go first; code only for what the data proves. Rerun the same prompt after four more weeks and compare.
