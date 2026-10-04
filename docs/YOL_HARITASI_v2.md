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
| **4. Portfolio** | My money, not companies: ledger, value and weights, benchmark against SPY and gold, total wealth against the goal, where the new money could go, drop alert, valuation info (section 3, "Agent 4 rules") | Weekly (Sunday) | `holdings`, `prices`, `signals`, `other_assets`, `snapshots` + the portfolio block of the Sunday summary | Does not trade; gives **no** sell signal; uses no AI |

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
 4. PORTFOLIO (weekly)                                   │
 Green list + my holdings + SPY / gold shadows           │
 new money, alerts, total wealth → Sunday summary ───────┘
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

**4. Serious-negative list (fixed; each such event is checked by the AI auditor — "AI auditor" below):** accounting / auditor problem · bankruptcy risk / debt restructuring · a company-specific
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

### Agent 3 (Analysis) rules (decision: 2026-10-03; tried on 10 real companies and checked by 2 external reviews — `BAGLAM.md` section 9, `docs/reviews/`)

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
5. **The AI writes the first thesis** (why it is owned, at most 3 points + 3 things that would break it). Later entries do not rewrite it;
   they only check whether it still holds. I can correct it with a `note` entry.
6. **Filings read:** 10-K (US companies) and 20-F (foreign companies / ADRs), in both the `us-gaap` and the `ifrs-full` taxonomy;
   each taxonomy has its own synonym lists. 20-F filers are annual only. Measures are ratios, so the reporting currency does not
   matter; only the price line converts currency (Yahoo FX rate, free).

**10 measures (Python computes all of them; each is computed for every company and shown on the card):**

