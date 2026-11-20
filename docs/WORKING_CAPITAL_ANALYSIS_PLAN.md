# Working capital analysis plan

## Goal

Add a working capital section to the Agent 3 stock card. It should show how many days cash is tied up in operations, which component drove the change, and what the company's filing says about it.

The existing `cash_conversion` measure compares adjusted free cash flow with net income. The proposed cash conversion cycle (CCC) measures time in days and appears as an informational section in the dated card entry.

## Proposed calculation

Start with completed fiscal years for US GAAP operating companies. Use opening and closing consolidated balances and flows from the same fiscal year. Use the actual day count of the reported period, including 52- and 53-week fiscal years.

| Component | Calculation |
|---|---|
| Inventory days (DIO) | Average inventory ÷ cost of sales × fiscal-year days |
| Receivable days (DSO) | Average net trade receivables ÷ net revenue × fiscal-year days |
| Payable days (DPO) | Average trade payables ÷ cost of sales × fiscal-year days |
| Cash conversion cycle (CCC) | DIO + DSO − DPO |

Use net revenue as the proxy for credit sales and cost of sales as the proxy for purchases. Show both denominator choices on the card. Average each balance using its opening and closing values. Compare the company with its own comparable fiscal year first. A negative CCC is valid. A rise in DPO lowers CCC, all else equal.

Mark a component `not_computed` with a reason if a required balance or comparable period is missing, or if its denominator is zero or negative. Show available components and calculate CCC when all three are available. Calculate a year-over-year change only on a comparable reporting basis. When a filing restates a comparative value, reconcile the periods and use the restated basis if confirmed.

## Implementation checklist

### 1. Check SEC data coverage

- [ ] Use NIKE (NKE) as the reference case, Costco (COST) as a retail coverage check, and Visa (V) as a case where a required input or the metric may be inapplicable.
- [ ] Compare SEC Company Facts with the original 10-Ks for inventory, net trade receivables, and trade payables. Record the tag, period, unit, filing accession and source link. Validate broad receivable and payable tags against the statement. Identify any material components that affect interpretation, such as supplier finance disclosed within NIKE's accounts payable.
- [ ] Verify that each fiscal year has both balances and matching flows. Record missing tags and identify the filing line for review so the coverage decision rests on the pilot. [SEC facts](../shared/sec/facts.py) · [SEC synonyms](../shared/sec/synonyms.py)

### 2. Calculate and display

- [ ] Reuse the SEC response and the existing Facts reader in annual mode. Select opening and closing balances from the annual fiscal periods. Agent 3's TTM window can omit its overlapping annual result, so use the explicitly annual dates for this calculation. [Analysis entry point](../agents/analysis/run.py) · [SEC facts](../shared/sec/facts.py)
- [ ] Calculate all four metrics in Python. Keep the input values and formula auditable. Round only when displaying the result. [Agent 3 measures](../agents/analysis/measures.py)
- [ ] Add an informational section to the dated card entry. Include the last two comparable fiscal years when available, the four day values, each component's contribution to the CCC change, and the source filings. Store the figures in the card's YAML block. [Stock card](../agents/analysis/card.py)

### 3. Explain the change with filing evidence

- [ ] Ask what drove the largest component change using the existing explanation flow. Look for the relevant Management's Discussion and Analysis passage or financial statement note. [Analysis explanations](../agents/analysis/ai.py)
- [ ] Give the model the calculated values and periods. Check that an excerpt appears in the original filing and supports the stated cause. When evidence is insufficient, show the measured change and indicate that a cause could not be verified from the filing.
- [ ] Review the calculation and card output first. Then test explanation quality and cost using the existing explanation call as the initial integration point.

## Acceptance checks

- [ ] Reproduce NIKE's 2025 and 2026 results from its 10-Ks using the reported line items and 365 days per year. Rounded to one decimal, CCC is 95.8 → 96.4 days, DIO is 103.3 → 103.3, DSO is 36.0 → 41.9, and DPO is 43.6 → 48.8.
- [ ] Check Costco against its filings and Visa for a correctly explained missing or inapplicable result where appropriate. Cover a 52- or 53-week fiscal year, a missing opening balance, a zero denominator, a negative CCC, and a TTM run with annual comparison dates.
- [ ] Verify the existing golden-set grades and append-only card behavior. Check the proposed explanation on one sourced change and on one change with insufficient evidence. [Golden-set tests](../tests/analysis/test_measures.py) · [Card entry tests](../tests/analysis/test_run.py)

## Open decisions

Approve the annual pilot and proposed denominator choices first. Decide whether standard US GAAP Company Facts provides sufficient coverage for rollout after seeing the pilot. Later candidates are interim and IFRS comparisons, a targeted inline XBRL fallback for missing company-specific figures, and source-backed explanations of earnings adjustments or lease exposure.

## Sources

- [İbrahim Gör on receivable, payable and cash conversion days](https://www.ibrahimgor.com/2022/10/06/faaliyet-etkinlik-analizi-2/)
- [BİMAŞ 2024/6 working capital example](https://www.ibrahimgor.com/2024/10/01/bimas-finansal-tablo-analizi-2024-6/)
- [Pegasus 2023 example of using notes to explain changes](https://www.ibrahimgor.com/2024/03/25/pegasus-2023-yillik-finansal-tablolar-analizi/)
- [SEC EDGAR XBRL API coverage](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [NIKE FY2025 10-K](https://www.sec.gov/Archives/edgar/data/320187/000032018725000047/nke-20250531.htm) · [NIKE FY2026 10-K](https://www.sec.gov/Archives/edgar/data/320187/000032018726000088/nke-20260531.htm)
