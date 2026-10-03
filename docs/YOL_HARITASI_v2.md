---
doc: Roadmap v2
date: 2026-10-03
status: draft
publish: no
---

# Roadmap v2 — investment-agents

Names of fields, tables, grades, and folders follow `docs/GLOSSARY.md`. Section numbers are unchanged.

## 1. Purpose

Financial freedom in 10 years (at age 43). On that path the system is an **advisor**:
it reads, researches, analyzes, and suggests. **I always make the decision and place the trades.**

- Start: 500 thousand TL · Monthly: stocks 25–50 thousand TL, BES (Turkish private pension) ~9 thousand TL, gold ~5 g
- Spending: 50–75 thousand TL/month · Emergency fund: 3 months of spending
- Goal: nominal ~30 million TL / 800 thousand–1 million $ (in today's money ~10–15 million TL)
- Markets: US + Hong Kong + China A-shares (through İş Bankası) · 5–10 stocks + ETFs
- **Version 1 is US markets only** (NYSE, NASDAQ; ADRs included). Hong Kong / China A-shares are added **later**, once the system is settled.

**Why this system:** Long-term investing, not speculative trading. The agents do the work I now do by hand
(calculation, data checks, news tracking) according to rules → less time each week.

**Working principle — "Think fast, iterate faster":** Keep it simple. If version 1 of a rule is good enough,
write it, build it, run it; see the mistake, fix it. Building and fixing beats thinking so long that nothing gets built.

## 2. Fixed rules

1. Agents only **suggest**. A broker or bank password **never** enters the system.
2. Green list ≠ buy. A score is a **ranking**; every score has a required `reason` sentence next to it.
3. The card is **append-only**. Old entries are not deleted; every entry is dated. One exception: the **header** at the top shows the current state (`status`, `in_portfolio`, `lynch_type`, `grade`, `last_entry`) and only code updates it; every change is also appended as a dated note.
4. Agents do not know each other; they communicate only through files / the database.
5. Simple first: a new feature is added only after the current step counts as "done".

## 3. Four agents

| Agent | What it does | How often | Output | What it does not do |
|---|---|---|---|---|
| **1. Eye** | Reads new Emtia Defteri + Dragonomi posts in full; writes one neutral sentence with a cheap model; maps tags to stock / commodity / sector | 3 passes a day | `articles` table + `Inbox/` | Does not say positive / negative, does not comment, does not score, does not count |
| **1B. Counter** | Counts and ranks which stock / sector / commodity appeared in how many posts over the last 7 days. Code, no AI | Right before agent 2 + on request | ranked list | Does not score, does not read |
| **2. Research** | Top of the Counter list, at most 10 stocks: reads the full text, web search, score + reason; **opens the card** | Once a week (Sunday morning) | `scores` table + card (`card.md`) + `Weekly/` report | Does not do fundamental analysis, does not visit the site |
| **3. Analysis** | Builds the card from financial statements for stocks with `status = watching` (US: SEC; HK/A: uploaded PDF) + sets the grade | When a new filing arrives (see below) | `financials` table + `card.md` + grade | Does not forecast price, does not say buy/sell |
| **4. Technical** | Weekly state + market filter for the green list | Weekly | `signals` table + Telegram summary | Does not trade |

**The card is the stock card.** Each stock has one card; everything about it is there. The card **is born in agent 2**
(first entry: research — score, reason, news summaries); when I start watching it, agent 3 appends fundamental entries
to the same file. As quarters pass, new dated entries are appended at the end and the file grows.

### Flow (architecture, decision: 2026-10-03)

```text
 1. EYE (3 passes/day)    1B. COUNTER        2. RESEARCH (Sunday morning)
 Reads both sites  ──→    Last 7 days  ──→   At most 10 stocks: reads,
 articles table           counts, ranks      web search, score + reason
                                             scores table + CARD opens (candidate)
                                          │
                                          ▼
                              ┌─ ME: "XYZ'yi takibe al" ─┐
                              ▼                          │
 3. ANALYSIS (when a new filing arrives)                 │
 Only stocks with status = watching                      │
 financials table + card.md + grade                      │
 (solid / mid / weak / unclear)                          │
                                          │              │
                         grade = solid → GREEN LIST      │
                                          ▼              │
 4. TECHNICAL (weekly)                                   │
 Green list + market filter                              │
 signals table → Sunday Telegram summary ────────────────┘
                                          │
                                          ▼
                              ME: buy / sell / wait (at the broker)
```

The process is not 100% automatic; an agent does not run when there is nothing to do.

### Stock states

Each stock is one row in the `stocks` table:

| Field | Values | Who changes it |
|---|---|---|
| `status` | **candidate** (agent 2 scored it, the card was opened) · **watching** (agent 3 keeps the card) · **archived** (the card stays, no new analysis) | candidate: agent 2 · watching / archived: **only me** |
| `grade` | solid · mid · weak · unclear (from the latest card) | agent 3 |
| `in_portfolio` | yes / no | **only me** (the system is not connected to the broker and cannot know) |
| `exchange` | where the stock trades: NYSE, NASDAQ (later HKEX, SSE, SZSE) | mapping (agent 1) |
| `country` | where the company is based (e.g. Alibaba: exchange NYSE, country China → ADR) | mapping (agent 1) |

- The **green list** is not a separate status: stocks with `status = watching` and `grade = solid`. A stock that comes out solid **enters automatically**, and Telegram sends a message.
- `status` and `in_portfolio` live in the database; code updates the card header at the same time and appends a dated note (e.g. `2026-10-10 · Portföye eklendi`).
- **Archive reminder:** watching + not in the portfolio + not solid on the last 2 cards → the Sunday summary asks "arşive alalım mı?". The decision is mine.

### Agent 1 (Eye) rules (decision: 2026-10-03)

Sites: Ghost; about 100–150 posts a day in total (Emtia Defteri ~30–90, Dragonomi ~50–90), and rising.
No RSS; the **sitemap** (`/sitemap-posts.xml`) gives every post's address and time with no login.
Title, date, and tags are public; the rest of the post requires a member login.

1. **3 passes a day:** 07:00, 13:00, 20:00 (changed from `ayarlar.yaml`).
2. **Finding new posts:** from the sitemap, posts since the previous pass (one request).
3. **Reading:** with my member session (Playwright, log in once on the Air) the **full** post is read.
4. **Not straining the site / not getting blocked:** ~20–30 seconds between pages, a little different each time → a pass ~20 minutes, about 1 hour a day.
   At most ~80 pages per pass; the rest wait for the next pass. If the site says "too many requests" / "access denied", the pass **stops at once**,
   does not retry, and Telegram gets an error.
5. **One sentence:** a cheap model reads the full post and writes **one neutral** sentence: only what the news says;
   no comment, no advice, no positive / negative. Example: "An accident occurred at Rio Tinto's X mine; the article says this could tighten copper supply." Purpose: a quick first look.
6. **Saving:** only the post's plain text is taken from the page (no images / menus). Address, site, title, date, tags,
   one sentence, **full text** (no length cap — deep reads are 15,000+ characters), the `read_deep` and `text_missing`
   flags → SQLite `articles` (Air disk; ~1–2 MB / day). Only the daily list goes to Drive (`Inbox/`): title,
   one sentence, address. Each post is downloaded from the site **once**; agent 2 reads the full text from here and does not go back to the site.
7. **Tag mapping:** every tag goes through one mapping table → company (ticker + exchange, e.g. `union-pacific` → UNP,
   `rio-tinto` → RIO), **commodity** (oil, lithium, cocoa, wheat…), or sector; every row also has a **sector**
   (see "Sector list" below). A cheap model classifies a new tag once and it is saved; if it is wrong, I correct it.
8. **Not taken:** only glossary posts ("Emtia Sözlüğü", "Yatırım Sözlüğü"). Everything else is taken; agent 2 decides whether it is useful.
9. **Cost:** ~150 posts / day, cheap model → roughly 1–5 $ / month (exact figure in the implementation plan).

### Sector list (decision: 2026-10-03)

Two levels; the AI picks **only from the list** for both (if it writes freely, "Energy" / "Fossil energy" / "Oil and gas"
count as different and the count splits).

| Level | List | Does it change? |
|---|---|---|
| **Sector** | The 11 sectors of GICS, the classification used most widely: Energy · Materials · Industrials · Consumer Discretionary · Consumer Staples · Health Care · Financials · Information Technology · Communication Services · Utilities · Real Estate | Never |
| **Subsector / theme** | A list we will write together (e.g. Aviation, Semiconductors, Artificial intelligence, Lithium) | Only **with my approval** |

If none fit, the model writes `other`; the Sunday summary asks "Yeni alt sektör eklensin mi?".

### Agent 1B (Counter) rules (decision: 2026-10-03)

1. Code counts, no AI, cost zero. It runs right before agent 2; Hermes can also be asked "bu hafta en çok ne geçti?".
2. **Rolling window:** each run looks back 7 days from that day; the count does not accumulate, it starts from zero every time. The 30-day count sits beside it as information.
3. No matter how many times a stock appears in the same post, it counts as **1** (number of distinct posts). Sectors and commodities are counted separately too.
4. **Only US-listed stocks enter the scoring order** (ADRs included). Non-US stocks are counted too, but on the Sunday
   summary they appear only as an information line: "ABD dışı çok geçenler" (the data is ready when the China add-on comes).
5. **A stock that already has a card does not enter the ranking** (it is not scored again). But the Sunday summary has one line: "Kartı olup bu hafta çok
   geçenler: XYZ (12 yazı)" — I decide whether it gets scored again.

### Agent 2 (Research) rules (decision: 2026-10-03)

1. **Once a week** (Sunday morning), **at most 10 stocks** from the top of the Counter list. Reason: long-term investing;
   I keep control. If budget / quota gets tight, the number drops.
2. **It does not visit the site;** it reads the full text from `articles`. One exception: a post flagged `text_missing` is fetched from the site once more.
3. **"Actually reading":** a strong model + reading against set questions (what is said about the company, which figures are there,
   is it an event or a general comment) + a **quote from the post** for every claim. The post is flagged `read_deep`; it is not read again.
4. **Commodity → stock link, from the company to the commodity:** the first time a stock is researched, one web search: "Which
   commodities is this company tied to?" → `commodity_links` table (company, commodity, **role**: producer / user, source). Role matters: when cocoa
   gets expensive it is good for the producer and bad for the chocolate maker (user). Kept only for stocks we care about.
   Use: when a commodity's news rises, it feeds the `sector_tailwind` score of linked stocks; a commodity story that affects a stock in my portfolio
   shows up on the Sunday summary.
5. **The card is born here:** `Investing/Stocks/<TICKER> - <Company name>/card.md` is opened on Drive; the first entry is a research
   entry (score, reason, news summaries). The stock becomes **candidate**.
6. **Score:** below.

### Score rules (decision: 2026-10-03)

5 criteria × 0–2 = **10 points**. The score is a **ranking**, not a buy; each criterion has a required `reason` sentence.
Principle: **code does the arithmetic**; the AI only sets labels (with a quote), and code computes the score from the labels.
Thresholds are starting values; they are adjusted after looking at the first weeks.

| Criterion | Who / data | 0 points | 1 point | 2 points |
|---|---|---|---|---|
| **1. `mentions`** | Code · Counter (last 7 days, distinct posts) | 1–2 posts | 3–5 posts | 6+ posts |
| **2. `tone`** | An expensive model marks each post positive / negative / neutral + a quote; code: net = positive − negative | net ≤ −2 | net −1…+1 ("mixed") | net ≥ +2 |
| **3. `sector_tailwind`** | Code · Yahoo prices (free, no AI / web search) | — | one of the 2 items below | both |
| **4. `news_flow`** | Expensive model + web search; every event has a source, split into `company_specific` / `general_risk` | at least one **serious negative** event | no serious negative | no serious negative **and** at least one important positive (large contract, new product, raised outlook…) |
| **5. `quick_health`** | Code · SEC (free) | 0–2 checks passed | 3–4 passed | all 5 passed |

**3. `sector_tailwind` — 2 items (each +1):**
- The stock's **sector fund** (the US fund for each of the 11 sectors, e.g. XLE energy, XLK technology) is **above its 40-week average** today (a general rise over the last ~9 months = wind at the back).
- **A linked commodity is favorable for the company's role:** if it is a producer, the commodity price is above its 40-week average; if it is a user, below
  (an oil rise is good for a producer, bad for an airline). If there is no linked commodity / no price data: the sector fund beat the S&P 500 over the last 13 weeks.

**4. Serious-negative list (fixed):** accounting / auditor problem · bankruptcy risk / debt restructuring · a company-specific
official investigation · profit warning + cut outlook · sudden departure of the CEO / CFO.

**5. `quick_health` — purpose:** a pre-screen for "is it worth spending money on fundamental analysis?"; the deep analysis is agent 3. Thresholds are **deliberately
loose** (the old system was too tight and no stock entered the green list). 8 figures from SEC: revenue, operating profit, operating cash flow,
capex, stock comp, cash, debt (current portion + convertible included), share count.

| Check | Passes if… |
|---|---|
| Profit | latest-year operating profit > 0 |
| Cash | free cash flow (operating cash − capex − stock comp; the single definition in agent 3 rules) > 0 in at least 2 of the last 3 years |
| Shrink | revenue grew at an average annual rate > 0% over 3 years |
| Debt | net debt / free cash flow < 4 years, or cash greater than debt |
| Dilution | share count has **not risen** by more than 10% in 3 years (new shares shrink the owner's slice) |

**When data is missing — `unclear`:** a check that cannot be computed is not counted as a fail and is left out of the arithmetic ("missing data ≠ bad"). If fewer than 3 checks
could be computed, the result is **unclear → a neutral 1 point** ("neither reward nor penalty"); the card and the Sunday summary say so plainly
(e.g. "quick_health: unclear — free cash flow was not found"). At the candidate stage I am not asked for data.

**SEC data:** free, no API key (an email on the request), 10 requests per second. US companies file 10-K (annual) + 10-Q
(quarterly); ADRs mostly file only 20-F (annual) → an ADR card is updated once a year. Companies can report the same figure under different names
(IFRS names on ADRs): the code has a list of possible names for each figure; the first one found is used, and a new name
is added to the list when it shows up. The US side is ready in the old project (to be brought over).

### Agent 3 (Analysis) rules (decision: 2026-10-03; thresholds tried on 10 real companies — `BAGLAM.md` section 9)

**Approach — quality first, the shape from Lynch:**

1. **First the company's type** (Peter Lynch): `fast_grower` · `stalwart` · `slow_grower` · `cyclical` (+ `unprofitable`, below).
   `turnaround` and `asset_play` are out of scope in version 1 → `unclear`. Code sets the type from the figures, the AI checks it against the
   business description, and I can correct it.
2. **Out of scope — for now (by business model, not by GICS sector):** `bank` · `insurance` · `reit` ·
   companies with no revenue yet (`pre_revenue`, e.g. early-stage biotech) · `utility` (electricity, water, natural-gas distribution).
   Why: "think fast, iterate faster" — first the companies where the 10 measures work well; add the others later if needed.
   An out-of-scope stock is marked "unclear — out of scope: <reason>". Payment companies such as Visa / Mastercard are
   **in** scope (Visa is "Financials" in GICS but is not a bank).
3. **Code measures and raises questions; it does not judge:** e.g. "there is a loss" → "why this loss?". The AI writes the reason from the annual report
   **with a quote** (e.g. "the loss is from a new warehouse investment; gross profit is growing 30%; operating cash is positive"). Figure + reason
   sit side by side on the card; the decision is mine. (The Amazon lesson: a loss by itself is not weakness.)
4. **I do not invest in a business I do not understand:** the card's first line is a Lynch-style 2-sentence story; if I do not understand it, I do not start watching it.

**10 measures (Python computes all of them; each is computed for every company and shown on the card):**

| # | Measure | In plain words | From |
|---|---|---|---|
| 1 | `revenue_growth_3y` | by what percent a year sales are growing (3-year average annual growth) | Lynch, Fisher |
| 2 | `margin_stability` | what remains of $100 of sales after product cost; did the latest year fall below the 5-year average? **If there is no gross margin, the stability of the operating margin.** Compared only with the company's own past (companies define "cost" differently) | Smith, me |
| 3 | `operating_margin` | what remains of $100 after all operating expenses | Buffett |
| 4 | `capital_return` | how many dollars a year each $100 tied up in the business earns (Smith's definition, formula below) | Buffett, Smith |
| 5 | `cash_conversion` | how much of $100 of paper profit arrives as cash | Smith, Piotroski |
| 6 | `interest_cover` | operating profit as a multiple of interest; **not required if cash > debt** | me, Smith |
| 7 | `debt_years` | net debt ÷ free cash (3-year average). If negative: "does not produce cash from the business, and has debt" (**⚠ research item**) | Buffett |
| 8 | `share_count` | dilution or buyback | Buffett, Lynch |
| 9 | `gross_profit_growth` | is the real business growing in a company that is losing money | Lynch |
| 10 | `cash_runway` | for a company burning cash, cash on hand ÷ annual cash burn (3-year average); if debt exceeds cash, a note on the card ("part of the cash on hand is debt") | Lynch |

Formulas:
- Capital return = operating profit × (1 − tax rate) ÷ (total assets − current liabilities − cash − short-term
  investments); tax rate = tax expense ÷ pre-tax profit (between 0 and 35%; 21% if there is no profit). Equity / debt are not used
  (a company with negative equity, such as Starbucks, produced a nonsense result like 105%; the figure also does not depend on the debt number).
- If operating profit is not reported (Nike, Pfizer, Dow): **pre-tax profit + interest expense** (approximate; the card says so).
- Interest cover = operating profit ÷ interest expense.
- **Free cash = operating cash − capex − stock comp** (one definition, everywhere; Buffett: "pay is pay").
  Stock comp: SEC `ShareBasedCompensation` → `AllocatedShareBasedCompensationExpense` (94% of 1,688 companies);
  fallback: Yahoo cash-flow statement ("Stock Based Compensation"). It also appears as its own line on the card. Example: Snap's free
  cash +0.44 → −0.58 billion $ after stock comp is subtracted; at Nike, stock comp is 33% of free cash. (The 10-company trial was run before this
  definition; the prototype will be updated.)
- **7 and 10 use the same base:** average free cash flow of the last 3 years (so a one-off payment does not wreck a single year).
- **Share count:** adjusted for splits — a jump of 2, 3, 4, 5, 10… times in the SEC figure + a **check against Yahoo's split
  history**; if they disagree, a flag, and the measure is `not_computed`. The IPO year is skipped (the first year's figure misleads).
- **If gross profit has just turned from a loss to a profit,** growth cannot be computed → ➖ "just turned from a loss to a profit".

**Thresholds (starting values; adjusted with the trial set + the acceptance test):**

| # | Measure | ✅ | ➖ | ❌ |
|---|---|---|---|---|
| 1 | Revenue growth (3-year average) | ≥ 15% | 8–15% | < 8% |
| 2 | Margin stability (latest year − 5-year average) | drop ≤ 1 percentage point | drop of 1–3 percentage points | drop > 3 percentage points |
| 3 | Operating margin | ≥ 15% | 5–15% | < 5% |
| 4 | Capital return (5-year average) | ≥ 15% | 8–15% | < 8% |
| 5 | Cash conversion (3-year average) | ≥ 80% | 50–80% | < 50% (not computed if net profit ≤ 0) |
| 6 | Interest cover | ≥ 8 times or cash > debt | 3–8 times | < 3 times |
| 7 | Pays down debt | ≤ 3 years or cash > debt | 3–5 years | > 5 years, or does not produce cash from the business and has debt |
| 8 | Share count (5 years) | down / flat | +0–10% | > +10% |
| 9 | Gross-profit growth (3-year average) | ≥ 20% | 10–20% | < 10% |
| 10 | Cash runway | ≥ 3 years or the business produces cash | 1.5–3 years | < 1.5 years |
| 10* | **The same — a fast grower that does not produce cash from the business** (Rivian type) | ≥ 5 years | 3–5 years | **< 3 years** |
| T | Dividend covered by cash (5-year total) | free cash ≥ dividends paid | — | not covered |

**Debt (one judgment in the grade, 6 + 7 together)** — "debt is fine if it is used well": the interest-cover mark is the base; if the
paydown time is ❌, it drops one step (✅ → ➖, ➖ → ❌). If interest cannot be found, use measure 7's mark.

**Type rules** (in order):

| Type | Rule |
|---|---|
| `cyclical` | sector is Energy / Materials **or** the last 5 years include both profitable years and loss years |
| `fast_grower` | revenue 3-year average ≥ 15% |
| `stalwart` | 5–15% **and** operating profit in at least 4 of the last 5 years |
| `unprofitable` | growing slower than 15% and no profit in 4 of the last 5 years (like Snap; Lynch would not call this a stalwart) |
| `slow_grower` | < 5% |

**Decisive measures (by type; in football, a striker is judged on goals and a goalkeeper on saves):**

| Type | Decisive measures |
|---|---|
| `stalwart` | 2 margin stability · 3 operating margin · 4 capital return · 5 cash conversion |
| `fast_grower` | 1 revenue growth · 9 gross-profit growth · 2 margin stability · 10 cash runway · 8 share count |
| `slow_grower` | 2 margin stability · 4 capital return · 5 cash conversion · debt · T dividend |
| `cyclical` | 4 capital return (5-year average) · debt · 8 share count |
| `unprofitable` | same as stalwart (2, 3, 4, 5) |

All 10 measures are computed for every company and shown on the card; if a measure that is not decisive gets ❌, the AI is asked "why?"
(the answer goes on the card) and the grade does not change.

**Grade rule:**

```text
solid    = none of the decisive measures is ❌  AND  at least half are ✅
weak     = 2 or more of the decisive measures are ❌
mid      = everything in between
unclear  = more than half of the decisive measures could not be computed, or out of scope
shrink   = if the 3-year average revenue growth is negative, the grade cannot be solid (mid at best); shrink_rule: yes
```

**Price does not enter the grade; it is a separate line on the card** (quality first; green list ≠ buy): PEG ≤ 1 attractive · 1–2 fair · > 2 expensive ·
Lynch dividend ratio (for dividend payers) ≥ 2 attractive · 1–2 fair · < 1 expensive · free-cash-flow yield ≥ 5% attractive ·
2–5% fair · < 2% expensive. If there is no profit / profit is falling, PEG is `not_computed`; the cash yield still works.

**SEC data — synonym method:**

- **Code** pulls the figures; the AI does not invent figures. One request brings the company's whole history (annual 10-K; US companies also have quarterly
  10-Q, ADRs do not).
- Names are not free-form: they are chosen from the SEC's official dictionary; companies' custom names do not arrive in this service.
- Each figure has a **synonym list** (by figure, not by company). For **each year separately**, code tries the list in order and
  takes the first one found → a company that renames a tag is caught on its own (Coca-Cola: 2023 `LongTermDebt`, 2024
  `LongTermDebtAndCapitalLeaseObligations`).
- Debt = the sum of the pieces (long-term + current portion + short-term + convertible); the pieces can overlap → **⚠ research item,
  must be checked by hand in the acceptance test.** Flags: debt suddenly drops to zero from one year to the next · debt is larger than total liabilities.
- **Consistency checks:** gross profit = revenue − cost · margin 0–100% · a sudden drop to zero / a 10-times jump → flagged, not used.
- **Trace:** the card records which name and which filing each figure came from.
- **Ledger:** a figure that cannot be found becomes `not_computed` and is written to the SQLite `missing_data` table (date, ticker, year,
  figure, names tried, status: `open` / `tag_added` / `absent`). One line on the Sunday summary; Hermes can be asked.
  The synonym list is filled each week from this ledger.
- **Coverage (2026-10-03, 1,688 US companies, assets ≥ 1 billion $, reporting operating profit):** revenue 98% · operating cash 98% ·
  share count 96% · interest expense 90% · capex 87% · debt (at least one piece) 85% · gross profit 67% (most of the gaps
  are not a missing name; the company never reports the figure — like Visa).

**Tests:** the trial set also includes **trap examples** (a fast grower that loses money on purpose → must not come out weak; high margin but
shrinking → must not come out solid; high debt but used well). **Acceptance test (UAT) at least 20 stocks**, figures compared by hand with the 10-K;
approval comes after that.

**Valuation (2 measures):**
- Lynch's **PEG** ratio: P/E ÷ annual earnings growth (%); ≈ 1 fair, < 1 attractive, > 2 expensive. **Growth is capped at 25%**
  (Lynch: faster than that does not last; Nvidia's uncapped PEG came out 0.15). Growth comes from past figures; **analyst estimates
  are not used.** There is no numerical floor (Lynch has none either); if earnings growth ≤ 0, PEG cannot be computed.
- **Lynch's dividend-adjusted ratio** (also, for companies that pay a dividend): (earnings growth % + dividend yield %) ÷ P/E;
  Lynch: < 1 weak, 1.5 is all right, ≥ 2 is what you want. It corrects PEG's unfairness to a slow grower that pays a dividend (such as Coca-Cola).
  (The same idea is used today under the name "PEGY", flipped: P/E ÷ (growth + yield).)
- **Free-cash-flow yield:** free cash flow ÷ market value ("if I bought the whole company today, what percent of my money comes back
  as cash per year?"). Free cash = operating cash − capex − stock comp (the single definition above; SEC); market value = price (Yahoo) × share
  count (SEC). The card also shows the 5-year path of free cash flow.

**Not in version 1 (maybe later):** a "company's real value vs market value" calculation and **hidden
assets** in the footnotes of annual reports (e.g. land booked at an old price). Lynch counts this as a separate type (`asset_play`) — that type is out of
scope in version 1. Buffett, after his early years, looks at the cash the business will produce, not at assets. Reading footnotes and valuing them
is hard and error-prone for an AI; it would make version 1 harder.

**Card format (decision: 2026-10-03; so an LLM and the code can read it easily):**

- Header: `ticker`, `company`, `exchange`, `country`, `sector`, `subsector`, `status`, `in_portfolio`, `lynch_type`, `grade`,
  `last_entry` (code updates these 5: `status`, `in_portfolio`, `lynch_type`, `grade`, `last_entry`), `opened` (first entry, never changes), `publish`.
- First line: a Lynch-style 2-sentence **story** (what it sells, where the money comes from).
- Every entry uses the same heading pattern: `## <date> · <record> · <who> [· <source>]` — records: `research` (agent 2),
  `fundamental` (agent 3), `note` (user; e.g. closing a warning). Entries are append-only.
- **Figures live only in the YAML data block inside the entry** (one source): ratios as `0.48` (no percent sign), marks
  as words (`good` / `mid` / `weak`), each measure has `decisive` and the source XBRL name; also `source` (report, period end,
  url, as-of date), `lynch_type`, `grade`, `price`, `warnings` (code, name, kind: `company_specific` / `general_risk`, status, quote,
  source page), `gaps`.
- Prose sits outside the blocks, under fixed subheadings: `### Summary` · `### Thesis` ·
  `### What changed`.
- `### Thesis` always has two parts: why it is owned (at most 3 points) and 3 things that would break the thesis. The heading stays short so code can find `### Thesis`.
- Closing a warning: a user note entry (`## 2026-11-06 · note · user` → "U1 kapatıldı, çünkü …"); the agent reads it on the next
  run and does not reopen it unless the condition has changed.
- Sample skeleton: `BAGLAM.md` section 7 (the current skeleton).

**Open (agent 3):** who writes the first thesis (proposal: the AI drafts 3 points, I correct and approve) · external-review results
(two models, waiting) · an AI auditor (last decision).

### Rules that prevent spending

1. Agent 3 runs on an **event**, not a calendar: once a week it asks SEC "is there a new 10-Q / 10-K?" (free); if not, it does nothing. HK / A: when I put a new PDF in the `filings/` folder.
2. An archived stock is never analyzed.
3. Every agent writes a row to the `runs` table on every run (start, end, `ok` / `error`, dollars spent).

### Telegram and Hermes (one counterpart)

On Telegram my only counterpart is **Hermes**; I do not talk to the 4 agents separately. Hermes runs the agents and reads the results.

- **When a message arrives:** one summary on Sunday (new candidates, what changed on cards, stocks that already have a card and were mentioned a lot this week, non-US names mentioned a lot, data still `unclear`, new subsector proposals, technical state) · **immediately:** if the grade of a stock in my portfolio drops · **immediately:** if an agent errors · a stock that comes out solid and enters the green list. Agent 1's daily output does not go to Telegram, only to `Inbox/`.
- **What it can do:** answer questions (it reads the database + the cards: "XYZ'nin karnesi ne diyor?", "bu ay ne harcadık?") and run a command from the **defined command list** ("XYZ'yi takibe al", "ABC'yi portföye ekledim", "XYZ'yi şimdi analiz et", "XYZ'deki U1 uyarısını kapat, çünkü …"). The command list is written in the implementation plan.
- **Asking for missing data (decision: 2026-10-03):** if agent 3 cannot find a figure (one that landed in the ledger), it asks me —
  **when I say "XYZ'yi analiz et"** and **on Sunday** during the analyses (that run's gaps in one message).
  The message is not a cryptic one-liner; it is **plain and clear**; code fills the template, a cheap model simplifies it:
  which stock · which figure · which year · why it is needed (which measure cannot be computed) · where to find it (e.g. "10-K → cash
  flow statement → 'Stock-based compensation' line") · how to answer (e.g. `XYZ 2025 borç 12,3 milyar`). Code checks the figure I enter
  (on an inconsistency such as a 10-times gap versus other years, "emin misin?"), and the card records `source: user`;
  if no answer comes, the figure stays `unclear` and is reminded once.
- **What it does not do:** it does not freely change the database / files (only the command list) · it does not change code or rules (that work is on the development Mac) · it does not trade.
- Chat with Hermes uses the Codex subscription: no extra fee, but a lot of chat can fill the quota.
- In step 0 (setup) this way of working is tried and confirmed.

## 4. Technology decisions

| Topic | Decision |
|---|---|
| Language | Python (one language) |
| Development | On the main Mac (Claude Code / Cursor); each agent is tried by hand here first. Bridge: GitHub |
| What runs it | Hermes Agent, on the backup MacBook Air M2 (16 GB), 24/7. No code is written on the Air: it is updated with `git pull`; `.env`, the site session, and the real SQLite live there. Hermes only schedules and reports; the calculation / analysis logic is in our code |
| Communication | One counterpart on Telegram, Hermes (section 3, "Telegram and Hermes") + Drive folders |
| AI | Expensive work (writing the card): Codex subscription (1 subscription is set aside for the agent). Cheap work + web search: OpenRouter, with a spend limit. The Claude subscription is **not** connected to Hermes (terms of use) |
| Site reading | Playwright; I log in once, the session is stored; 3 passes a day, slow (section 3, "Agent 1 rules"). No AI in the page-download step; a cheap model only for the one sentence on the post that was read. **Permission:** the owner of both sites personally allowed reading (scraping) (2026-10-03); no API; condition: do not strain the site / do not abuse it |
| Model choice | One place: `ayarlar.yaml` |
| Independence | The code does not know Hermes; each agent also runs by hand (`python -m agents.analysis`) |
| Blog possibility | Every report/card is Markdown + a header (`publish: yes/no`). No web interface for now |

## 5. Storage

| Place | What | Who reads it |
|---|---|---|
| **Drive** (`Investing/`) | PDFs, `card.md`, sector/stock reports, weekly summaries | Me |
| **SQLite** (Mac disk, **not** on Drive) | Figures, scores, prices, signals, lists, run records | The machine |

Every night a **backup copy** of SQLite is sent to Drive.

Tables: `stocks`, `articles` (full text included), `tags` (mapping: kind, maps_to, exchange, country, sector, subsector), `commodity_links`, `scores`, `missing_data` (the ledger), `financials`, `prices`, `signals`, `runs` (dollars spent included).

```text
Investing/                                 (Drive)
├── Inbox/                                 agent 1's daily list (title + one sentence + address)
├── Weekly/                                weekly summaries
├── Backup/                                nightly SQLite copy
└── Stocks/<TICKER> - <Company name>/      flat; sector is in the card header
    ├── card.md                            born in agent 2
    └── filings/                           HK / A-share PDFs (I upload them by hand)

investment-agents/                         (code, Git)
├── agents/eye/  counter/  research/  analysis/  technical/
├── shared/                                AI, SEC, price, Drive paths, database
├── ayarlar.yaml
└── docs/  YOL_HARITASI_v2.md  BAGLAM.md  GLOSSARY.md  TASINANLAR.md
```

Today's folders are still `ajanlar/` and `ortak/` (the prototype and the backtest). New code uses the names in the tree above.

## 6. Budget

- AI / API: **at most 25–30 $ / month** (expected: OpenRouter < 5 $ — of which 1–5 $ is agent 1's one-sentence summaries — + the existing Codex subscription)
- Emtia Defteri + Dragonomi subscriptions are **outside** this budget
- A fixed monthly limit on OpenRouter; the `runs` table answers "bu ay ne harcadık?" from Telegram

## 7. To bring from the old project (investment-intelligence, `v1-arsiv`)

No bulk copy; when needed, with a line in `TASINANLAR.md`:

- SEC client + companyfacts mapping (including the convertible-debt fix)
- Price fetch (Yahoo / Stooq)
- Emtia Defteri data format
- Backtest scripts (5-8-13 daily / weekly)

Not brought: the 9-stage gate system, the final FA color logic, the handoff documents.

## 8. Steps

| Step | Work | Counts as done if… |
|---|---|---|
| **0. Setup** | Mac settings (sleep off, separate user, FileVault), Hermes, Codex login, OpenRouter limit, Drive on the desktop, Telegram bot | I can exchange messages on Telegram and a scheduled trial job writes a file to Drive |
| **1. Analysis + card** | `shared/` + SQLite + agent 3, 3–5 US stocks | **Acceptance test of at least 20 stocks, figures compared by hand with the 10-K;** 3 stocks have a card on Drive; a second run appends a new dated entry without deleting the old one; **the trial-set test passes:** 3–5 companies everyone accepts as quality come out solid, 1–2 companies known to be weak do **not** come out solid, trap examples are classified correctly (in the old system no stock could enter the green list; if the quality names do not come out solid the rules are too tight, if the weak names come out solid the rules are too loose) |
| **2. Eye** | Both sites with Playwright, 3 passes a day | For 1 week every pass fills `articles` (one sentence + full text + mapped tags) and the site never once answers "too many requests" / a block |
| **3. Research** | 1B Counter + agent 2: reading + web search + score + reason + opening the card | The weekly report is on Drive and on Telegram; cards for candidate stocks open on Drive |
| **4. Technical** | Weekly state + market filter | A green-list summary arrives on Telegram on Sunday |

## 9. Open topics (decided together before coding)

**Decision order (2026-10-03):** all decisions and plans first, then code.

1. ~~Overall frame~~ ✅ (2026-10-03: card = the stock card, working principle, site permission, development / runtime split)
2. ~~Architecture~~ ✅ (2026-10-03: section 3 — flow, stock states, in_portfolio, event-driven runs, Telegram / Hermes)
3. ~~Agent 1 (Eye)~~ ✅ (2026-10-03: section 3, "Agent 1 rules")
4. ~~Agent 2~~ ✅ (2026-10-03: Counter, sector list, reading, commodity link, birth of the card, score rules — section 3)
5. **Agent 3** — ✅ mostly (2026-10-03: Lynch types, scope, 10 measures + thresholds, grade rule, valuation + PEG cap + Lynch dividend ratio, stock comp, card format, asking for missing data — section 3). **Left:** who writes the first thesis, external-review results, auditor (last)
6. **Agent 4** — technical rules
7. **Implementation plan** — model / budget split, Air setup, coding order

Topic notes:

- ~~**Agent 2 score rules.**~~ ✅ section 3, "Score rules".
- **Card format.** Which metrics, which checks, how the "reason" section is written. Fundamental-analysis result in 3 classes: **solid / mid / weak**; only solid ones go to technical analysis (the green list). **To be discussed with agent 3:** if data is missing, Hermes asks me for it on Telegram (I find it and provide it, the agent continues the calculation) — control stays with me, the work stays with the agent.
- **Agent 4 rules.** Backtest result: daily 5-8-13 lagged buy-and-hold in 24 of 24 stocks. Current proposal: green list + market filter (SPY above its 40-week average); exit = the stock drops off the green list.
- ~~**Site terms of use.**~~ ✅ The site owner gave permission (see section 4, Site reading).
- **HK / A-share data** (⏸ deferred — version 1 is US only). Which figures will be taken from the PDF by hand / by AI. Note: US filings do not need PDF / OCR (SEC figures are a ready table). Most HK / A PDFs contain text → read with a free Python library; OCR only for a scanned (image) PDF, and that too is free on the computer.
