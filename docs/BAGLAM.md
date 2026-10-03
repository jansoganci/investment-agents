---
doc: Context notes
date: 2026-10-03
status: reference
publish: no
---

# Context — the information behind the decisions

`YOL_HARITASI_v2.md` says **what** we will do; this file says **why** we decided that.
Source: the planning chat of 2–3 October 2026 (inside the old project, Cursor).

Names follow `docs/GLOSSARY.md`. Section numbers are unchanged.

## 1. Investor profile

- The user used to trade on technical analysis alone and took sharp drops in stocks with a weak business → now **fundamentals first**.
- Experience 3+ years. The system's role: **it gives a list + a reason; the decision and the trade stay with the user.**
- On a 30% drop: **the user waits, but loses sleep** → risk management and calm, low-turnover rules matter.
- Focus: US + China stocks (HK + A-shares through İş Bankası; the user accepts the commission, a premium is fine up to ~3–5 million TL), then commodities. 5–10 stocks + ETFs.
- Cash flow (monthly): stocks 25–50 thousand TL · BES (Turkish private pension) ~9 thousand TL (taken from salary) · gold ~5 g (~30 thousand TL). Spending 50–75 thousand TL. Emergency fund: about 3 months of spending is already there. Salary is fixed for now.
- Idea source: two paid sites of an older investor the user follows ("abi") — **emtiadefteri.com** and **dragonomi.com**. No newsletter / RSS, but there is a sitemap (address + time of new posts, no login). Title / tags are public; the rest of the post is read after login. Both sites run on Ghost, managed by agents 24/7; about 100–150 posts a day in total. The site owner personally allowed reading (scraping); no API; condition: do not abuse it. A Grok Bot used to log in and read the posts one by one.

## 2. Goal math (in today's money, the "middle" case)

Assumption (annual, after inflation): stocks 7%, gold 1.5%, BES 3%. Start 500 thousand TL. The user's exchange rate: 30 million TL ≈ 800 thousand $ (~37.5 TL/$).

| Monthly stocks | Total after 10 years | Monthly income at the 4% rule | Share of spending (62.5 thousand) |
|---|---|---|---|
| 25 thousand TL | ~10.4 million TL | ~35 thousand TL | 55% |
| 37.5 thousand TL | ~12.5 million TL | ~42 thousand TL | 67% |
| 50 thousand TL | ~14.7 million TL | ~49 thousand TL | 78% |

- Bad (stocks 5%) to good (stocks 10%) range: 9.5–16.6 million TL.
- In nominal TL the 30 million is likely to be passed; purchasing power lands around 10–17 million of today's money. **The goal is always thought of in today's money.**
- Left out of the math (all of them help): the BES and gold already saved, future raises.
- Main lesson: what carries the goal is the **monthly saving**; the system's job is to put the money into good companies and protect against big mistakes, not a miracle return.

## 3. Technical analysis: Selçuk Gönençler 5-8-13 and backtest results

### Rule (the user's description; code: `ajanlar/teknik/backtest/gunluk_5_8_13.py`)

The code still stores the token in parentheses. Docs use the English name.

| State | Condition (close vs SMA5/8/13) | Trade (on the money set aside per stock) |
|---|---|---|
| `CONFIRMED_BUY` (`TEYITLI_AL`) | above all three | fill the rest with the remaining cash → 100% |
| `CAUTIOUS_BUY` (`TEMKINLI_AL`) | the day before, below all three; today above 5 and 8, below 13 | buy 40% |
| `CAUTIOUS_SELL` (`TEMKINLI_SAT`) | below 5; above 8 and 13 | sell 40% of what is held |
| `PREPARE_EXIT` (`RISK`) | below 5 and 8; above 13 | no trade |
| `SELL` (`SAT`) | below all three | sell all of it (if none is held, do nothing) |
| mixed | the rest | keep the previous state |

A trade happens only on the day the state **changes**. The signal uses the ordinary close; the return uses the dividend-adjusted price; cost is 0.1% per trade. Data: Yahoo Finance (`yfinance`).

### Daily result (January 2016 – October 2026, 24 stocks equal weight)

| Method | Annual return | Largest drop |
|---|---|---|
| Buy and hold | 19.8% | −28.6% |
| SPY | 14.9% | −33.7% |
| 55% stocks + cash, no timing | 10.9% | −16.3% |
| **5-8-13 (the 40% rule)** | **4.9%** | −17.3% |

