---
belge: Dış inceleme promptu (İngilizce) — 3. ajan kuralları ve 10 hisselik deneme
tarih: 2026-10-03
durum: incelemeye gönderilecek
yayinla: hayir
---

# External review prompt (English) — Agent 3

**How to use (note to me):** This is the earlier English wording, prepared to be given to the models unchanged. The answer is asked for in Turkish. The project master is now `DIS_INCELEME_PROMPT.md` (glossary names: solid / mid / weak / unclear). If a model was already given this file, leave this body as it is.

---

## PROMPT START

### Your role

Act as an experienced **equity analyst** and **financial data engineer**. Your job is to **audit** the fundamental-analysis
rules, the calculation method and the results of a trial we ran on 10 real US companies: find calculation errors, data
errors, code errors, logic flaws and overlooked risks.

**Write your answer in Turkish** (the user reads Turkish). You may add the English term in parentheses.

### Rules for accuracy (please read carefully)

1. **Data date: 2026-10-03.** Figures were pulled from SEC on this date; for most companies the latest fiscal year is 2025
   (Nvidia: fiscal year ending January 2026, Nike: fiscal year ending May 2026). Prices were taken from Yahoo on the same
   day. **If your knowledge cutoff is earlier than this, do not "correct" these years' figures from memory.** Verify only
   against a source you can actually access (SEC EDGAR, the company's 10-K); otherwise write "could not verify".
2. **If you find no error, say "no error found".** Do not invent problems. For every issue, show evidence: which figure,
   which formula, which line.
3. For every finding state **how you know**: "verified against source" / "recomputed from raw data in Appendix B" /
   "reasoning only".
4. **Do not expand scope.** The system's principles are below; instead of large proposals that contradict them (e.g. a full
   DCF model, adding banks), answer "is this needed for version 1?". If you propose something, propose its simplest form.
5. Priority: **(a) errors that produce a wrong class > (b) errors that produce a wrong figure > (c) logic weaknesses >
   (d) improvements.**

### Short context about the system

- A personal investment-advisor system. 4 AI agents read, research, analyse and give **suggestions**; **the user always
  makes the decision and places the trades.** The system never says BUY / SELL.
- The user is a beginner, long-term (10-year) investor; trades rarely; does not invest in businesses they don't understand.
- AI budget at most USD 25–30 / month. Principle: **keep it simple, build, test, fix** ("think fast, iterate faster").
- Version 1 covers **US exchanges only** (NYSE, NASDAQ; ADRs included).
- **Agent 3** (what we want you to review): builds a "report card" (karne) from the financial statements of stocks the user
  chose to follow, and assigns a class: **SAĞLAM (strong) / ORTA (medium) / ZAYIF (weak) / BELİRSİZ (undetermined)**.
  Strong ones enter a "green list" (green list ≠ BUY; it is only the list the technical-analysis agent looks at).
- Approach: **quality first** (Buffett / Munger / Terry Smith), structure from **Peter Lynch** (first the company type, then
  metrics are read according to the type). **Code** does all calculations; AI never produces numbers, it only answers
  "why?" questions with quotes from the annual report. Price does **not** enter the class; it is shown on a separate line.

### Data sources and method

**SEC (financial figures):** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (free, no key). Only the
`us-gaap` taxonomy was used (all trial companies report in us-gaap).

- **Annual (duration) values:** form `10-K` or `10-K/A`; period length 350–380 days; keyed by end date; if several facts
  share an end date, the **latest filed** one wins (to pick up later restatements).
- **Instant (balance-sheet) values:** form 10-K, facts without a start date; keyed by end date; latest filed wins.
- **Fiscal year ends:** union of end dates seen in the revenue and operating-income tags; the last 6.
- **Synonym-list method:** each figure has a list of XBRL names; for **each year separately** the code tries the list in
  order and takes the first one found (companies rename tags over time; e.g. Coca-Cola reported debt as `LongTermDebt`
  until 2023 and as `LongTermDebtAndCapitalLeaseObligations` from 2024). Lists:

| Figure | XBRL names tried (in order) |
|---|---|
| Revenue | Revenues · RevenueFromContractWithCustomerExcludingAssessedTax · RevenueFromContractWithCustomerIncludingAssessedTax · SalesRevenueNet |
| Cost of revenue | CostOfRevenue · CostOfGoodsAndServicesSold · CostOfGoodsSold |
| Gross profit | GrossProfit; otherwise revenue − cost of revenue |
| Operating income | OperatingIncomeLoss; **otherwise pre-tax income + interest expense** (Nike, Pfizer, Dow do not report operating income) |
| Pre-tax income | IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest · IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments |
| Income tax | IncomeTaxExpenseBenefit |
| Net income | NetIncomeLoss |
| Interest expense | InterestExpense · InterestExpenseNonoperating · InterestExpenseDebt · InterestAndDebtExpense · InterestPaidNet (last option = cash interest paid) |
| Operating cash flow | NetCashProvidedByUsedInOperatingActivities |
| Capital expenditure | PaymentsToAcquirePropertyPlantAndEquipment · PaymentsToAcquireProductiveAssets |
| Cash | CashAndCashEquivalentsAtCarryingValue · CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents |
| Short-term investments | MarketableSecuritiesCurrent · ShortTermInvestments · AvailableForSaleSecuritiesDebtSecuritiesCurrent |
| Equity | StockholdersEquity · StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest (information only; not used in formulas) |
| Total assets / current liabilities | Assets / LiabilitiesCurrent |
| Share count | WeightedAverageNumberOfDilutedSharesOutstanding |
| Dividends paid | PaymentsOfDividends · PaymentsOfDividendsCommonStock · PaymentsOfOrdinaryDividends |

- **Debt:** for the long-term part, the **first group found** among these is used and its found members are summed:
  (1) LongTermDebt → (2) LongTermDebtNoncurrent + LongTermDebtCurrent → (3) LongTermDebtAndCapitalLeaseObligations +
  LongTermDebtAndCapitalLeaseObligationsCurrent → (4) ConvertibleDebtNoncurrent + ConvertibleDebtCurrent +
  ConvertibleNotesPayable + LongTermNotesPayable. **CommercialPaper** and **ShortTermBorrowings** are added if present.
  Operating lease liabilities are not included. Debt is an open "research item" for us: components may overlap.