| # | Measure | In plain words | From |
|---|---|---|---|
| 1 | `revenue_growth_3y` | by what percent a year sales are growing (3-year average annual growth) | Lynch, Fisher |
| 2 | `margin_stability` | what remains of $100 of sales after product cost; did the latest year fall — against the previous 4 years and against last year? **If there is no gross margin, the stability of the operating margin.** Compared only with the company's own past (companies define "cost" differently) | Smith, me |
| 3 | `operating_margin` | what remains of $100 after all operating expenses | Buffett |
| 4 | `capital_return` | how many dollars a year each $100 tied up in the business earns (Smith's definition, formula below) | Buffett, Smith |
| 5 | `cash_conversion` | how much of $100 of paper profit arrives as cash | Smith, Piotroski |
| 6 | `interest_cover` | operating profit as a multiple of interest; **not required if cash > debt** | me, Smith |
| 7 | `debt_years` | net debt ÷ free cash (3-year average). If negative: "does not produce cash from the business, and has debt" (**⚠ research item**) | Buffett |
| 8 | `share_count` | dilution or buyback | Buffett, Lynch |
| 9 | `gross_profit_growth` | is the real business growing in a company that is losing money | Lynch |
| 10 | `cash_runway` | for a company burning cash, cash on hand ÷ annual cash burn (3-year average); if debt exceeds cash, a note on the card ("part of the cash on hand is debt") | Lynch |

Formulas:
- **Missing is not zero** (both external reviews): a figure that is not found stays `not_computed` and goes to the ledger;
  zero is used only when the filing really says zero. This applies to capex, free cash, liquid assets, dividends, net profit and the
  price line. A multi-year average uses the years that exist; with fewer than 2 years it is `not_computed`.
- **Liquid assets = cash + short-term investments + current marketable securities** — the parts are **added**, not tried as
  alternatives. Short-term investments: `ShortTermInvestments` · `OtherShortTermInvestments`; marketable securities:
  `MarketableSecuritiesCurrent`; a partial tag (`AvailableForSaleSecuritiesDebtSecuritiesCurrent`, …) only if nothing else is found.
  (The trial missed these at Coca-Cola, Nvidia, Nike and Pfizer; Nvidia uses a company-only tag that SEC's standard data never shows
  → `not_computed` + ledger + a Telegram request.)
- Capital return (per year) = operating profit × (1 − tax rate) ÷ (total assets − current liabilities − liquid assets);
  tax rate = tax expense ÷ pre-tax profit (between 0 and 35%; 21% if there is no profit). Equity / debt are not used
  (a company with negative equity, such as Starbucks, produced a nonsense result like 105%; the figure also does not depend on the debt number).
  **The grade uses the worse of the 3-year and the 5-year average** — Smith's test is a *sustained* high return; a 5-year average
  can carry old good years (Pfizer: 5-year 12% ➖, last 3 years 5% ❌). **Exception: `cyclical` uses the 5-year average only**
  (on purpose: the bottom of the cycle must not punish it alone).
- If operating profit is not reported (Nike, Pfizer, Dow): **pre-tax profit − net interest income** (a net-interest tag such as
  `InterestIncomeExpenseNonoperatingNet`; Nike: 3.900 − 0.050 = 3.850, the same as Nike's own figure). With no net tag, net interest
  income = interest income (`InvestmentIncomeInterest` · `InterestIncomeOther`) − interest expense — both accrual figures, never
  cash interest (Pfizer, Dow). If neither works → `not_computed`. The card says it is approximate.
- Interest cover = operating profit ÷ interest expense. **Cash interest paid (`InterestPaidNet`) is never used in 3, 4, 6 or the
  fallback**; it may appear only as an info line.
- Net profit synonyms: `NetIncomeLoss` · `NetIncomeLossAvailableToCommonStockholdersBasic` · `ProfitLoss`.
- Fiscal-year ends less than 10 days apart are the same year (52/53-week years).
- **Free cash = operating cash − capex − stock comp** (one definition, everywhere; Buffett: "pay is pay").
  Stock comp: SEC `ShareBasedCompensation` → `AllocatedShareBasedCompensationExpense` (94% of 1,688 companies);
  fallback: Yahoo cash-flow statement ("Stock Based Compensation"). It also appears as its own line on the card. Example: Snap's free
  cash +0.44 → −0.58 billion $ after stock comp is subtracted; at Nike, stock comp is 33% of free cash. (The 10-company trial was run before this
  definition; the prototype will be updated.)
- **7 and 10 use the same base:** average free cash flow of the last 3 years (so a one-off payment does not wreck a single year).
- **Share count:** adjusted for splits — a jump of 2, 3, 4, 5, 10… times **or the reverse (1/2, 1/10 …, reverse split)** in the SEC
  figure, adjusted **only if Yahoo's split history confirms it** (only whole-number ratios count; Yahoo also lists spin-offs such
  as Pfizer's "×1.054"). Unconfirmed → no adjustment, a flag ("possible merger"), and the measure is `not_computed`. SEC's later
  filings may already be restated (Nvidia ×4 in 2021). The IPO year is skipped (the first year's figure misleads).
- **Margin stability = the worse of** (latest − average of the **previous 4** years) and (latest − previous year), in percentage points.
  Years with a margin beyond ±100% or revenue below 10% of the latest year are left out (Rivian's early years gave a meaningless
  +223 points); fewer than 3 years left → `not_computed`.
- **Gross-profit growth:** just turned from a loss to a profit → ➖ "just turned from a loss to a profit"; a loss both 3 years ago
  and now → ❌.
- **Profit years** (for the type rules): the sign of operating profit; if it is missing, the sign of pre-tax profit (sign only, not the
  amount); if both are missing the year is not counted; fewer than 3 years with data → type `unclear`.

**Thresholds (starting values; adjusted with the trial set + the acceptance test):**

| # | Measure | ✅ | ➖ | ❌ |
|---|---|---|---|---|
| 1 | Revenue growth (3-year average) | ≥ 15% | 8–15% | < 8% |
| 2 | Margin stability (the worse of: latest − previous 4-year average, latest − previous year) | drop ≤ 1 percentage point | drop of 1–3 percentage points | drop > 3 percentage points |
| 3 | Operating margin | ≥ 15% | 5–15% | < 5% |
| 4 | Capital return (worse of 3-year and 5-year average; `cyclical`: 5-year) | ≥ 15% | 8–15% | < 8% |
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

**Type rules** (in order; the first that matches wins):

| # | Type | Rule |
|---|---|---|
| 1 | `cyclical` | sector Energy / Materials, **or** a cyclical industry by the SEC SIC code: semiconductors, autos, airlines, shipping, homebuilding, chemicals, steel, mining (Lynch's biggest trap: a cyclical at its peak looks like a fast grower) — **the sector / SIC test applies only if the company made a profit in at least 1 of the last 5 years** (no profit, nothing to cycle: Rivian has an auto SIC code but is `unprofitable`; can be revised later) — **or** the last 5 years include both profit years and loss years |
| 2 | `unprofitable` | profit in fewer than 4 of the last 5 years **and** it burns cash (3-year average free cash < 0) — the Rivian type |
| 3 | `fast_grower` | revenue 3-year average ≥ 15% (a loss-maker that produces cash stays here — the Amazon type) |
| 4 | `unprofitable` | profit in fewer than 4 of the last 5 years (produces cash but grows slower; like Snap — Lynch would not call this a stalwart) |
| 5 | `stalwart` | 5–15% |
| 6 | `slow_grower` | < 5% |

Because rule 1 catches mixed profit / loss years, `unprofitable` in practice means "a loss in every year". Known limit: a company that
was a loss-maker and then turned profitable (e.g. Uber) gets `cyclical`.

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
fast_grower safety = if operating margin is ❌ and it burns cash (3-year average free cash < 0), the grade cannot be solid (mid at best)
```

**Flags (they never change the grade; each one sends a "why?" question to the AI, answered with a quote on the card):**
one-off (operating cash fell more than 30% over 2 years while net profit rose — e.g. Coca-Cola's 12 billion $ tax deposit and
fairlife payment; or a gain on a sale explains most of operating profit — e.g. Boeing's 9.6 billion $ in 2025) · free cash negative
in the latest year and falling for 3 years (Dow) · data check over the last 3 years: liquid assets **fell** more than 50% in a year
(a rise is normal in growing companies; Nvidia's 43.2 → 10.6 caught its company-only tag) or debt changed more than 30% ·
**borderline** (within 10% of a threshold, including dividend cover; shown, no grade change) · lease-heavy (info line: debt including leases; not in the grade —
both reviews: a rough lease adjustment counts rent twice) · acquisitive (info line: money spent on acquisitions; free cash does not
include it).

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
  must be checked by hand in the acceptance test.** The group `LongTermDebtNoncurrent` + current portion (`LongTermDebtCurrent` /
  `DebtCurrent`) is tried **before** `LongTermDebt` (Pfizer 2020: `LongTermDebt` held a single 4 billion $ item, the true total was
  ~40 billion $). **A group counts only if all of its parts are found** (convertible group: any part) — the prototype once took
  Boeing's current part alone (8.5 instead of 53.9 billion $). Short-term borrowings are added only when the group does not
  already include them, and only one of `ShortTermBorrowings` / `CommercialPaper` (the first often includes the second). Code builds
  every candidate total; if they disagree, a flag. Flags: debt suddenly drops to zero from one year to the
  next · debt is larger than total liabilities · debt changed more than 30% in a year. Debt of a business held for sale and
  leases: info lines only.
- **Consistency checks:** gross profit = revenue − cost · margin 0–100% · a sudden drop to zero / a 10-times jump → flagged, not used.
- **Trace:** the card records which name and which filing each figure came from.
- **Ledger:** a figure that cannot be found becomes `not_computed` and is written to the SQLite `missing_data` table (date, ticker, year,
  figure, names tried, status: `open` / `tag_added` / `absent`). One line on the Sunday summary; Hermes can be asked.
  The synonym list is filled each week from this ledger.
- **Coverage (2026-10-03, 1,688 US companies, assets ≥ 1 billion $, reporting operating profit):** revenue 98% · operating cash 98% ·
  share count 96% · interest expense 90% · capex 87% · debt (at least one piece) 85% · gross profit 67% (most of the gaps
  are not a missing name; the company never reports the figure — like Visa).

**Tests:** the trial set also includes **trap examples** (a fast grower that loses money on purpose → must not come out weak; high margin but
shrinking → must not come out solid; high debt but used well; a cyclical at its peak; a reverse split; an acquisitive company).
**Golden set:** the 10 trial companies with their expected grades (`BAGLAM.md` section 9); after every rule change code reruns them and
reports which grade changed. **Acceptance test (UAT) at least 20 stocks**, figures compared by hand with the 10-K / 20-F — always
liquid assets and total debt against the balance-sheet lines; flagged rows first; the export includes the tag used, the raw fact, tax
and the parts of liquid assets and debt. Approval comes after that.

**Valuation (2 measures):**
- Lynch's **PEG** ratio: P/E ÷ annual earnings growth (%); ≈ 1 fair, < 1 attractive, > 2 expensive. **Growth is capped at 25%**
  (Lynch: faster than that does not last; Nvidia's uncapped PEG came out 0.15). Growth comes from past figures; **analyst estimates
  are not used.** There is no numerical floor (Lynch has none either); if earnings growth ≤ 0, PEG cannot be computed.
- **Lynch's dividend-adjusted ratio** (also, for companies that pay a dividend): (earnings growth % + dividend yield %) ÷ P/E;
  Lynch: < 1 weak, 1.5 is all right, ≥ 2 is what you want. It corrects PEG's unfairness to a slow grower that pays a dividend (such as Coca-Cola).
  (The same idea is used today under the name "PEGY", flipped: P/E ÷ (growth + yield).)
- **Free-cash-flow yield:** free cash flow ÷ market value ("if I bought the whole company today, what percent of my money comes back
  as cash per year?"). Free cash = operating cash − capex − stock comp (the single definition above; SEC); **the main value uses
  the 3-year average free cash**, the latest year is shown next to it (Coca-Cola: latest 1.4%, 3-year 1.7%). Market value = price
  (Yahoo) × share count (SEC). The card also shows the 5-year path of free cash flow.
- **PEG growth = diluted earnings per share, 3-year growth** (split-adjusted; P/E is a per-share ratio, so growth is per share too —
  Lynch also worked per share), capped at 25%.
- **P/E and dividend yield are computed from SEC figures:** P/E = market value ÷ (latest net profit × FX); dividend yield = latest
  dividends paid × FX ÷ market value. From Yahoo only price, market value (USD), split history and FX (Yahoo mixed currencies on
  the ADR: Novo Nordisk's dividend yield showed 31%). Split confirmation uses only splits inside the years being looked at.

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

**Quarterly updates — last 4 quarters (decision: 2026-10-04):** agent 3 reads every 10-Q as well as the 10-K. A single quarter is
noisy (seasons, one-offs), so at each new filing the measures are recomputed on the **last 4 quarters summed** (a rolling year,
"TTM"); balance-sheet figures come from the latest quarter. Multi-year averages keep the annual history, with the last 4 quarters as
the current year. SEC gives no separate Q4 and reports cash flow cumulatively (Q4 = year − 9 months; quarters by subtraction) — code
handles it. 20-F filers (ADRs) stay annual.

**When to consider selling (decision: 2026-10-04)** — never because the price fell; because the reason to own it is gone (Fisher:
"if you bought the right stock, the time to sell is almost never"). Every item is a "consider selling" alert; **the decision is mine.**

| # | Trigger | When | Who notices |
|---|---|---|---|
| 1 | The thesis broke (one of the card's "3 things that would break the thesis" happened) | any quarter → Telegram at once | agent 3 |
| 2 | Grade fell to `weak` | any quarter → Telegram at once | agent 3 |
| 3 | Grade `mid` for 2 quarters in a row (after `solid`) | 2 quarters | agent 3 |
| 4 | I realize I was wrong (I did not understand the business) | — | me |

**Sell suggestions come only from agent 3** (decision: 2026-10-04). Agent 4 never says "sell" — not on price, not on valuation, not
on the market filter.

**My rule for a crash:** *"I do not sell because the market fell. I consider selling only when agent 3's triggers break."* (In a
2008-like crash the portfolio can show about −45% on paper; selling at the bottom in panic would cost more than any filter saves.
The emergency fund and the gold exist so that I never have to sell stocks on a bad day.)

**Every sell suggestion comes with its evidence:** which measure or thesis point broke, from which filing, and the figures. If the
stock has an open `data_check` flag, the message says first: "check the figure before acting" (a wrongly read figure can produce a
wrong `weak`).

A single bad quarter is **not** a sell trigger; it is a "check now": the card is updated and the AI answers "why?" with a quote.

**Prototype and golden set (2026-10-03):** `ajanlar/analiz/prototip/` follows these rules; `altin_set.py` reruns the 10 companies —
10/10 as expected: `solid` Nvidia · `mid` Coca-Cola (borderline), Nike, Starbucks · `weak` Pfizer, Intel, Boeing, Snap, Dow, Rivian.
IFRS / 20-F works (Novo Nordisk). Details: `BAGLAM.md` section 9.

**Open (agent 3):** a third external review is still running. (The AI auditor is decided — below, "AI auditor".)

### Agent 4 (Portfolio) rules (decision: 2026-10-04; renamed from "Technical" the same day)

**Why the role changed:** the backtests (`BAGLAM.md` section 3) show that buying and selling single stocks on technical signals
loses. Daily 5-8-13 lagged buy-and-hold in 24 of 24 stocks; a market filter with short averages loses money; a stock's own trend
exit sells quality companies on every dip and buys them back late. The way to get **more shares** is not to sell and buy back,
but to **send the new monthly money to a quality stock while it is down**. So agent 4 is not a trading signal. It is the only
agent that looks at **my money**, not at companies: what I bought, what it is worth, whether my picks beat SPY and gold, how far
total wealth is from the goal, and where the new money could go. It runs weekly (Sunday), with the Friday close and the last 4
quarters' figures.

**Code only, no AI.** Every figure is arithmetic; the only data is free Yahoo data. The AI around it is decided elsewhere: Hermes
turns my message into a command (section 10.2), and agent 3 answers the drop-alert check (rule 6).

**All figures in USD.** Nothing is converted to TL (the lira's fall would look like a gain). The only conversion is the BES
balance: TL → USD at that week's rate.

1. **Ledger (`holdings`):** one row per event, append-only — `buy` and `sell` from my commands (`/bought`, `/sold`); `dividend`
   and `split` added by code. Positions (quantity, average cost) are computed from the rows. The ledger starts empty (on
   2026-10-04 I hold no stocks).
   - **Dividends:** Yahoo's dividend history × the quantity I held on the ex-date × (1 − withholding). Withholding is one setting
     in `ayarlar.yaml` (20%, user-confirmed; checked once against the Midas statement).
   - **Splits:** from Yahoo's split history; code adjusts the quantity and tells me ("NVDA split 10:1 — your 10 shares are now
     100; check it in Midas"). No drop alert in a split week (section 3, "AI auditor").
2. **Value and weights (weekly):** each holding's value, its weight in the **stock portfolio** (gold and BES not included), and
   its gain / loss in $ and %; the stock portfolio's total.
3. **Benchmark — shadow portfolios (weekly):** every money movement is copied on the same day, for the same dollars, into a
   **SPY shadow** and a **gold shadow**: a buy puts money in; a sale or a dividend takes money out. Cash waiting at the broker
   is not counted (simple first).
   - For me and for each shadow: **put in**, **got back** (sales + dividends), **value now**, and the return.
   - **Return:** for the first 12 months only the total return (%), because a short gain turned into a yearly figure misleads
     (+1% in one week ≈ +68% a year). After 12 months, also the yearly return that counts every buy (`xirr`).
   - SPY uses Yahoo's adjusted close (dividends reinvested; a small advantage for the shadow, whose dividends are not taxed);
     gold uses the gold price in USD.
   - Information only: it shows whether my picks add anything over SPY and gold. It never moves money.
4. **Total wealth (`total_wealth`):** stocks (from the ledger) + gold + BES, and its share of the goal (a setting in
   `ayarlar.yaml`: 800,000 $). I enter each gold purchase and, once a month, my BES payment and BES total; each entry is a new
   dated row in `other_assets` (append-only).
   - **Gold:** `/gold 1 4689` = 1 gram bought at 4,689 TL a gram (a sale: minus grams). What I put in = the sum of my purchases
     (TL → USD at that day's rate); value now = my grams × today's gold price per gram, fetched by code.
   - **BES:** `/bes 8670 245000` = this month's payment and the total shown in the BES app (TL). Value now = the latest total
     (TL → USD at that week's rate). Fund switches inside BES are not entered; the total already includes them, the returns and
     the company and state contributions.
   - Emergency cash is not counted (user-confirmed).
5. **Where the new money could go (weekly, user-confirmed; was monthly — same work, no extra cost):** it ranks the green-list stocks — down from
   their high + thesis intact + a fair price line come first. Message: "this month's money could go to …". It never buys. A stock
   that is already above **25%** of the stock portfolio gets no new money (the portfolio rebalances itself with new money, no
   selling, no tax); being above 25% is fine and triggers no sell alert (Lynch: do not cut the flowers). **A stock skipped only
   because of the 25% rule is not dropped silently:** the summary lists it under "Not suggested (25% rule)" with the rank it would
   have had and its weight — "Not a sell signal. Your call." (`weight_cap`).
6. **Drop alert:** a stock I hold falls **20%** from its highest weekly close of the last 52 weeks → Telegram, and agent 3 runs a
   "did the fundamentals break?" check at once. Filings are slower than the price, so the check reads **the latest filing and the
   latest news** (agent 1's `articles` for that stock + a short web search: e.g. "sales are slowing", "management cut its outlook").
   The answer: "thesis intact, the drop is the market" or "thesis point 2 broke" or "news says watch: …". News can only say "watch";
   a sell suggestion still needs agent 3's filing-based triggers. It never says "sell".
7. **Valuation watch:** PEG > 3 **or** free-cash-flow yield < 1% for **4 weeks in a row** → information only ("expensive for now") and
   the stock goes to the back of the queue for new money. **No sell suggestion.** Weekly figures live in the database, not in
   the card; the card gets a dated note only when an alert fires.
8. **Market filter: not used in version 1** (decision: 2026-10-04 — option A, no insurance). Tests (`BAGLAM.md` section 3): an
   S&P 500 average of about 21–55 weeks (40 in the middle) roughly halves the largest drop but costs return; with monthly buying,
   "new money waits" protects almost nothing, "sell half" costs about 4 points a year, "sell all" about 7–8. Later idea (not now):
   **shrink, do not sell** the portfolio on a macro reason (e.g. rising interest rates) — to be discussed later.
9. **No sell signals at all from agent 4** — no per-stock technical signal, no market-filter selling. Selling is suggested only by
   agent 3's triggers (above); the decision is mine.

**Storage (SQLite):** `holdings` (the ledger) · `prices` (Friday closes: my stocks, the green list, SPY, gold, USD/TRY) ·
`signals` (`new_money_rank`, `weight_cap`, `drop_alert`, `expensive`) · `other_assets` (my gold / BES entries) · `snapshots`
(one row per week: stock value, put in, got back, return, SPY shadow, gold shadow, gold, BES, `total_wealth`, share of the
goal — the frozen weekly history).

**Output:** the portfolio block of the Sunday summary; the same on demand with `/portfolio`. Example (made-up figures):

```text
PORTFOLIO — week ending 2026-11-06
Value $14,820 · week +1.2% · put in $13,000 · got back $40 (dividends)
Return so far: +14.3%   (yearly figure after 12 months)
Same money, same days → SPY $14,310 (+10.4%) · Gold $13,650 (+5.3%)
You vs SPY: +$510
Weights: NVDA 31% · V 22% · KO 18% · COST 15% · RIO 14%
Drop alerts: none · Expensive 4 weeks: NVDA (PEG 3.4)
New money: 1) V  2) COST
Not suggested (25% rule): NVDA — would rank 1st, 31% of the stock portfolio. Not a sell signal. Your call.
Total wealth: stocks $14.8k + gold 52 g $6.8k + BES $5.3k = $26.9k · 3.4% of $800k
```

**Test:** a hand-checked ledger (two buys, a sale, a dividend, a split) gives the same value, weights, shadow values and return
as a spreadsheet.

### AI auditor (decision: 2026-10-04)

**What it prevents** — the errors we actually met: a wrong figure (Coca-Cola's short-term investments, Boeing's debt), a wrong
reading (the old system's NET: a general legal risk sentence taken as a real case), an invented quote.

**One auditor, used only where an error is expensive.** It is not a running agent but a check step called inside agents 2 and 3.
Free code checks come first; the auditor is the second line. **It never produces or fixes figures** (the AI does not produce figures).

| Stop | Error and its cost | Who checks |
|---|---|---|
| Agent 1 (Eye) | a tag mapped to the wrong company (medium) · a poorly translated sentence (low) | **code:** the ticker exists in SEC's company list and the name is close; otherwise the mapping waits and the Sunday summary asks me · the sentence: no audit |
| 1B Counter | — (pure code) | tests |
| **Agent 2 (Research)** | an invented or misread **serious negative event** forces news-flow to 0 (medium) | **code + AI auditor** (only these events) |
| **Agent 3 (Analysis)** | a wrong figure, a wrong reading, an invented quote → a wrong grade, **a wrong sell suggestion** (high) | **code + AI auditor** (the main place) |
| Agent 4 (Portfolio) | a split shows as a fake −50% drop (low) | **code:** no drop alert in a week with a split in Yahoo's history |
| Hermes commands | a message misunderstood ("15" vs "50") (medium) | **me** (every change asks for confirmation) + **code:** `/sold` cannot exceed what I hold; `/bought` / `/sold` price more than 20% from that day's close → "are you sure?"; an unknown ticker is refused |

**Shared engine, one rule card per place.** Shared: the model, the output format (for each item **pass / fail / not_found** + a
quote + a reason), logging and cost, "check only, never produce figures". Per place a short **rule card** file (task, inputs,
numbered checklist, known traps, pass criterion, what happens on a fail), read as the AI instruction on every run; full texts are
written with agent 3's code (under `ortak/`, planned `shared/auditor/`). Four cards:

1. **Agent 3 — figure audit.** Input: the ~10 main figures code took from SEC (revenue, operating profit, operating cash, capex,
   cash, short-term investments, marketable securities, debt, share count, net profit — each with its XBRL name and period) + the
   filing's main tables. Checklist: find each figure and quote its row · same unit (thousands / millions) · same period (year, last 4
   quarters, 9 months) · liquid assets = cash + short-term investments + marketable securities — any part code missed? · debt =
   long-term + current portion + short-term — any part missed or counted twice? · share count diluted average, after splits?
   Known traps: Coca-Cola short-term investments under another name · Boeing only the current part of debt · Pfizer 2020 a single
   item in `LongTermDebt`. Pass: difference under 1% or rounding only.
2. **Agent 3 — reading audit.** Input: Sonnet's "why?" answers, warnings and quotes. Code first checks every quote appears verbatim
   in the filing (catches invented quotes for free); then the auditor: does the quote really support the claim? general risk
   sentence or company-specific event? (the NET lesson).
3. **Agent 3 — sell-suggestion audit.** Input: the "consider selling" suggestion and its trigger. Have the figures behind it passed
   card 1 and the claims card 2? If the thesis broke, is the evidence really in the filing / news?
4. **Agent 2 — serious-negative event audit.** Input: the event, its source link, its quote. Code first checks the quote is in that
   source; then: is it really about this company? within the last 12 months? company-specific, not a general risk sentence? Not
   confirmed → the event is not counted and a note is written. Tone labels and positive events are not audited (cheap errors; the
   score is only a ranking).

**When agent 3's auditor runs:** a stock's **first card** (cards 1 + 2) · a `data_check` flag is open (1) · **before every sell
suggestion** (3) · a big grade change, `solid` ↔ `weak` (1 + 2) · a **random 1 in 5** routine quarterly update (1 + 2, to measure
the error rate).

**On a fail:** the card gets an **`unverified`** mark, Telegram gets "the auditor disagrees: …"; a sell suggestion is **held back**;
the figure is not changed; the decision is mine.

**Model:** **DeepSeek V4 Pro**, fallback **GPT-6 Sol** (section 10.1). The auditor must come from a **different model family** than
the writer (Claude Sonnet 5.5): a model checking its own writing tends to share its blind spots. Cost about 0.01 $ per audit — a few
cents a month.

**Living checklists:** every new kind of error found (acceptance test, my checks, a big review) is added to the relevant card's
"known traps", like the synonym ledger.

**An error test set per card** (like the golden set): card 1 — the old prototype's wrong figures (Coca-Cola and Nvidia liquid
assets, Boeing debt, Pfizer 2020 debt); card 2 — a fake claim that turns a general risk sentence into a case (NET) and an invented
quote; card 4 — another company's news and a 3-year-old event. Rerun after every card change. This is also the test of "is DeepSeek
V4 Pro enough?"; if it misses, switch to GPT-6 Sol.

**Big review every 6 months** (started by me, not automatic): the rules and the golden set are reviewed by one or two strong
outside models, like the external review of 2026-10-03 (`docs/reviews/`) — the most valuable check of this round.

### Rules that prevent spending

1. Agent 3 runs on an **event**, not a calendar: once a week it asks SEC "is there a new 10-Q / 10-K?" (free); if not, it does nothing. HK / A: when I put a new PDF in the `filings/` folder.
2. An archived stock is never analyzed.
3. Every agent writes a row to the `runs` table on every run (start, end, `ok` / `error`, dollars spent).

### Telegram and Hermes (one counterpart)

On Telegram my only counterpart is **Hermes**; I do not talk to the 4 agents separately. Hermes runs the agents and reads the results.

- **When a message arrives:** one summary on Sunday (new candidates, what changed on cards, stocks that already have a card and were mentioned a lot this week, non-US names mentioned a lot, data still `unclear`, new subsector proposals, the portfolio block of agent 4) · **immediately:** if the grade of a stock in my portfolio drops · **immediately:** if an agent errors · a stock that comes out solid and enters the green list. Agent 1's daily output does not go to Telegram, only to `Inbox/`.
- **What it can do:** answer questions (it reads the database + the cards: "XYZ'nin karnesi ne diyor?", "bu ay ne harcadık?") and run a command from the **defined command list** ("XYZ'yi takibe al", "ABC'yi portföye ekledim", "XYZ'yi şimdi analiz et", "XYZ'deki U1 uyarısını kapat, çünkü …"). The command list is written in the implementation plan.
- **Asking for missing data (decision: 2026-10-03):** if agent 3 cannot find a figure (one that landed in the ledger), it asks me —
  **when I say "XYZ'yi analiz et"** and **on Sunday** during the analyses (that run's gaps in one message).
  The message is not a cryptic one-liner; it is **plain and clear**; code fills the template, a cheap model simplifies it:
  which stock · which figure · which year · why it is needed (which measure cannot be computed) · where to find it (e.g. "10-K → cash
  flow statement → 'Stock-based compensation' line") · how to answer (e.g. `XYZ 2025 borç 12,3 milyar`). Code checks the figure I enter
  (on an inconsistency such as a 10-times gap versus other years, "emin misin?"), and the card records `source: user`;
  if no answer comes, the figure stays `unclear` and is reminded once.
- **What it does not do:** it does not freely change the database / files (only the command list) · it does not change code or rules (that work is on the development Mac) · it does not trade.
- Chat with Hermes uses my ChatGPT / Codex subscription if Hermes can log in with it (checked in step 0); otherwise a cheap but strong model (DeepSeek V4 Pro). Details: section 10.
- In step 0 (setup) this way of working is tried and confirmed.

## 4. Technology decisions

| Topic | Decision |
|---|---|
| Language | Python (one language) |
| Development | On the main Mac (Claude Code / Cursor); each agent is tried by hand here first. Bridge: GitHub |
| What runs it | Hermes Agent, on the backup MacBook Air M2 (16 GB), 24/7. No code is written on the Air: it is updated with `git pull`; `.env`, the site session, and the real SQLite live there. Hermes only schedules and reports; the calculation / analysis logic is in our code |
| Communication | One counterpart on Telegram, Hermes (section 3, "Telegram and Hermes") + Drive folders |
| AI | Agents call models through one client in `ortak/` with an ordered provider list per job: my API credits first, then OpenRouter (section 10). Hermes chat: ChatGPT / Codex subscription if possible. The Claude **subscription** is not connected to Hermes (terms of use); Claude **API credits** are fine |
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

Tables: `stocks`, `articles` (full text included), `tags` (mapping: kind, maps_to, exchange, country, sector, subsector), `commodity_links`, `scores`, `missing_data` (the ledger), `financials`, `prices`, `signals`, `holdings` (the ledger: buys / sells via Hermes; dividends and splits added by code), `other_assets` (my gold / BES entries), `snapshots` (agent 4's weekly row), `runs` (dollars spent included).

```text
Investing/                                 (Drive)
├── Inbox/                                 agent 1's daily list (title + one sentence + address)
├── Weekly/                                weekly summaries
├── Backup/                                nightly SQLite copy
└── Stocks/<TICKER> - <Company name>/      flat; sector is in the card header
    ├── card.md                            born in agent 2
    └── filings/                           HK / A-share PDFs (I upload them by hand)

investment-agents/                         (code, Git)
├── agents/eye/  counter/  research/  analysis/  portfolio/
├── shared/                                AI, SEC, price, Drive paths, database
├── ayarlar.yaml
└── docs/  YOL_HARITASI_v2.md  BAGLAM.md  GLOSSARY.md  TASINANLAR.md
```

Today's folders are still `ajanlar/` and `ortak/` (the prototype and the backtest). New code uses the names in the tree above.

## 6. Budget

- AI / API: **at most 25–30 $ / month**. Expected once running: ~6–7 $ / month on OpenRouter prices (agent 1 ~0.2 $, agents 2 + 3 ~4–5 $, web search ~0.6 $); while my API credits last, close to 0 (section 10)
- Emtia Defteri + Dragonomi subscriptions are **outside** this budget
- OpenRouter: a fixed monthly limit of **15 $**, a Telegram warning at **10 $**; the `runs` table answers "what did we spend this month?" from Telegram

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
| **4. Portfolio** | Ledger, value and weights, benchmark against SPY and gold, total wealth, new-money ranking with the 25% note, drop alert, valuation info; no sell signals; code only | The ledger test passes (section 3, "Agent 4 rules"); the Sunday summary shows the portfolio block (value, return, SPY and gold shadows, weights, total wealth, new money with the 25% note); a drop alert triggers agent 3's check |

## 9. Open topics (decided together before coding)

**Decision order (2026-10-03):** all decisions and plans first, then code.

1. ~~Overall frame~~ ✅ (2026-10-03: card = the stock card, working principle, site permission, development / runtime split)
2. ~~Architecture~~ ✅ (2026-10-03: section 3 — flow, stock states, in_portfolio, event-driven runs, Telegram / Hermes)
3. ~~Agent 1 (Eye)~~ ✅ (2026-10-03: section 3, "Agent 1 rules")
4. ~~Agent 2~~ ✅ (2026-10-03: Counter, sector list, reading, commodity link, birth of the card, score rules — section 3)
5. **Agent 3** — ✅ (2026-10-03 / 04: rules + 2 external reviews applied + prototype and golden set 10/10 + AI auditor — section 3). **Left:** third review
6. ~~**Agent 4**~~ ✅ (2026-10-04: weekly price watcher — new-money ranking, drop alert, valuation and weight info; no sell signals; market filter not used in v1 — section 3). Renamed **Portfolio** the same day: ledger, benchmark against SPY and gold, total wealth, the 25% note; code only. Later: a macro "shrink, do not sell" idea
7. **Implementation plan** — section 10. ✅ 10.1 models and providers, ✅ 10.2 Hermes command list, ✅ 10.3 Air setup checklist (2026-10-04). Left: 10.4 coding order

Topic notes:

- ~~**Agent 2 score rules.**~~ ✅ section 3, "Score rules".
- **Card format.** Which metrics, which checks, how the "reason" section is written. Fundamental-analysis result in 3 classes: **solid / mid / weak**; only solid ones go to agent 4 (the green list). **To be discussed with agent 3:** if data is missing, Hermes asks me for it on Telegram (I find it and provide it, the agent continues the calculation) — control stays with me, the work stays with the agent.
- ~~**Agent 4 rules.**~~ ✅ section 3, "Agent 4 rules". No market-filter selling in v1; later idea: shrink the portfolio on a macro reason (e.g. rising rates).
- ~~**Site terms of use.**~~ ✅ The site owner gave permission (see section 4, Site reading).
- **HK / A-share data** (⏸ deferred — version 1 is US only). Which figures will be taken from the PDF by hand / by AI. Note: US filings do not need PDF / OCR (SEC figures are a ready table). Most HK / A PDFs contain text → read with a free Python library; OCR only for a scanned (image) PDF, and that too is free on the computer.

## 10. Implementation plan

### 10.1 Models and providers (decision: 2026-10-04)

**Language:** every system output is **English** — cards, reports, the Sunday summary, Telegram messages and commands; I talk to
Hermes in English. The sources are Turkish (Emtia Defteri, Dragonomi), so agent 1 reads Turkish and writes its one sentence in
English — checked in the model test. (My working conversations about the project stay in Turkish — `AGENTS.md`.)

| Job | Model | Effort | Fallback |
|---|---|---|---|
| **Cheap** — agent 1's one sentence, new-tag classification, making Telegram messages plain | **DeepSeek V4 Flash** | — | Gemini Flash-Lite or GPT-6 Luna if the test is poor |
| **Strong** — agent 2 (tone, news flow, score reasons), agent 3 ("why?" answers with quotes, first thesis, thesis check, drop-alert check) | **Claude Sonnet 5.5** | **high** | **GPT-6 Sol** |
| **Hermes chat** (Telegram) | my ChatGPT / Codex subscription, if Hermes can log in with it (checked in step 0) | — | **DeepSeek V4 Pro** (cheap, strong for its price) |
| **Auditor** (agents 2 and 3; section 3, "AI auditor") | **DeepSeek V4 Pro** — a different family from the writer | — | **GPT-6 Sol** |

Not needed for routine work: Opus 5.5 / GPT-6 Astra (the code does the arithmetic; the model reads and explains). A one-off use
(e.g. one first thesis) is possible with a Telegram override.

**Who writes the first thesis:** the AI (strong model), decided in section 3.

**Provider order (per job, in `ayarlar.yaml`):** my API credits first, then OpenRouter. The client in `ortak/` tries the list in
order; on an error, exhausted credit or quota it moves to the next one; every call's cost goes to `runs`.

```yaml
cheap:  [deepseek: deepseek-v4-flash,          openrouter: deepseek/deepseek-v4-flash]
strong: [anthropic: claude-sonnet-5.5 (high),  openrouter: anthropic/claude-sonnet-5.5,  openai: gpt-6-sol,  openrouter: openai/gpt-6-sol]
auditor: [deepseek: deepseek-v4-pro,         openrouter: deepseek/deepseek-v4-pro,   openai: gpt-6-sol,  openrouter: openai/gpt-6-sol]
```

**My credits (2026-10-04):** Anthropic API 90 $ (expires 2026-10-19), DeepSeek 10 $, OpenAI API 5 $. The system will not be live
before 10-19, so the Anthropic credit is for development: the model test, agent 3's AI parts, the 20-stock acceptance test (≈ 4–5 $
with Sonnet). It is **not** spent just to use it up. DeepSeek's 10 $ covers agent 1 for years; OpenAI's 5 $ covers the GPT tests.
Using the ChatGPT subscription inside the agents (through the Codex command-line tool) is possible but not planned (quota locks,
unclear terms); it can be added as a provider later.

**Choosing by test, not by guess:**
- cheap: 20 real posts → the model's English sentences side by side; I choose.
- strong: two companies' "why?" answers from Sonnet 5.5 and GPT-6 Sol, shown **without model names**; I choose.

**Model change from Telegram (Hermes command list):**
- one job: `analyze XYZ with opus-5.5`
- from now on: `set strong model to gpt-6-sol`
The override lives in the database on the Air (not in `ayarlar.yaml` in git, so the repo stays clean); every change is logged; the
spend limit still applies.

**Data sent to models — only what the job needs.** Post texts and filings go out; my holdings, trades, amounts and portfolio do not
go to a model unless a job needs them (e.g. Hermes answering my own question). DeepSeek's own API processes data in China — fine
for news text, never for my personal data.

**Spend safety:** OpenRouter monthly limit 15 $, a Telegram warning at 10 $ (section 6).

### 10.2 Hermes command list (decision: 2026-10-04)

Hermes may change something **only** through these commands; anything not on the list it cannot do ("not on the command list").
All commands are registered in the Telegram `/` menu with a short description (names: lowercase, one word — Telegram's rule).
I can also write a plain sentence ("I bought 10 KO at 85.65"); Hermes maps it to a command and shows the exact command in its
confirmation. Clashes with Hermes's own built-in commands are checked in step 0; on a clash ours is renamed.

**Rules:** (1) every command that changes something asks for confirmation first — Hermes lists exactly what will change, and runs
it only after `yes`; (2) every change is logged (what, when, which command); (3) each command is a small Python function in our code
(`python -m ortak.komut …` style) — Hermes calls it, it never edits tables or files itself.

**A. Information (changes nothing, no confirmation)**

| Command | What it does |
|---|---|
| `/help` | lists all commands with a short description |
| `/summary` | shows the latest Sunday summary again |
| `/green` | the green list: type, grade, price line |
| `/candidates` | this week's candidates with scores and reasons |
| `/card KO` | summary of the latest card entry + Drive link |
| `/portfolio` | the portfolio block: holdings (quantity, average cost, weight, gain / loss), benchmark against SPY and gold, total wealth and its share of the goal |
| `/missing` | missing figures waiting for me |
| `/spend` | this month's AI spend by provider; how much is left of the limit |
| `/model` | which job runs on which model now |
| `/status` | system health: when each agent last ran, any errors |

**B. Actions (change something, ask for confirmation)**

| Group | Command | Example | What changes |
|---|---|---|---|
| Stock state | `/watch` | `/watch KO` | `candidate` → `watching`; agent 3 starts the card; a note on the card |
| | `/archive` | `/archive KO` | `watching` → `archived`; no new analysis or spend; a note on the card |
| | `/unarchive` | `/unarchive KO` | `archived` → `watching` |
| Portfolio | `/bought` | `/bought 10 KO 85.65` (date and fee optional) | a BUY row in `holdings`; on the first buy `in_portfolio = yes` and a card note |
| | `/sold` | `/sold 5 KO 92.10` | a SELL row; when the position reaches 0, `in_portfolio = no` |
| | `/gold` | `/gold 1 4689` | a gold purchase: grams and the TL price per gram (a sale: minus grams) → a new dated row in `other_assets` (total wealth); a price more than 20% from that day's gram price → "are you sure?" |
| | `/bes` | `/bes 8670 245000` | this month's BES payment and the BES total (TL) → a new dated row in `other_assets`; a total more than 50% away from the last one → "are you sure?" |
| Analysis | `/analyze` | `/analyze KO` or `/analyze KO opus-5.5` | runs agent 3 now (filing + latest news); the confirmation shows the **estimated cost** |
| Card | `/closewarning` | `/closewarning KO U1 one-off tax deposit, not recurring` | the warning closes; a note with the reason; it does not reopen unless the condition changes |
| | `/thesis` | `/thesis KO <corrected point>` | my correction of the AI's thesis as a note; the old thesis is not deleted |
| | `/note` | `/note KO met management at a conference…` | my free note on the card |
| Data | `/data` | `/data NKE 2026 interest 0.25bn` | enters a missing figure I was asked for; code checks it is plausible (a 10× gap vs other years → "are you sure?"); the card says "source: user" |
| | `/tag` | `/tag rio-tinto RIO` | fixes a wrong tag mapping; the tag is not asked to the AI again |
| Settings | `/model` | `/model strong gpt-6-sol` · `/model strong default` | persistent model override (in the Air database), or back to the default |
| | `/subsector` | `/subsector add Uranium Energy` | approves a new subsector (the answer to "add a new subsector?") |

`/model` appears in both groups: without arguments it only shows; with arguments it changes.

**Deliberately not on the list:** changing rules, thresholds or code (done on the development Mac; no code is written on the Air) ·
deleting a card entry (append-only) · buy / sell orders (the system never connects to a broker) · changing the spend limit from
Telegram (only in the OpenRouter dashboard, for safety).

### 10.3 Air setup — step 0 (decision: 2026-10-04)

Checklist: `docs/AIR_SETUP.md` (7 phases: the Mac, tools and project, Drive, Telegram bot, Hermes, OpenRouter, tests). Key
points: a separate macOS user, FileVault, no sleep on power, Screen Sharing / SSH from the main Mac; a read-only GitHub deploy
key; `.env` with `chmod 600`, never committed; the bot talks only to my Telegram user ID; Hermes logs in with the ChatGPT
subscription, runs as a launchd service, its terminal powers limited to our command scripts; agents run as script-only cron jobs
(no LLM); OpenRouter key with a 15 $ monthly limit. Done when the tests in phase 7 pass.