The rule lagged buy-and-hold in **24 of 24** stocks; about 57 trades per stock per year. Cause: the three averages sit very close together → daily noise produces signals; selling after a drop misses the best recovery days. "A smaller drop" is not a timing success; it is the result of being out of the market.

### Weekly result (annual return / largest drop; code: `haftalik.py`)

| Rule | 2006–2015 (2008 included) | 2016–2026 | Trades per year |
|---|---|---|---|
| Buy and hold the stocks | 16.7% / −42.3% | 19.9% / −27.5% | – |
| Buy and hold SPY | 7.4% / −54.6% | 14.8% / −31.8% | – |
| Weekly 5-8-13 | 6.6% / −23.8% | 8.6% / −14.6% | 12 |
| MA8 + RSI>50, sell below MA8 | 5.0% / −16.3% | 7.4% / −13.7% | 9 |
| The same, patient exit (below MA8 **and** RSI<50) | 9.2% / −18.1% | 10.9% / −17.8% | 4.6 |
| Hold if above the 40-week average | 10.0% / −20.2% | 11.4% / −16.9% | 3.9 |
| **Hold all of them if SPY is above its 40-week average** | **10.5% / −16.8%** | **14.3% / −15.8%** | 3.6 |

- No rule beat buy-and-hold on return; timing = **insurance** (a smaller drop, a smaller return).
- The cheapest insurance: the **market filter** (SPY 40-week). The price: in 2016–2026, 19.9% a year → 14.3%.
- Limits: the stocks were chosen looking from today (the absolute figures are optimistic, the comparison is reliable); cash earns no interest and there is no tax; the more rules you try, the higher the risk of a rule that "happened to fit the past" → it was proposed to watch for 3 months with paper money without changing the rules.
- Proposed but not run: with the market filter on, make the **entry** with weekly 5-8-13.

## 4. Lessons from the old system (do not repeat them in the card design)

The old step 3 was tested on 5 stocks (ROP, V, WM, APH, NET); **none of them got GREEN.** The cause was the rules, not the companies:

1. **NET — a false legal alarm.** The 10-K sentence "DOJ and GSA have sued suppliers *in the past*" is a general risk sentence; because the words "Department of Justice" appeared, it was counted as a concrete, open case (it overrode the "general warning" filter). It was wrongly tagged "competition law" (it is actually the False Claims Act). Because the sentence contained "pricing", it was said to "affect the thesis". The keyword list had been tuned to the previous test companies (Deere: farmer, dealer, right to repair; Visa: interchange, network rules).
   → **Lesson:** No legal / semantic judgment by word match. If an AI reads it, it must support the claim with a **quote** from the report; the split between "general risk warning" and "company-specific event" must be explicit.
2. **WM — a tie chain.** In the company-type classification two types scored equal; the one earlier in the list (A7, grows by acquisition) was chosen → "REVIEW_REQUIRED" → an automatic "thesis–capital tension" flag → ORANGE. The finding was not about WM; it was the system's indecision; the flag's name was misleading. 4 stages at once said "a human should look", but the signal quietly dissolved into ORANGE.
   → **Lesson:** If the system is not sure, it should say so plainly as **`unclear`**; it should not turn uncertainty into a negative finding about the company. Flag names should say what they are.
3. **APH — the same fact counted twice, and no way out.** Rule: flag if capital return including acquisitions is less than half of the return excluding them. APH: including 24.2% (excellent), excluding 57.6% → a flag; the same condition lit a second flag. The human review queue was empty → there was no way to clear the warning. Perverse effect: the better the company's own business, the higher the chance of a penalty.
   → **Lesson:** Look at the **absolute level** next to the ratio; one fact is counted once; every warning has a path for "a human looked and closed it".
4. **NET — convertible debt was not read.** In companies that report debt only under ConvertibleDebt* tags, debt and company value stayed empty. Fixed (old project, commit `c325d1d`): as a fallback, only when no ordinary debt tag exists at all. NET 2025: 1.974 + 1.291 = **3.265 billion $**.
   Extra note: the old Stage 8 debt total skipped "the current portion of long-term debt" — the new calculation must include it.

Overall lesson: the old step 3's **SEC fetch + compute in code** part is valuable (keep it); word matching and the 9-stage gate structure were heavy (dropped). The card should be one page that can be read in 5 minutes.