- **Liquid assets** = cash + short-term investments. **Free cash flow (FCF)** = operating cash flow − capital expenditure.
- **Share-count adjustments:** a year-over-year jump of 2, 3, 4, 5, 8, 10 or 20× (±6%) is treated as a **stock split** and
  earlier years are adjusted. The IPO year is skipped (that year's weighted-average share count is misleading).
- **Yahoo (prices):** last price, market cap, trailing P/E. Our rule says splits must be **cross-checked** against Yahoo's
  split history. Cross-check done in the trial: for Nvidia Yahoo shows ×4 (2021) and ×10 (2024); the code only adjusted ×10
  because SEC's later filings had already restated ×4 in earlier years. For Pfizer Yahoo shows "×1.054" in 2020; this is
  not a split but the price adjustment for the Viatris spin-off.
- **Sector:** in the trial the GICS sector was assigned **by hand**.

### The 10 metrics — definitions and formulas

All are computed for every company. "3y / 5y avg" = last 3 / 5 fiscal years.

| # | Metric | Formula |
|---|---|---|
| 1 | Revenue growth | 3-year CAGR: (revenue_last ÷ revenue_3 years earlier)^(1/3) − 1 |
| 2 | Margin stability | (last-year margin − average margin of the last 5 years [last year included]) × 100 → **percentage points**. Margin = gross margin; if gross margin is found for fewer than 3 years, **operating margin** is used |
| 3 | Operating margin | operating income ÷ revenue (last year) |
| 4 | Return on capital (Terry Smith style, ROCE) | 5-year average of: operating income × (1 − tax rate) ÷ (total assets − current liabilities − liquid assets). Tax rate = income tax ÷ pre-tax income, clamped to 0–35%; 21% if pre-tax income ≤ 0. Years with denominator ≤ 0 are skipped; at least 3 years required |
| 5 | Cash conversion | sum of FCF over last 3 years ÷ sum of net income over last 3 years; not computed if net-income sum ≤ 0 |
| 6 | Interest coverage | if liquid assets ≥ debt → "cash > debt" (✅); otherwise operating income ÷ interest expense (last year) |
| 7 | Years to repay debt | net debt = debt − liquid assets; if ≤ 0 → "cash > debt" (✅); if the 3-year average FCF ≤ 0 → "does not generate cash from its business, has debt" (❌); otherwise net debt ÷ 3-year average FCF |
| 8 | Share-count change | (last year ÷ first year) − 1; window at most 5 years; split-adjusted |
| 9 | Gross-profit growth | 3-year CAGR of gross profit; if it was ≤ 0 three years ago and is > 0 now → "just turned from loss to profit" (➖) |
| 10 | Years of cash runway | if 3-year average FCF ≥ 0 → "generates cash" (✅); otherwise liquid assets ÷ (−3-year average FCF) |
| T | Dividend covered by cash | sum of FCF over last 5 years ≥ sum of dividends paid over last 5 years |

### Thresholds

| # | Metric | ✅ good | ➖ medium | ❌ weak |
|---|---|---|---|---|
| 1 | Revenue growth | ≥ 15% | 8–15% | < 8% |
| 2 | Margin stability | drop ≤ 1 pt | drop 1–3 pt | drop > 3 pt |
| 3 | Operating margin | ≥ 15% | 5–15% | < 5% |
| 4 | Return on capital | ≥ 15% | 8–15% | < 8% |
| 5 | Cash conversion | ≥ 80% | 50–80% | < 50% |
| 6 | Interest coverage | ≥ 8× or cash > debt | 3–8× | < 3× |
| 7 | Years to repay debt | ≤ 3 or cash > debt | 3–5 | > 5 or no cash generation + debt |
| 8 | Share count | ≤ 0% | 0–10% | > 10% |
| 9 | Gross-profit growth | ≥ 20% | 10–20% | < 10% |
| 10 | Cash runway | ≥ 3 years or generates cash | 1.5–3 | < 1.5 |
| 10* | Same, for **fast grower + 3-year avg FCF < 0** | ≥ 5 years | 3–5 | < 3 |
| T | Dividend | covered | — | not covered |

**Debt (a single judgement in the class decision):** start from metric 6's colour; if metric 7 is ❌, downgrade one step
(✅→➖, ➖→❌). If 6 cannot be computed, use 7's colour. Logic: "debt is fine if it is used well (interest is easily covered)."

### Company type (Lynch) — applied in order

| Type | Rule |
|---|---|
| Cyclical (Döngüsel) | sector Energy or Materials, **or** the last 5 years contain both positive and negative operating income |
| Fast grower (Hızlı büyüyen) | revenue growth (metric 1) ≥ 15% |
| Unprofitable (Kârsız) | operating income positive in fewer than 4 of the last 5 years (Lynch would not call a loss-maker a "stalwart") |
| Stalwart (İstikrarlı dev) | metric 1 ≥ 5% |
| Slow grower (Yavaş büyüyen) | the rest (< 5%) |

### Deciding metrics and class rule

The class uses only the type's **deciding** metrics (a striker is judged by goals, a goalkeeper by saves). If a
non-deciding metric is ❌, the report card asks the AI "why?"; it does not change the class.

| Type | Deciding metrics |
|---|---|
| Stalwart | 2 · 3 · 4 · 5 |
| Fast grower | 1 · 9 · 2 · 10 · 8 |
| Slow grower | 2 · 4 · 5 · Debt · T |
| Cyclical | 4 · Debt · 8 |
| Unprofitable | 2 · 3 · 4 · 5 |

```text
BELİRSİZ (undetermined) = fewer than half of the deciding metrics could be computed (or the company is out of scope)
ZAYIF (weak)            = 2 or more deciding metrics are ❌
SAĞLAM (strong)         = none is ❌  AND  number of ✅ ≥ half of the deciding metrics
ORTA (medium)           = everything in between
Shrinking rule          = if metric 1 (3-year revenue growth) is negative, the company cannot be SAĞLAM → ORTA
```

**Out of scope (for now):** banks, insurers, real estate (REITs), companies with no revenue yet, utilities; turnarounds and
"asset plays". Payment companies such as Visa / Mastercard are in scope.

### Price line (not part of the class)

- **PEG** = P/E (Yahoo trailing P/E) ÷ (3-year CAGR of net income × 100). The trial used **net income** growth, not EPS
  growth. If there is no profit / profit is falling → "not computable". ≤ 1 attractive · 1–2 fair · > 2 expensive.
- **FCF yield** = last-year FCF ÷ market cap. ≥ 5% attractive · 2–5% fair · < 2% expensive.

### The 10 trial companies and the user's expectation

Coca-Cola (KO), Nvidia (NVDA), Nike (NKE), Starbucks (SBUX), Pfizer (PFE), Intel (INTC), Boeing (BA), Snap (SNAP),
Dow (DOW), Rivian (RIVN). 2 were expected to be strong, 8 medium / weak. The user's assessment of our results:
Coca-Cola ORTA is right (do not bend the rules for it), Nvidia SAĞLAM is right, Intel / Boeing / Snap / Dow / Rivian ZAYIF
are right; the user sees Nike / Starbucks / Pfizer as **weak** but accepts ORTA for now. Results in **Appendix A**, raw
figures in **Appendix B**, trial code in **Appendix C**.

### Known limitations and open questions (we want your view on these too)

1. The trial code is a **prototype**; figures have not yet been checked by hand against the 10-Ks (to be done in acceptance
   testing on at least 20 stocks).
2. **If capital expenditure is not found it is treated as 0** → FCF may be overstated.
3. In the 3-year FCF average a missing year counts as 0 (always divided by 3).
4. **Dow:** FCF over the last 3 years 2.8 → 0 → −1.4 billion USD; the average is positive, so metric 10 says "generates
   cash". Averaging smooths one-offs but can hide a deteriorating trend.
5. The return-on-capital denominator includes goodwill; it comes out low for acquisitive companies (Coca-Cola 13.8%).
6. The operating-income fallback (pre-tax income + interest) includes unusual items; the interest figure may be cash
   interest paid (InterestPaidNet).
7. Debt components may overlap; leases excluded.
8. **PEG:** Nvidia's net income grew ~202% a year over 3 years, so PEG comes out 0.15 (meaningless). Proposal: cap growth at
   25% (Lynch: faster growth does not last). Not decided yet.
9. **Stock-based compensation** is not deducted from FCF; Snap's FCF yield looks inflated. Proposal: deduct it. Not decided.
10. FCF yield uses last-year FCF; other metrics use the 3-year average. Should it be consistent?
11. Type thresholds (5% / 15%) use revenue growth; Lynch classified by earnings growth. Coca-Cola (3.7%) became a "slow
    grower" (Lynch would probably call it a stalwart).
12. Fiscal year ends differ (Nvidia January, Nike May, Starbucks September); comparisons are not aligned to calendar years.

### What we ask you to do

1. **Calculation check:** recompute the metrics in Appendix A from the raw figures in Appendix B (at least 4 companies,
   ideally all). List anything that does not match.
2. **Data check:** if you have access, compare the last-year figures of at least 3 companies (revenue, operating income,
   operating cash flow, capex, debt, share count) with the company's 10-K. Pay special attention to the **debt** total.
3. **Code check:** does the code in Appendix C contradict any rule above, or contain a bug?
4. **Rule logic:** are the thresholds, type rules, deciding metrics and class rule financially consistent? Anything that
   contradicts Buffett / Munger / Smith / Lynch? What **trap company types** could get the wrong class?
5. **Class results:** do you agree with each of the 10 classes? If not, **which rule** causes it and what general fix would
   you propose (bending a rule for a single company is "curve fitting"; propose a general rule).
6. **Open questions:** a short view on each of the 12 items above.
7. **Blind spots:** the 5 most important risks that could mislead the system.

### Answer format (in Turkish)

First fill in this table (one row per finding):

| # | Type (calculation / data / code / rule / class / missing) | Where (company, metric, line) | Issue | Evidence | Severity (high / medium / low) | Fix (simplest form) | How you know (source / recomputed / reasoning) |
|---|---|---|---|---|---|---|---|

Then:

- **10-company table:** company · our class · your class · short reason.
- **Open questions:** 1–3 sentences for each of 1–12.
- **Top 3 findings.**
- **Areas where you found no error** (e.g. "threshold table is consistent", "Coca-Cola calculations are correct").

### Glossary for the appendices (Turkish → English)

Classes: SAĞLAM = strong · ORTA = medium · ZAYIF = weak · BELİRSİZ = undetermined. Types: Hızlı büyüyen = fast grower ·
İstikrarlı dev = stalwart · Yavaş büyüyen = slow grower · Döngüsel = cyclical · Kârsız = unprofitable. In the code:
gelir = revenue · maliyet = cost of revenue · brut = gross profit · faal / faaliyet = operating income · vergi_oncesi / vo =
pre-tax income · vergi = income tax · net = net income · faiz = interest expense · isletme_nakit / on = operating cash flow ·
yatirim / yat = capex · nakit = cash · kv_yatirim = short-term investments · likit = liquid assets · ozkaynak / oz = equity ·
varlik = total assets · kv_yukumluluk / kvy_ = current liabilities · borc = debt · hisse = diluted share count ·
temettu / tem = dividends paid · fcf3 = 3-year average FCF · bolunme = split · ilk_10k = first 10-K fiscal year ·
renk = colour · tur = type · sinif = class · bel = deciding metrics · kuculme = shrinking rule · sert10 = stricter metric-10
thresholds. "nakit üretiyor" = generates cash · "nakit > borç" = cash > debt · "hesaplanamadı" / "—" = not computable ·
"puan" = percentage points.

### Appendix A — Results (output of the trial code)

**Bold** = deciding metric for that company's type. "—" = not computable. Colours: ✅ good · ➖ medium · ❌ weak · `·` not computable / none.

| Metric | Coca-Cola (KO) | Nvidia (NVDA) | Nike (NKE) | Starbucks (SBUX) | Pfizer (PFE) |
|---|---|---|---|---|---|
| 1. Revenue growth (3y) | ❌ +3.7% | **✅ +100.0%** | ❌ -3.2% | ❌ +4.9% | ❌ -14.8% |
| 2. Margin stability | **✅ +1.5 pt** | **✅ +2.9 pt** | **➖ -1.0 pt** | **❌ -6.2 pt** | **✅ +7.8 pt** |
| 3. Operating margin | ✅ 28.7% | ✅ 60.4% | ➖ 9.1% | ➖ 7.9% | ✅ 16.3% |
| 4. Return on capital (5y, ROCE) | **➖ 13.8%** | ✅ 76.0% | **✅ 25.5%** | **✅ 21.5%** | **➖ 12.0%** |
| 5. Cash conversion (3y) | **➖ 57.4%** | ✅ 82.9% | **✅ 100.3%** | **✅ 96.9%** | **✅ 132.3%** |
| 6. Interest coverage (×) | ✅ 8.3 | ✅ cash > debt | ✅ 13.1 | ➖ 5.4 | ➖ 3.8 |
| 7. Years to repay debt | ❌ 5.3 | ✅ cash > debt | ✅ 0.1 | ➖ 4.0 | ❌ 6.9 |
| 8. Share count (≤5y) | ✅ -0.2% | **✅ -2.3%** | ✅ -8.0% | ✅ -3.6% | ➖ +1.4% |
| 9. Gross-profit growth (3y) | ❌ +5.7% | **✅ +115.4%** | ❌ -3.7% | · — | ❌ -11.4% |
| 10. Cash runway (years) | ✅ generates cash | **✅ generates cash** | ✅ generates cash | ✅ generates cash | ✅ generates cash |
| Debt (6+7 combined) | **➖** | ✅ | **✅** | **➖** | **❌** |
| T. Dividend covered (5y) | **✅** | ✅ | **✅** | **✅** | **✅** |
| 3y avg FCF (bn USD) | 6.59 | 61.52 | 4.02 | 3.15 | 7.90 |
| **Type → Class** | Slow grower → **ORTA (medium)** | Fast grower → **SAĞLAM (strong)** | Slow grower → **ORTA (medium, shrinking rule)** | Slow grower → **ORTA (medium)** | Slow grower → **ORTA (medium)** |
| Price line | PEG 2.32 · FCF yield 1.4% | PEG 0.15 · FCF yield 1.7% | PEG not computable · FCF yield 4.3% | PEG not computable · FCF yield 2.3% | PEG not computable · FCF yield 5.7% |

| Metric | Intel (INTC) | Boeing (BA) | Snap (SNAP) | Dow (DOW) | Rivian (RIVN) |
|---|---|---|---|---|---|
| 1. Revenue growth (3y) | ❌ -5.7% | ➖ +10.3% | ➖ +8.8% | ❌ -11.1% | **✅ +48.1%** |
| 2. Margin stability | ❌ -6.3 pt | ✅ +0.4 pt | **➖ -1.2 pt** | ❌ -6.2 pt | **✅ +222.9 pt** |
| 3. Operating margin | ❌ -4.2% | ❌ 4.8% | **❌ -9.0%** | ❌ -4.1% | ❌ -66.5% |
| 4. Return on capital (5y, ROCE) | **❌ 2.1%** | **❌ -6.2%** | **❌ -24.3%** | **❌ 6.1%** | ❌ -94.4% |
| 5. Cash conversion (3y) | · — | · — | **· —** | · — | · — |
| 6. Interest coverage (×) | ❌ -2.0 | ❌ 1.5 | ❌ -4.4 | ❌ -1.9 | ✅ cash > debt |
| 7. Years to repay debt | ❌ no cash generation, has debt | ❌ no cash generation, has debt | ✅ 2.8 | ❌ 31.3 | ✅ cash > debt |
| 8. Share count (≤5y) | **➖ +7.0%** | **❌ +34.1%** | ❌ +16.4% | **✅ -4.1%** | **❌ +29.9%** |
| 9. Gross-profit growth (3y) | ❌ -11.9% | ❌ +6.7% | ❌ +5.4% | ❌ -33.4% | **➖ just turned to profit** |
| 10. Cash runway (years) | ✅ 3.2 | ✅ 7.5 | ✅ generates cash | ✅ generates cash | **❌ 1.6** |
| Debt (6+7 combined) | **❌** | **❌** | ❌ | **❌** | ✅ |
| T. Dividend covered (5y) | ❌ | ❌ | · | ✅ | · |
| 3y avg FCF (bn USD) | -11.63 | -3.92 | 0.23 | 0.46 | -3.75 |
| **Type → Class** | Cyclical → **ZAYIF (weak)** | Cyclical → **ZAYIF (weak)** | Unprofitable → **ZAYIF (weak)** | Cyclical → **ZAYIF (weak)** | Fast grower → **ZAYIF (weak)** |
| Price line | PEG not computable · FCF yield -0.8% | PEG not computable · FCF yield -1.2% | PEG not computable · FCF yield 4.6% | PEG not computable · FCF yield -7.2% | PEG not computable · FCF yield -12.0% |

### Appendix B — Raw figures (SEC; billion USD; share count in millions, **before** split adjustment)

Columns are fiscal-year-end dates (yyyy-mm). "—" = not found by the synonym list.

#### Coca-Cola (KO) — fiscal year ends: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · type: Slow grower · class: ORTA (medium)

| Item (bn USD) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Revenue | 33.01 | 38.66 | 43.00 | 45.75 | 47.06 | 47.94 |
| Gross profit (reported or revenue − cost) | 19.58 | 23.30 | 25.00 | 27.23 | 28.74 | 29.54 |
| Operating income | 9.00 | 10.31 | 10.91 | 11.31 | 9.99 | 13.76 |
| Pre-tax income | 9.75 | 12.43 | 11.69 | 12.95 | 13.09 | 16.00 |
| Interest expense | 1.44 | 1.60 | 0.88 | 1.53 | 1.66 | 1.65 |
| Net income | 7.75 | 9.77 | 9.54 | 10.71 | 10.63 | 13.11 |
| Operating cash flow | 9.84 | 12.62 | 11.02 | 11.60 | 6.80 | 7.41 |
| Capex | 1.18 | 1.37 | 1.48 | 1.85 | 2.06 | 2.11 |
| Free cash flow | 8.67 | 11.26 | 9.53 | 9.75 | 4.74 | 5.30 |
| Cash + short-term investments | 9.14 | 9.68 | 9.52 | 9.37 | 10.83 | 10.27 |
| Total assets | 87.30 | 94.35 | 92.76 | 97.70 | 100.55 | 104.82 |
| Current liabilities | 14.60 | 19.95 | 19.72 | 23.57 | 25.25 | 21.28 |
| Equity | 19.30 | 23.00 | 24.11 | 25.94 | 24.86 | 32.17 |
| Debt (total) | 44.12 | 45.22 | 41.30 | 41.72 | 44.16 | 45.44 |
| Dividends paid | 7.05 | 7.25 | 7.62 | 7.95 | 8.36 | 8.78 |
| Diluted weighted-avg shares (millions, raw) | 4,323 | 4,340 | 4,350 | 4,339 | 4,320 | 4,313 |

Last-year debt source (XBRL names): LongTermDebtAndCapitalLeaseObligations, LongTermDebtAndCapitalLeaseObligationsCurrent, CommercialPaper · operating income source: OperatingIncomeLoss

#### Nvidia (NVDA) — fiscal year ends: 2021-01-31, 2022-01-30, 2023-01-29, 2024-01-28, 2025-01-26, 2026-01-25 · type: Fast grower · class: SAĞLAM (strong)

| Item (bn USD) | 2021-01 | 2022-01 | 2023-01 | 2024-01 | 2025-01 | 2026-01 |
|---|---|---|---|---|---|---|
| Revenue | 16.68 | 26.91 | 26.97 | 60.92 | 130.50 | 215.94 |
| Gross profit (reported or revenue − cost) | 10.40 | 17.48 | 15.36 | 44.30 | 97.86 | 153.46 |
| Operating income | 4.53 | 10.04 | 4.22 | 32.97 | 81.45 | 130.39 |
| Pre-tax income | 4.41 | 9.94 | 4.18 | 33.82 | 84.03 | 141.45 |
| Interest expense | 0.18 | 0.24 | 0.26 | 0.26 | 0.25 | 0.26 |
| Net income | 4.33 | 9.75 | 4.37 | 29.76 | 72.88 | 120.07 |
| Operating cash flow | 5.82 | 9.11 | 5.64 | 28.09 | 64.09 | 102.72 |
| Capex | — | 0.98 | 1.83 | 1.07 | 3.24 | 6.04 |
| Free cash flow | 5.82 | 8.13 | 3.81 | 27.02 | 60.85 | 96.68 |
| Cash + short-term investments | 11.56 | 21.21 | 13.30 | 25.98 | 43.21 | 10.61 |
| Total assets | 28.79 | 44.19 | 41.18 | 65.73 | 111.60 | 206.80 |
| Current liabilities | 3.92 | 4.33 | 6.56 | 10.63 | 18.05 | 32.16 |
| Equity | 16.89 | 26.61 | 22.10 | 42.98 | 79.33 | 157.29 |
| Debt (total) | 6.96 | 10.95 | 10.95 | 9.71 | 8.46 | 8.47 |
| Dividends paid | 0.40 | 0.40 | 0.40 | 0.40 | 0.83 | 0.97 |
| Diluted weighted-avg shares (millions, raw) | 2,510 | 2,535 | 25,070 | 24,940 | 24,804 | 24,514 |

Last-year debt source (XBRL names): LongTermDebt · operating income source: OperatingIncomeLoss · shares: split adjusted (×10)

#### Nike (NKE) — fiscal year ends: 2021-05-31, 2022-05-31, 2023-05-31, 2024-05-31, 2025-05-31, 2026-05-31 · type: Slow grower · class: ORTA (medium, shrinking rule)

| Item (bn USD) | 2021-05 | 2022-05 | 2023-05 | 2024-05 | 2025-05 | 2026-05 |
|---|---|---|---|---|---|---|
| Revenue | 44.54 | 46.71 | 51.22 | 51.36 | 46.31 | 46.40 |
| Gross profit (reported or revenue − cost) | 19.96 | 21.48 | 22.29 | 22.89 | 19.79 | 19.91 |
| Operating income | 6.95 | 6.94 | 6.55 | 7.08 | 4.27 | 4.22 |
| Pre-tax income | 6.66 | 6.65 | 6.20 | 6.70 | 3.88 | 3.90 |
| Interest expense | 0.29 | 0.29 | 0.35 | 0.38 | 0.39 | 0.32 |
| Net income | 5.73 | 6.05 | 5.07 | 5.70 | 3.22 | 3.11 |
| Operating cash flow | 6.66 | 5.19 | 5.84 | 7.43 | 3.70 | 2.87 |
| Capex | 0.69 | 0.76 | 0.97 | 0.81 | 0.43 | 0.68 |
| Free cash flow | 5.96 | 4.43 | 4.87 | 6.62 | 3.27 | 2.18 |
| Cash + short-term investments | 13.48 | 8.57 | 7.44 | 9.86 | 7.46 | 7.56 |
| Total assets | 37.74 | 40.32 | 37.53 | 38.11 | 36.58 | 38.41 |
| Current liabilities | 9.67 | 10.73 | 9.26 | 10.59 | 10.57 | 12.55 |
| Equity | 12.77 | 15.28 | 14.00 | 14.43 | 13.21 | 14.87 |
| Debt (total) | 9.41 | 9.43 | 8.93 | 8.91 | 7.97 | 7.94 |
| Dividends paid | 1.64 | 1.84 | 2.01 | 2.17 | 2.30 | 2.41 |
| Diluted weighted-avg shares (millions, raw) | 1,609 | 1,611 | 1,570 | 1,530 | 1,488 | 1,481 |

Last-year debt source (XBRL names): LongTermDebt · operating income source: approx.: pre-tax income + interest

#### Starbucks (SBUX) — fiscal year ends: 2020-09-27, 2021-10-03, 2022-10-02, 2023-10-01, 2024-09-29, 2025-09-28 · type: Slow grower · class: ORTA (medium)

| Item (bn USD) | 2020-09 | 2021-10 | 2022-10 | 2023-10 | 2024-09 | 2025-09 |
|---|---|---|---|---|---|---|
| Revenue | 23.52 | 29.06 | 32.25 | 35.98 | 36.18 | 37.18 |
| Gross profit (reported or revenue − cost) | — | — | — | — | — | — |
| Operating income | 1.56 | 4.87 | 4.62 | 5.87 | 5.41 | 2.94 |
| Pre-tax income | 1.16 | 5.36 | 4.23 | 5.40 | 4.97 | 2.51 |
| Interest expense | 0.44 | 0.47 | 0.48 | 0.55 | 0.56 | 0.54 |
| Net income | 0.93 | 4.20 | 3.28 | 4.12 | 3.76 | 1.86 |
| Operating cash flow | 1.60 | 5.99 | 4.40 | 6.01 | 6.10 | 4.75 |
| Capex | 1.48 | 1.47 | 1.84 | 2.33 | 2.78 | 2.31 |
| Free cash flow | 0.11 | 4.52 | 2.56 | 3.68 | 3.32 | 2.44 |
| Cash + short-term investments | 4.63 | 6.62 | 3.18 | 3.95 | 3.54 | 3.47 |
| Total assets | 29.37 | 31.39 | 27.98 | 29.45 | 31.34 | 32.02 |
| Current liabilities | 7.35 | 8.15 | 9.15 | 9.35 | 9.07 | 10.21 |
| Equity | -7.81 | -5.32 | -8.71 | -7.99 | -7.45 | -8.10 |
| Debt (total) | 16.35 | 14.62 | 15.04 | 15.40 | 15.57 | 16.07 |
| Dividends paid | 1.92 | 2.12 | 2.26 | 2.43 | 2.58 | 2.77 |
| Diluted weighted-avg shares (millions, raw) | 1,182 | 1,186 | 1,158 | 1,151 | 1,137 | 1,140 |

Last-year debt source (XBRL names): LongTermDebt · operating income source: OperatingIncomeLoss

#### Pfizer (PFE) — fiscal year ends: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · type: Slow grower · class: ORTA (medium)

| Item (bn USD) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Revenue | 41.65 | 81.29 | 101.17 | 59.55 | 63.63 | 62.58 |
| Gross profit (reported or revenue − cost) | 33.17 | 50.47 | 66.83 | 34.60 | 45.78 | 46.51 |
| Operating income | 8.48 | 25.60 | 35.97 | 3.27 | 11.11 | 10.19 |
| Pre-tax income | 7.04 | 24.31 | 34.73 | 1.06 | 8.02 | 7.52 |
| Interest expense | 1.45 | 1.29 | 1.24 | 2.21 | 3.09 | 2.67 |
| Net income | 9.16 | 21.98 | 31.37 | 2.12 | 8.03 | 7.77 |
| Operating cash flow | 14.40 | 32.58 | 29.27 | 8.70 | 12.74 | 11.70 |
| Capex | 2.23 | 2.71 | 3.24 | 3.91 | 2.91 | 2.63 |
| Free cash flow | 12.18 | 29.87 | 26.03 | 4.79 | 9.84 | 9.07 |
| Cash + short-term investments | 11.49 | 23.96 | 19.16 | 7.25 | 11.92 | 10.32 |
| Total assets | 154.23 | 181.48 | 197.21 | 226.50 | 213.40 | 208.16 |
| Current liabilities | 25.92 | 42.67 | 42.14 | 47.79 | 42.99 | 36.98 |
| Equity | 63.24 | 77.20 | 95.66 | 89.01 | 88.20 | 86.48 |
| Debt (total) | 4.56 | 37.83 | 35.44 | 71.76 | 63.60 | 64.64 |
| Dividends paid | 8.44 | 8.73 | 8.98 | 9.25 | 9.51 | 9.77 |
| Diluted weighted-avg shares (millions, raw) | 5,632 | 5,708 | 5,733 | 5,709 | 5,700 | 5,713 |

Last-year debt source (XBRL names): LongTermDebtNoncurrent, LongTermDebtCurrent · operating income source: approx.: pre-tax income + interest

#### Intel (INTC) — fiscal year ends: 2020-12-26, 2021-12-25, 2022-12-31, 2023-12-30, 2024-12-28, 2025-12-27 · type: Cyclical · class: ZAYIF (weak)

| Item (bn USD) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Revenue | 77.87 | 79.02 | 63.05 | 54.23 | 53.10 | 52.85 |
| Gross profit (reported or revenue − cost) | 43.61 | 43.81 | 26.87 | 21.71 | 17.34 | 18.38 |
| Operating income | 23.68 | 19.46 | 2.33 | 0.09 | -11.68 | -2.21 |
| Pre-tax income | 25.08 | 21.70 | 7.77 | 0.76 | -11.21 | 1.56 |
| Interest expense | 0.63 | 0.60 | 0.50 | 0.88 | 1.03 | 1.09 |
| Net income | 20.90 | 19.87 | 8.01 | 1.69 | -18.76 | -0.27 |
| Operating cash flow | 35.86 | 29.46 | 15.43 | 11.47 | 8.29 | 9.70 |
| Capex | 14.26 | 18.73 | 24.84 | 25.75 | 23.94 | 14.65 |
| Free cash flow | 21.61 | 10.72 | -9.41 | -14.28 | -15.66 | -4.95 |
| Cash + short-term investments | 8.16 | 29.25 | 28.34 | 25.03 | 22.06 | 37.42 |
| Total assets | 153.09 | 168.41 | 182.10 | 191.57 | 196.49 | 211.43 |
| Current liabilities | 24.75 | 27.46 | 32.16 | 28.05 | 35.67 | 31.57 |
| Equity | 81.04 | 95.39 | 101.42 | 105.59 | 99.27 | 114.28 |
| Debt (total) | 36.40 | 38.10 | 42.01 | 49.27 | 50.01 | 46.59 |
| Dividends paid | 5.57 | 5.64 | 6.00 | 3.09 | 1.60 | 0.00 |
| Diluted weighted-avg shares (millions, raw) | 4,232 | 4,090 | 4,123 | 4,212 | 4,280 | 4,530 |

Last-year debt source (XBRL names): LongTermDebt · operating income source: OperatingIncomeLoss

#### Boeing (BA) — fiscal year ends: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · type: Cyclical · class: ZAYIF (weak)

| Item (bn USD) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Revenue | 58.16 | 62.29 | 66.61 | 77.79 | 66.52 | 89.46 |
| Gross profit (reported or revenue − cost) | -5.68 | 3.05 | 3.53 | 7.72 | -1.99 | 4.29 |
| Operating income | -12.77 | -2.87 | -3.52 | -0.77 | -10.71 | 4.28 |
| Pre-tax income | -14.48 | -5.03 | -5.02 | -2.00 | -12.21 | 2.63 |
| Interest expense | 2.16 | 2.71 | 2.56 | 2.46 | 2.73 | 2.77 |
| Net income | -11.87 | -4.20 | -4.93 | -2.22 | -11.82 | 2.23 |
| Operating cash flow | -18.41 | -3.42 | 3.51 | 5.96 | -12.08 | 1.06 |
| Capex | 1.30 | 0.98 | 1.22 | 1.53 | 2.23 | 2.94 |
| Free cash flow | -19.71 | -4.40 | 2.29 | 4.43 | -14.31 | -1.88 |
| Cash + short-term investments | 25.59 | 16.24 | 17.22 | 15.96 | 26.28 | 29.40 |
| Total assets | 152.14 | 138.55 | 137.10 | 137.01 | 156.36 | 168.24 |
| Current liabilities | 87.28 | 81.99 | 90.05 | 95.83 | 97.08 | 108.11 |
| Equity | -18.32 | -15.00 | -15.88 | -17.23 | -3.91 | 5.45 |
| Debt (total) | 63.38 | 57.92 | 56.79 | 52.05 | 53.62 | 53.85 |
| Dividends paid | 1.16 | — | — | — | — | 0.33 |
| Diluted weighted-avg shares (millions, raw) | 569 | 588 | 595 | 606 | 647 | 762 |

Last-year debt source (XBRL names): LongTermDebt · operating income source: OperatingIncomeLoss

#### Snap (SNAP) — fiscal year ends: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · type: Unprofitable · class: ZAYIF (weak)

| Item (bn USD) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Revenue | 2.51 | 4.12 | 4.60 | 4.61 | 5.36 | 5.93 |
| Gross profit (reported or revenue − cost) | 1.32 | 2.37 | 2.79 | 2.49 | 2.89 | 3.26 |
| Operating income | -0.86 | -0.70 | -1.40 | -1.40 | -0.79 | -0.53 |
| Pre-tax income | -0.93 | -0.47 | -1.40 | -1.29 | -0.67 | -0.45 |
| Interest expense | 0.10 | 0.02 | 0.02 | 0.02 | 0.02 | 0.12 |
| Net income | -0.94 | -0.49 | -1.43 | -1.32 | -0.70 | -0.46 |
| Operating cash flow | -0.17 | 0.29 | 0.18 | 0.25 | 0.41 | 0.66 |
| Capex | 0.06 | 0.07 | 0.13 | 0.21 | 0.19 | 0.22 |
| Free cash flow | -0.23 | 0.22 | 0.06 | 0.03 | 0.22 | 0.44 |
| Cash + short-term investments | 2.54 | 3.69 | 3.94 | 3.54 | 3.38 | 2.94 |
| Total assets | 5.02 | 7.54 | 8.03 | 7.97 | 7.94 | 7.68 |
| Current liabilities | 0.67 | 0.85 | 1.22 | 1.13 | 1.24 | 1.29 |
| Equity | 2.33 | 3.79 | 2.58 | 2.41 | 2.45 | 2.28 |
| Debt (total) | 1.68 | 2.25 | 3.74 | 3.75 | 3.68 | 3.58 |
| Dividends paid | — | — | — | — | — | — |
| Diluted weighted-avg shares (millions, raw) | 1,456 | 1,559 | 1,608 | 1,613 | 1,659 | 1,695 |

Last-year debt source (XBRL names): LongTermDebt, ShortTermBorrowings · operating income source: OperatingIncomeLoss

#### Dow (DOW) — fiscal year ends: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · type: Cyclical · class: ZAYIF (weak)

| Item (bn USD) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Revenue | 38.54 | 54.97 | 56.90 | 44.62 | 42.96 | 39.97 |
| Gross profit (reported or revenue − cost) | 5.20 | 10.78 | 8.56 | 4.88 | 4.61 | 2.53 |
| Operating income | 2.90 | 8.88 | 6.75 | 1.40 | 2.41 | -1.65 |
| Pre-tax income | 2.07 | 8.14 | 6.09 | 0.66 | 1.60 | -2.51 |
| Interest expense | 0.83 | 0.73 | 0.66 | 0.75 | 0.81 | 0.86 |
| Net income | — | — | — | — | — | — |
| Operating cash flow | 6.23 | 7.01 | 7.47 | 5.20 | 2.91 | 1.03 |
| Capex | 1.25 | 1.50 | 1.82 | 2.36 | 2.94 | 2.48 |
| Free cash flow | 4.97 | 5.51 | 5.65 | 2.84 | -0.03 | -1.45 |
| Cash + short-term investments | 5.10 | 2.99 | 3.89 | 2.99 | 2.19 | 3.82 |
| Total assets | 61.47 | 62.99 | 60.60 | 57.97 | 57.31 | 58.54 |
| Current liabilities | 11.11 | 13.23 | 11.33 | 9.96 | 10.29 | 9.18 |
| Equity | 12.44 | 18.16 | 20.72 | 18.61 | 17.36 | 16.01 |
| Debt (total) | 17.11 | 14.67 | 15.42 | 15.09 | 16.21 | 18.07 |
| Dividends paid | 2.07 | 2.07 | 2.01 | 1.97 | 1.97 | 1.49 |
| Diluted weighted-avg shares (millions, raw) | 742 | 749 | 726 | 709 | 705 | 712 |

Last-year debt source (XBRL names): LongTermDebtAndCapitalLeaseObligations, LongTermDebtAndCapitalLeaseObligationsCurrent · operating income source: approx.: pre-tax income + interest

#### Rivian (RIVN) — fiscal year ends: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · type: Fast grower · class: ZAYIF (weak)

| Item (bn USD) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Revenue | 0.00 | 0.06 | 1.66 | 4.43 | 4.97 | 5.39 |
| Gross profit (reported or revenue − cost) | 0.00 | -0.47 | -3.12 | -2.03 | -1.20 | 0.14 |
| Operating income | -1.02 | -4.22 | -6.86 | -5.74 | -4.69 | -3.58 |
| Pre-tax income | -1.02 | -4.69 | -6.75 | -5.43 | -4.74 | -3.62 |
| Interest expense | 0.01 | 0.03 | 0.10 | 0.22 | 0.32 | 0.27 |
| Net income | -1.02 | -4.69 | -6.75 | -5.43 | -4.75 | -3.65 |
| Operating cash flow | -0.85 | -2.62 | -5.05 | -4.87 | -1.72 | -0.78 |
| Capex | 0.91 | 1.79 | 1.37 | 1.03 | 1.14 | 1.71 |
| Free cash flow | -1.76 | -4.42 | -6.42 | -5.89 | -2.86 | -2.49 |
| Cash + short-term investments | 2.98 | 18.13 | 11.57 | 9.37 | 7.70 | 6.08 |
| Total assets | 4.60 | 22.29 | 17.88 | 16.78 | 15.41 | 14.86 |
| Current liabilities | 0.61 | 1.31 | 2.42 | 2.49 | 2.25 | 3.69 |
| Equity | -1.38 | 19.51 | 13.80 | 9.14 | 6.56 | 4.59 |
| Debt (total) | 0.07 | 1.23 | 1.23 | 4.43 | 4.44 | 4.44 |
| Dividends paid | — | — | — | — | — | — |
| Diluted weighted-avg shares (millions, raw) | 101 | 204 | 913 | 947 | 1,013 | 1,186 |

Last-year debt source (XBRL names): LongTermDebtNoncurrent · operating income source: OperatingIncomeLoss

### Appendix C — Trial code (Python, prototype; identifiers are Turkish — see the glossary above)

`karne_deneme.py` — metrics, type, class:

```python
"""Deneme: 10 ölçü + tür + sınıf kuralı, gerçek SEC verisiyle. Projeye ait değil (scratchpad)."""
import json, sys
from datetime import date

SEKTOR = {"KO": "Zorunlu tüketim", "NVDA": "Bilgi teknolojisi", "NKE": "Zorunlu olmayan tüketim",
          "SBUX": "Zorunlu olmayan tüketim", "PFE": "Sağlık", "INTC": "Bilgi teknolojisi", "BA": "Sanayi",
          "SNAP": "İletişim hizmetleri", "DOW": "Malzeme", "RIVN": "Zorunlu olmayan tüketim"}

ES = {  # eş anlamlılar listeleri
    "gelir": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
              "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "maliyet": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "brut": ["GrossProfit"],
    "faaliyet": ["OperatingIncomeLoss"],
    "vergi_oncesi": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                     "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "vergi": ["IncomeTaxExpenseBenefit"],
    "net": ["NetIncomeLoss"],
    "faiz": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense", "InterestPaidNet"],
    "isletme_nakit": ["NetCashProvidedByUsedInOperatingActivities"],
    "yatirim": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "nakit": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "kv_yatirim": ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "ozkaynak": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "hisse": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "temettu": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock", "PaymentsOfOrdinaryDividends"],
    "varlik": ["Assets"], "kv_yukumluluk": ["LiabilitiesCurrent"],
    "hbk": ["EarningsPerShareDiluted"],
}
BORC_UV = [["LongTermDebt"], ["LongTermDebtNoncurrent", "LongTermDebtCurrent"],
           ["LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent"],
           ["ConvertibleDebtNoncurrent", "ConvertibleDebtCurrent", "ConvertibleNotesPayable", "LongTermNotesPayable"]]
BORC_KV = ["CommercialPaper", "ShortTermBorrowings"]


def d(s): return date.fromisoformat(s)


class Sirket:
    def __init__(self, t):
        self.t = t
        self.f = json.load(open(f"{t}.json"))["facts"].get("us-gaap", {})
        self.yil_sonu = self._yil_sonlari()

    def _sure(self, tag, unit="USD"):
        """Yıllık (≈1 yıl) dönem değerleri: {bitiş tarihi: değer}, en son dosyalanan kazanır."""
        out = {}
        for x in self.f.get(tag, {}).get("units", {}).get(unit, []):
            if x.get("form") not in ("10-K", "10-K/A") or "start" not in x: continue
            gun = (d(x["end"]) - d(x["start"])).days
            if 350 <= gun <= 380:
                if x["end"] not in out or x["filed"] > out[x["end"]][1]:
                    out[x["end"]] = (x["val"], x["filed"])
        return {k: v[0] for k, v in out.items()}

    def _an(self, tag, unit="USD"):
        out = {}
        for x in self.f.get(tag, {}).get("units", {}).get(unit, []):
            if x.get("form") not in ("10-K", "10-K/A") or "start" in x: continue
            if x["end"] not in out or x["filed"] > out[x["end"]][1]:
                out[x["end"]] = (x["val"], x["filed"])
        return {k: v[0] for k, v in out.items()}

    def _yil_sonlari(self):
        ends = set()
        for tg in ES["gelir"] + ES["faaliyet"]:
            ends |= set(self._sure(tg))
        return sorted(ends)[-6:]  # son 6 mali yıl

    def seri(self, kavram, unit="USD", anlik=False):
        """Her yıl için eş anlamlıları SIRAYLA dene; ilk bulunan. {yıl_sonu: (değer, isim)}"""
        tablolar = [(tg, (self._an if anlik else self._sure)(tg, unit)) for tg in ES[kavram]]
        out = {}
        for e in self.yil_sonu:
            for tg, tb in tablolar:
                if e in tb:
                    out[e] = (tb[e], tg); break
        return out

    def borc(self):
        out = {}
        for e in self.yil_sonu:
            parca, kaynak = 0.0, []
            for grup in BORC_UV:
                vals = [(tg, self._an(tg).get(e)) for tg in grup]
                vals = [(tg, v) for tg, v in vals if v is not None]
                if vals:
                    parca += sum(v for _, v in vals); kaynak += [tg for tg, _ in vals]; break
            for tg in BORC_KV:
                v = self._an(tg).get(e)
                if v: parca += v; kaynak.append(tg)
            out[e] = (parca, kaynak)
        return out


def cagr(a, b, n):
    if a is None or b is None or a <= 0 or b <= 0 or n <= 0: return None
    return (b / a) ** (1 / n) - 1


def renk(v, iyi, orta, ters=False):
    """iyi/orta eşikleri; ters=True ise küçük olan iyidir."""
    if v is None: return "·"
    if not ters: return "✅" if v >= iyi else ("➖" if v >= orta else "❌")
    return "✅" if v <= iyi else ("➖" if v <= orta else "❌")


def analiz(t, fiyat=None):
    s = Sirket(t)
    Y = s.yil_sonu
    g = lambda k, **kw: {e: v[0] for e, v in s.seri(k, **kw).items()}
    gelir, maliyet, brut = g("gelir"), g("maliyet"), g("brut")
    faal, vo, vergi, net = g("faaliyet"), g("vergi_oncesi"), g("vergi"), g("net")
    faiz_s = s.seri("faiz"); faiz = {e: v[0] for e, v in faiz_s.items()}
    on, yat = g("isletme_nakit"), g("yatirim")
    nakit, kvy, oz = g("nakit", anlik=True), g("kv_yatirim", anlik=True), g("ozkaynak", anlik=True)
    hisse = g("hisse", unit="shares"); tem = g("temettu"); hbk = g("hbk", unit="USD/shares")
    borc = s.borc()
    for e in Y:  # brüt kâr yoksa gelir − maliyet
        if e not in brut and e in gelir and e in maliyet: brut[e] = gelir[e] - maliyet[e]
    faal_kaynak = {}
    for e in Y:
        if e in faal: faal_kaynak[e] = "OperatingIncomeLoss"
        elif e in vo:
            faal[e] = vo[e] + (faiz.get(e) or 0); faal_kaynak[e] = "yaklaşık: vergi öncesi kâr + faiz"
    fcf = {e: on[e] - yat.get(e, 0) for e in Y if e in on}
    fcf3 = sum(fcf.get(e, 0) for e in Y[-3:]) / 3
    varlik, kvy_ = g("varlik", anlik=True), g("kv_yukumluluk", anlik=True)
    # hisse sayısı: ilk 10-K yılı atla (halka arz), tam kat sıçrama = bölünme → düzelt
    ilk_10k = min(x["fy"] for v in s.f.values() for u in v["units"].values() for x in u if x.get("form") == "10-K" and x.get("fy"))
    hy = [e for e in Y if e in hisse and int(e[:4]) > ilk_10k] if int(Y[0][:4]) <= ilk_10k else [e for e in Y if e in hisse]
    hy = hy[-6:]
    duz = dict(hisse); bolunme = []
    for a, b in zip(hy, hy[1:]):
        r = duz[b] / duz[a]
        for k in (2, 3, 4, 5, 8, 10, 20):
            if abs(r - k) / k < 0.06:
                for e in hy[:hy.index(b)]: duz[e] *= k
                bolunme.append(f"bölünme düzeltildi (×{k})"); break
    hisse_ilk = hy[0] if hy else None
    likit = {e: nakit.get(e, 0) + kvy.get(e, 0) for e in Y}
    son = Y[-1]
    i3 = Y[-4] if len(Y) >= 4 else Y[0]
    i5 = Y[-6] if len(Y) >= 6 else Y[0]
    n3 = len(Y[Y.index(i3):]) - 1; n5 = len(Y[Y.index(i5):]) - 1

    M, A = {}, {}  # ölçü değeri, açıklama
    # 1 gelir büyümesi (3 yıl)
    M[1] = cagr(gelir.get(i3), gelir.get(son), n3)
    # 2 brüt marj istikrarı (son yıl − 5 yıl ort.), yoksa faaliyet marjı
    gm = {e: brut[e] / gelir[e] for e in Y if e in brut and e in gelir and gelir[e]}
    taban, adi = (gm, "brüt") if len(gm) >= 3 else ({e: faal[e] / gelir[e] for e in Y if e in faal and e in gelir and gelir[e]}, "faaliyet")
    son5 = [taban[e] for e in Y[-5:] if e in taban]
    M[2] = (taban[son] - sum(son5) / len(son5)) * 100 if son in taban and son5 else None
    A[2] = f"{adi} marj {taban.get(son, 0)*100:.1f}% (5y ort {sum(son5)/len(son5)*100:.1f}%)" if son5 else ""
    # 3 faaliyet marjı
    M[3] = faal[son] / gelir[son] if son in faal and son in gelir else None
    # 4 sermaye getirisi (5 yıl ort.)
    roics = []
    for e in Y[-5:]:
        if e not in faal: continue
        vo_e, vg = vo.get(e), vergi.get(e)
        vr = min(max(vg / vo_e, 0), 0.35) if vo_e and vo_e > 0 and vg is not None else 0.21
        if e not in varlik or e not in kvy_: continue
        ic = varlik[e] - kvy_[e] - likit[e]
        if ic > 0: roics.append(faal[e] * (1 - vr) / ic)
    M[4] = sum(roics) / len(roics) if len(roics) >= 3 else None
    A[4] = f"{len(roics)} yıl"
    # 5 nakde dönüşüm (3 yıl)
    ny = Y[-3:]
    sn, sf = sum(net.get(e, 0) for e in ny), sum(fcf.get(e, 0) for e in ny)
    M[5] = sf / sn if sn > 0 else None
    A[5] = "net kâr ≤ 0 → anlamsız" if sn <= 0 else ""
    # 6 faiz karşılama
    net_nakit = likit[son] >= borc[son][0]
    if net_nakit: M[6], A[6] = "NN", "nakit > borç"
    elif faiz.get(son) and son in faal: M[6], A[6] = faal[son] / faiz[son], faiz_s[son][1]
    else: M[6], A[6] = None, "faiz bulunamadı"
    # 7 borcu kaç yılda öder
    nb = borc[son][0] - likit[son]
    if nb <= 0: M[7] = "NN"
    elif fcf3 <= 0: M[7] = "FCF-"
    else: M[7] = nb / fcf3
    A[7] = "+".join(borc[son][1]) or "borç ismi yok"
    # 8 hisse sayısı (5 yıl)
    M[8] = duz[son] / duz[hisse_ilk] - 1 if son in duz and hisse_ilk else None
    A[8] = f"{son[:4] if False else ''}{hisse_ilk[:4] if hisse_ilk else ''}→{son[:4]} " + ", ".join(bolunme)
    # 9 brüt kâr büyümesi (3 yıl)
    M[9] = cagr(brut.get(i3), brut.get(son), n3)
    if M[9] is None and brut.get(i3) is not None and brut.get(i3) <= 0 < brut.get(son, 0): M[9] = 'POZ'; A[9] = 'zarardan kâra döndü (yeni)'
    # 10 nakit kaç yıl yeter
    M[10] = "FCF+" if fcf3 >= 0 else likit[son] / -fcf3

    sek = SEKTOR[t]
    oi5 = [faal[e] for e in Y[-5:] if e in faal]
    kar_yili = sum(1 for v in oi5 if v > 0)
    dongusel = sek in ("Enerji", "Malzeme") or (any(v > 0 for v in oi5) and any(v < 0 for v in oi5))
    if dongusel: tur = "Döngüsel"
    elif M[1] is not None and M[1] >= .15: tur = "Hızlı büyüyen"
    elif kar_yili < 4: tur = "Kârsız"
    elif M[1] is not None and M[1] >= .05: tur = "İstikrarlı dev"
    else: tur = "Yavaş büyüyen"
    sert10 = tur == "Hızlı büyüyen" and fcf3 < 0
    R = {  # renkler
        1: renk(M[1], .15, .08), 2: renk(M[2], -1, -3),
        3: renk(M[3], .15, .05), 4: renk(M[4], .15, .08), 5: renk(M[5], .80, .50),
        6: "✅" if M[6] == "NN" else renk(M[6], 8, 3),
        7: "✅" if M[7] == "NN" else ("❌" if M[7] == "FCF-" else renk(M[7], 3, 5, ters=True)),
        8: renk(M[8], 0, .10, ters=True), 9: '➖' if M[9] == 'POZ' else renk(M[9], .20, .10),
        10: "✅" if M[10] == "FCF+" else (renk(M[10], 5, 3) if sert10 else renk(M[10], 3, 1.5)),
    }
    # temettü karşılama (3 yıl)
    y5 = Y[-5:]
    st = sum(tem.get(e, 0) for e in y5); sf5 = sum(fcf.get(e, 0) for e in y5)
    tem_r = "·" if st == 0 else ("✅" if sf5 >= st else "❌")
    # Borç (6+7 birleşik): faiz karşılamanın rengi; borç yılı ❌ ise bir basamak düşür
    sira = ["❌", "➖", "✅"]
    b6, b7 = R[6], R[7]
    borc_r = b6 if b6 != "·" else b7
    if borc_r != "·" and b7 == "❌" and b6 != "·": borc_r = sira[max(sira.index(borc_r) - 1, 0)]

    bel = {"İstikrarlı dev": [2, 3, 4, 5], "Hızlı büyüyen": [1, 9, 2, 10, 8],
           "Yavaş büyüyen": [2, 4, 5, "B", "T"], "Döngüsel": [4, "B", 8], "Kârsız": [2, 3, 4, 5]}[tur]
    br = [tem_r if b == "T" else (borc_r if b == "B" else R[b]) for b in bel]
    hesap = [x for x in br if x != "·"]
    kirmizi, yesil = br.count("❌"), br.count("✅")
    if len(hesap) * 2 < len(br): sinif = "BELİRSİZ"
    elif kirmizi >= 2: sinif = "ZAYIF"
    elif kirmizi == 0 and yesil * 2 >= len(br): sinif = "SAĞLAM"
    else: sinif = "ORTA"
    # küçülme kuralı: gelir 3 yıl üst üste düştüyse sağlam olamaz
    kuculme = M[1] is not None and M[1] < 0
    if kuculme and sinif == "SAĞLAM": sinif = "ORTA (küçülme kuralı)"

    A[3] = faal_kaynak.get(son, "")
    return dict(borc_r=borc_r, fcf3=fcf3, sert10=sert10, bolunme=bolunme, likit=likit, borc=borc, vo=vo, faiz=faiz,
                oz=oz, varlik=varlik, kvy_=kvy_, on=on, yat=yat, tem=tem, brut=brut, faal_kaynak=faal_kaynak, t=t, son=son, tur=tur, sek=sek, M=M, R=R, A=A, bel=bel, br=br, sinif=sinif, tem_r=tem_r,
                kuculme=kuculme, gelir=gelir, fcf=fcf, Y=Y, net=net, hisse=hisse, hbk=hbk, gm=gm, faal=faal)


def fmt(k, v):
    if v is None: return "hesaplanamadı"
    if v == "NN": return "nakit > borç"
    if v == "FCF-": return "nakit üretmiyor, borç var"
    if v == "FCF+": return "nakit üretiyor"
    if v == "POZ": return "zarardan kâra döndü"
    if k == 2: return f"{v:+.1f} puan"
    if k in (6, 7, 10): return f"{v:.1f}"
    return f"{v*100:+.1f}%" if k in (1, 8, 9) else f"{v*100:.1f}%"


AD = {1: "Gelir büyümesi (3y)", 2: "Marj istikrarı", 3: "Faaliyet marjı", 4: "Sermaye getirisi (5y, ROCE)",
      5: "Nakde dönüşüm (3y)", 6: "Faiz karşılama (kat)", 7: "Borcu öder (yıl)", 8: "Hisse sayısı (5y)",
      9: "Brüt kâr büyümesi (3y)", 10: "Nakit yeter (yıl)"}

if __name__ == "__main__":
    out = {}
    for t in sys.argv[1:]:
        r = analiz(t)
        out[t] = r
        print(f"\n===== {t} · {r['sek']} · son mali yıl {r['son']} · TÜR: {r['tur']} · SINIF: {r['sinif']}")
        for k in range(1, 11):
            isaret = "◆" if k in r["bel"] else " "
            print(f"  {isaret} {k:>2} {AD[k]:24s} {r['R'][k]} {fmt(k, r['M'][k]):28s} {r['A'].get(k, '')}")
        if "B" in r["bel"]: print(f"  ◆  B Borç (6+7 birleşik)          {r['borc_r']}")
        if "T" in r["bel"]: print(f"  ◆  T Temettü nakitle karşılanıyor (5y) {r['tem_r']}")
        print("     FCF (milyar $): " + "  ".join(f"{e[:4]}:{r['fcf'][e]/1e9:.1f}" for e in r["Y"] if e in r["fcf"]))
        print("     Gelir (milyar $): " + "  ".join(f"{e[:4]}:{r['gelir'][e]/1e9:.1f}" for e in r["Y"] if e in r["gelir"]))
        print(f"     belirleyiciler {r['bel']} → {r['br']}  küçülme={r['kuculme']}")
    json.dump({t: {"son": r["son"], "fcf_son": r["fcf"].get(r["son"]),
                   "hbk": {e: r["hbk"][e] for e in r["Y"] if e in r["hbk"]},
                   "hisse_son": r["hisse"].get(r["son"])} for t, r in out.items()}, open("ozet.json", "w"))
```

`fiyat.py` — price line (Yahoo, `yfinance`):

```python
import json, yfinance as yf
from karne_deneme import analiz
out = {}
for t in ["KO","NVDA","NKE","SBUX","PFE","INTC","BA","SNAP","DOW","RIVN"]:
    r = analiz(t)
    try:
        tk = yf.Ticker(t); fi = tk.fast_info
        fiyat, pd = float(fi["last_price"]), float(fi["market_cap"])
        info = tk.info; pe = info.get("trailingPE")
    except Exception as e:
        print(t, "fiyat alınamadı:", e); continue
    Y = r["Y"]; net = r["net"]; son = Y[-1]; i3 = Y[-4]
    a, b = net.get(i3), net.get(son)
    buy = ((b / a) ** (1/3) - 1) if a and b and a > 0 and b > 0 else None
    peg = (pe / (buy * 100)) if pe and buy and buy > 0 else None
    fv = r["fcf"].get(son, 0) / pd
    out[t] = dict(fiyat=fiyat, pd=pd, pe=pe, buy=buy, peg=peg, fv=fv)
    pegs = "anlamsız (kâr yok ya da düşüyor)" if peg is None else f"{peg:.2f} ({'cazip' if peg<=1 else 'makul' if peg<=2 else 'pahalı'})"
    fvs = f"{fv*100:.1f}% ({'cazip' if fv>=.05 else 'makul' if fv>=.02 else 'pahalı' if fv>0 else 'nakit yakıyor'})"
    print(f"{t:5s} fiyat {fiyat:8.2f}$  piyasa değeri {pd/1e9:7.0f} milyar$  F/K {pe if pe is None else round(pe,1)}  "
          f"net kâr büy.(3y) {'—' if buy is None else f'{buy*100:.1f}%'}  PEG {pegs}  FCF verimi {fvs}")
json.dump(out, open("fiyat.json","w"))
```

## PROMPT END