## 5. Behind the platform and subscription decisions

- MacBook Air 2022 = Apple **M2**, 16 GB RAM, 256 GB → Hermes supports it.
- Subscriptions: Cursor Pro (annual, Grok Bot included) · 2× OpenAI/Codex · 1× Claude.
- The **Codex subscription** can officially be used in Hermes (`hermes auth add openai-codex`); no extra API fee. Risk: when the quota fills, a **silent 2–4 hour lock** → jobs should save in pieces, and fall back to OpenRouter if needed; one of the subscriptions should be set aside for the agent only.
- The **Claude subscription is not connected to Hermes:** Anthropic's consumer terms allow Free/Pro/Max OAuth only in Claude Code and claude.ai; on a third-party agent there is an "extra usage" fee or account risk. Claude is for personal use and for writing code with Claude Code.
- Grok Bot stays as advisor / research / code help; there is no model choice, and the weekly quota is not public.
- Mac 24/7: plugged in, lid open, "Prevent automatic sleeping when the display is off", Optimized Battery Charging; in a short power cut the battery works like a UPS.

## 6. Idea sources (old project — ideas only, not rules)

- `../investment-intelligence/handoff_pack/01_INVESTMENT_PHILOSOPHY.md` — the user's documented investment philosophy (owner mindset, universe / attention philosophy, false-positive patterns, the list of missing personal philosophy). **Read it when talking about the card format.**
- `../investment-intelligence/handoff_pack/03_FA_STAGES_1_9.md` — which questions the old 9 stages asked (a question pool for card metrics).
- `../investment-intelligence/docs/AUDIT_REPORT.md` — the technical audit report of the old system.

Rules in those files such as "LOCKED", "Plan §0", and stage gates **do not apply** to this project.

## 7. Card draft (2026-10-03 — first draft; **the current decision is roadmap section 3, "Card format"**)

**Current skeleton (the decision):**

````markdown
---
ticker: XYZ
company: XYZ Corp
exchange: NASDAQ
country: US
sector: Information Technology
subsector: Semiconductors
status: watching          # code updates
in_portfolio: no          # code updates
lynch_type: fast_grower   # code updates
grade: solid              # code updates
last_entry: 2026-11-05    # code updates
opened: 2026-10-05        # first entry, never changes
publish: no
---
# XYZ Corp (XYZ)
> Story: <2 sentences — what it sells, where the money comes from>

## 2026-10-05 · research · agent_2
```yaml
score: 7
criteria:
  mentions: {score: 2, reason: "8 posts in 7 days"}
  tone: {score: 1, reason: "3 positive, 2 negative"}
```
<short summary>

## 2026-11-05 · fundamental · agent_3 · 2025 annual (10-K)
```yaml
source: {report: 10-K, period_end: 2025-12-31, url: "https://...", as_of: 2026-11-05}
lynch_type: fast_grower
grade: solid
measures:
  revenue_growth_3y: {value: 0.48, mark: good, decisive: yes, xbrl: Revenues}
  margin_stability: {value: 2.9, unit: pp, mark: good, decisive: yes}
  # ... 10 measures + debt + dividend
free_cash: {value: 1.2e9, stock_comp: 0.3e9}
price: {peg: 1.18, lynch_dividend_ratio: null, fcf_yield: 0.017}
warnings:
  - {code: U1, name: "Acquisition dependence", flag_kind: company_specific, flag_status: open, quote: "...", source: "10-K p.34"}
gaps: ["maintenance capex is not disclosed"]
```
### Summary
### Thesis
Why it is owned (at most 3 points):
1. …
3 things that would break the thesis:
1. …
### What changed

## 2026-11-06 · note · user
U1 kapatıldı, çünkü …
````

**First draft (kept for history):**

This is where the agent 3 discussion started. One question: **"Why do I hold this company, and is that reason still true?"**
On a 30% drop, opening the card should show in 5 minutes "is it the price that fell, or the company?"

**Note (2026-10-03):** The card is born in agent 2; the first entry is a research entry. The format below is the first draft of the fundamental entries agent 3 appends. File location now: `Investing/Stocks/<TICKER> - <Company name>/card.md`. The trial code ran from a scratchpad; it now lives in `ajanlar/analiz/prototip/`.

Each quarter / year a new section is appended to `card.md`; the newest entry is at the bottom. The figures are examples (made up).

```markdown
---
ticker: XYZ
sector: Industrials
opened: 2026-11-05        # date of the first entry; it does not change later
publish: no
---

## 2026-11-05 · 2025 annual (10-K)

**Summary:** Cash generation is strong, debt is low; half of the growth is from acquisitions, watch it.
**State:** … — reason: …

### Thesis — why it is owned (written on the first entry, then only checked)
1. … 2. … 3. …
**Is the thesis still true this period?** Yes — none of the 3 points broke.

### Figures (code computes; the AI does not do arithmetic)
| Measure | Latest year | 5-year trend | Note |
|---|---|---|---|
| Revenue growth | 9% | 8% a year | |
| Operating margin | 28% | flat | |
| Free cash flow / net profit | 1.1 | 1.0–1.2 | profit is turning into cash |
| Capital return (including / excluding acquisitions) | 12% / 45% | ↓ / ↑ | the two figures side by side |
| Net debt / free cash flow | 1.8 years | ↓ | current portion + convertible included |
| Share-count change | −6% (over 5 years) | buyback | |

### Warnings
| Code | What | Evidence | Kind | Status |
|---|---|---|---|---|
| U1 | Acquisition dependence | return 12% vs 45% | company_specific | open |
| U2 | Lawsuit | "…" (quote, 10-K p.34) | general_risk | info |

### Gaps (not counted as negative)
- Maintenance capex is not disclosed → not_computed.

### 3 things that would break the thesis (to watch)
1. Operating margin under 22% for 2 years in a row → this period: no

### What changed versus the previous entry?
- …

<sub>Source: SEC 10-K (link) · as-of date · model · cost $0.04</sub>
```

**How the lessons in section 4 are met in the draft:**

| Lesson | In the draft |
|---|---|
| NET: word match caused a false alarm | Every warning has a **quote** from the report + a `general_risk` / `company_specific` split; no word list |
| WM: uncertainty became a negative finding | "Gaps" is a separate section and is not counted as negative; warning names say what they are |
| APH: the same fact twice, and no way to close it | Ratio + absolute level together; each warning has one code; status `open` / `closed` |
| NET: debt was read incompletely | Debt = current portion + convertible included |
| The 9-stage gate was too heavy | 6 rows of figures, one page; no score / weight / gate |

**Open questions (with proposals):**

1. ✅ **Grade label** (decision: solid / mid / weak / unclear) — the user wanted 3 classes: solid / mid / weak. Proposal: also **unclear** (not enough data); the AI suggests it + writes the reason.
2. **Valuation section** — ✅ decision (2026-10-03): Lynch PEG will be used (roadmap section 3). Old proposal: none for now. Later, at most 2 descriptive figures (free-cash-flow yield, where the P/E sits in its own 5-year range); no "cheap / expensive" judgment.
3. ✅ **Closing a warning** (decision: a user note entry) — proposal: a dated user note at the end of the card (`2026-11-06 · user: "U1 kapatıldı, çünkü …"`); the agent reads it on the next run and does not reopen it unless the condition has changed.
4. **Who writes the first thesis** — proposal: the AI drafts 3 points, the user corrects and approves; later cards do not change the thesis, they only check it.

## 8. Agent 3 research notes (2026-10-03)

What the well-known investors look at (sources: Berkshire acquisition criteria, Fundsmith Owner's Manual, *One Up on Wall Street*,
Piotroski F-Score, AQR "Quality Minus Junk"):

| Who | What they look at | Why |
|---|---|---|
| Buffett / Munger | Years of consistent profit (no forecasts and no "it will turn around" companies) · high return on equity with little debt · a simple business · management · "owner earnings" | Past consistency is evidence, a forecast is hope; debt can make a weak business look strong. Buffett publishes no hard threshold; figures such as "ROE > 15%" are the books about him, not him |
| Terry Smith (Fundsmith) | High capital return (on a cash basis) · high gross margin · cash conversion · interest cover · little debt; "buy a good company, don't overpay, do nothing" | Reinvestment at a high return compounds; gross margin shows pricing power. The hard thresholds circulating online (gross margin > 50% and so on) are third-party commentary |
| Peter Lynch | Company type first (6 types) · a 2-minute story · **PEG** = P/E ÷ earnings growth (≈ 1 fair, < 1 attractive, > 2 expensive) · low debt / equity · net cash · inventory rising faster than sales is a red flag · share buybacks | The same ruler is not applied to every company (a cyclical looks cheap at the peak) |
| Fisher | A long runway for growth, R&D, honest management | Compounding needs room |
| Nick Sleep | Shares the gain from scale with the customer (Costco, Amazon) | A low margin is not always bad |
| Piotroski | 9 yes / no accounting questions | Computed entirely in code; it separated the winners among cheap stocks |
| AQR | Quality = profitable + growing + safe + paying out | Quality's definition as measured in long data |
| Graham / Klarman / Marks | Price and margin of safety | A valuation topic (open) |
| Ray Dalio | The whole economy: debt cycles, interest rates, inflation | Not on the card; later, a note on the market as a whole / the Sunday summary |

The user's own rules: no investing in a business the user does not understand · no buying just because debt is low; using debt well matters (interest cover,
capital return > the cost of debt) · holding the gross margin in a hard environment (high rates, oil, war) is a very good sign · a loss is not always
bad (Amazon).

SEC data was tried (Apple, Amazon, Cloudflare, Visa, Coca-Cola, Novo Nordisk): annual figures for 2021–2025 exist for all of them. Problems
found: Coca-Cola changed its debt name in 2024 · Cloudflare's debt is only under convertible names (2025: 1.97 + 1.29 = 3.26
billion $) · Apple has not reported interest expense separately after 2023 · Amazon does not report gross profit (it is computed as revenue − cost) ·
Visa has no cost of sales (gross margin cannot be computed) and, because of multiple share classes, there is no standard share-count name · Novo Nordisk
(20-F) uses IFRS names, annual only.

## 9. Agent 3 rules — a trial on 10 real companies (2026-10-03)

The trial code (a scratchpad; it was not in the project then; it now lives in `ajanlar/analiz/prototip/`) was run on the latest SEC annual report (mostly 2025) plus Yahoo's price that day. The figures
have not yet been compared by hand with the 10-K (that work is the acceptance test). The results can be used as the **expected grade** in the trial set.

| Company | Type | Grade | Why (short) | User's view |
|---|---|---|---|---|
| Coca-Cola (KO) | `slow_grower` | `mid` | capital return 13.8% (under the line); cash conversion 57% (one-off payments in 2024–25); price expensive (PEG 2.3, cash yield 1.4%) | correct; do not loosen the rule for KO (that would be fitting the past) |
| Nvidia (NVDA) | `fast_grower` | `solid` | every decisive measure ✅; but cash yield 1.7% → "the company is excellent, the price is a separate question" | correct |
| Nike (NKE) | `slow_grower` | `mid`, `shrink_rule: yes` | revenue 3-year average −3.2%; free cash 6.6 → 2.2 billion $ | sees it as weak; leave it `mid` for now |
| Starbucks (SBUX) | `slow_grower` | `mid` | operating margin 5-year average 14.1% → 7.9% | sees it as weak; leave it `mid` for now |
| Pfizer (PFE) | `slow_grower` | `mid` | revenue collapsed after Covid; debt ❌ (the Seagen acquisition) | sees it as weak; leave it `mid` for now |
| Intel (INTC) | `cyclical` | `weak` | capital return 2%; does not produce cash from the business + debt | correct |
| Boeing (BA) | `cyclical` | `weak` | capital return negative; interest cover 1.5; shares +34% | correct |
| Snap (SNAP) | `unprofitable` (under the old rule `stalwart`) | `weak` | operating margin −9%; shares +16% (stock comp) | correct; the `unprofitable` type was added |
| Dow (DOW) | `cyclical` | `weak` | margin −6 percentage points; does not produce cash from the business | correct |
| Rivian (RIVN) | `fast_grower` | `weak` (under the new rule; under the old rule `mid`) | burns ~2.5 billion $ of cash a year, runway < 3 years, shares +30% | correct — not the Amazon type, the Rivian type |

**What the trial taught (written into the rules):** splits (Nvidia was coming out "+877% shares") · the IPO year (Rivian) · companies that do not report operating profit
(Nike, Pfizer, Dow — the old "found 100% of the time" measurement was misleading, because of how coverage was defined) · negative equity
(Starbucks capital return was coming out 105% → switched to Smith's definition) · "shrinking 3 years in a row" was missing the Nike trap
(→ the 3-year average) · quality was not measured for slow growers (→ margin + capital return were added) · debt as one combined judgment ·
one-off payments (→ 3- / 5-year averages) · 7 and 10 were using different bases (Boeing 15.7 years → ~7.7 years).

**Amazon type vs Rivian type** (the user's summary): Amazon was a company that produced cash and, by preference, lost money or made very little profit;
its cash rose every year because it was investing furiously in infrastructure; today it is established and reports a profit. Rivian both loses money,
fails to produce cash from the business, and the cash on hand is falling → weak.

### After the two external reviews (2026-10-03)

Both reviews (`docs/reviews/`) found the same main error: **liquid assets were read incompletely** (short-term investments and
marketable securities missed at Coca-Cola, Nvidia, Nike, Pfizer — wrong tag names, parts treated as alternatives instead of added;
Nvidia uses a company-only tag). Rules and grade code were found correct; the problems were in data extraction. Decisions taken
(roadmap section 3): missing ≠ 0 · liquid parts added · operating-profit fallback with net interest · no cash-interest in accrual
measures · debt group order + candidate check · reverse splits only with Yahoo confirmation · margin stability vs previous 4 years
and vs last year · capital return = worse of 3y / 5y (cyclical 5y) · new type order (`unprofitable` = loss + cash burn before
`fast_grower`) + cyclical industry list by SIC · fast-grower safety rule · 20-F and IFRS read · FCF yield on 3-year average ·
PEG on diluted EPS growth · flags for one-offs, borderline, leases, acquisitions · the AI writes the first thesis.

Stock comp stays subtracted from free cash everywhere (review 1: warning only; review 2: subtract except in cash conversion).
Reason: net profit already deducts stock comp as a cost while operating cash adds it back; without subtracting it, cash conversion
(free cash ÷ net profit) compares unlike things.

**Golden set after the prototype rerun (2026-10-03, `ajanlar/analiz/prototip/altin_set.py`, 10/10):**

| Company | Type | Grade | Decisive measures / why | User |
|---|---|---|---|---|
| Coca-Cola | `slow_grower` | **`mid`** (borderline) | margin ✅ · capital return ➖ 14.3% (borderline) · cash conversion ➖ 55% · debt ✅ (true liquid 13.87 bn) · dividend cover ❌: 5-year free cash 39.06 vs dividends 39.96 bn (−2%) because of the 12.1 bn one-offs (IRS deposit, fairlife); without them 51.2 bn. Flags: one-off, borderline. The reviews' `solid` did not subtract stock comp. Back to `solid` once the one-offs leave the 5-year window | **`mid` is right** — do not bend the rule |
| Nvidia | `cyclical` (SIC 3674) | `solid` | capital return ✅ · debt ✅ · share count ✅ (×10 split confirmed by Yahoo). Flag: liquid 43.2 → 10.6 bn (company-only tag) | right |
| Nike | `slow_grower` | `mid` (shrink rule) | true liquid 9.03 bn → cash > debt; revenue 3-year −3.2% | right |
| Starbucks | `slow_grower` | `mid` | operating margin 15.6% → 7.9% ❌ | right |
| Pfizer | `slow_grower` | **`weak`** | capital return 3-year 4.7% ❌ (5-year 12.1%, carried by Covid years) · debt ❌. Needed net interest from interest income − expense | right |
| Intel | `cyclical` | `weak` | capital return 2.1% · debt ❌ | right |
| Boeing | `cyclical` | `weak` | capital return −6.2% · debt ❌ (53.9 bn; a prototype bug once read 8.5) · shares +34% | right |
| Snap | `unprofitable` | `weak` | stock comp makes 3-year free cash negative → loss + cash burn | right |
| Dow | `cyclical` | `weak` | capital return 5.8% · debt ❌ · flag: free cash falling | right |
| Rivian | `unprofitable` | `weak` | auto SIC code, but no profit in 5 years → not cyclical (user: "if it makes no profit, forget its cyclicality" — for now) | right |
| *Novo Nordisk* (IFRS, not in the set) | `fast_grower` | `mid` | gross margin −3.7 pt ❌; DKK converted for the price line (P/E 10.7, FCF yield 6.4%) | — |

Fixed during the rerun: debt groups need all their parts (Boeing) · net interest from interest income − expense (Pfizer, Dow) ·
P/E and dividend yield from SEC × FX, not Yahoo (ADR currency mix) · liquid data-check only on drops · dividend borderline flag.
