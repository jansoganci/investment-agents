import json,sys
GROUPS = {
 "Gelir": ["Revenues","RevenueFromContractWithCustomerExcludingAssessedTax","SalesRevenueNet","Revenue"],
 "Satis maliyeti": ["CostOfRevenue","CostOfGoodsAndServicesSold","CostOfGoodsSold","CostOfSales"],
 "Brut kar": ["GrossProfit"],
 "Faaliyet kari": ["OperatingIncomeLoss","ProfitLossFromOperatingActivities"],
 "Vergi oncesi kar": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest","IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments","ProfitLossBeforeTax"],
 "Vergi gideri": ["IncomeTaxExpenseBenefit","IncomeTaxExpenseContinuingOperations"],
 "Faiz gideri": ["InterestExpense","InterestExpenseNonoperating","InterestExpenseDebt","InterestPaidNet","FinanceCosts","InterestExpenseOnBorrowings"],
 "Isletme nakit akisi": ["NetCashProvidedByUsedInOperatingActivities","CashFlowsFromUsedInOperatingActivities"],
 "Yatirim harcamasi": ["PaymentsToAcquirePropertyPlantAndEquipment","PaymentsToAcquireProductiveAssets","PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"],
 "Nakit": ["CashAndCashEquivalentsAtCarryingValue","CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents","CashAndCashEquivalents"],
 "Kisa vadeli yatirim": ["MarketableSecuritiesCurrent","ShortTermInvestments","AvailableForSaleSecuritiesDebtSecuritiesCurrent","CurrentFinancialAssetsAtFairValueThroughProfitOrLoss"],
 "Ozkaynak": ["StockholdersEquity","StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest","Equity"],
 "Borc: uzun vade (toplam)": ["LongTermDebt"],
 "Borc: uzun vade (cari olmayan)": ["LongTermDebtNoncurrent","NoncurrentPortionOfNoncurrentBorrowings"],
 "Borc: uzun vade cari kisim": ["LongTermDebtCurrent","CurrentPortionOfNoncurrentBorrowings"],
 "Borc: kisa vade / ticari senet": ["ShortTermBorrowings","CommercialPaper","DebtCurrent","ShorttermBorrowings","CurrentBorrowings"],
 "Borc: convertible": ["ConvertibleNotesPayable","ConvertibleDebtNoncurrent","ConvertibleSeniorNotesNoncurrent","ConvertibleDebtCurrent"],
 "Borc: IFRS toplam": ["Borrowings","NoncurrentBorrowings"],
 "Hisse sayisi (bilanco)": ["CommonStockSharesOutstanding"],
 "Hisse sayisi (seyreltilmis ort.)": ["WeightedAverageNumberOfDilutedSharesOutstanding","WeightedAverageNumberOfSharesOutstandingDiluted","AdjustedWeightedAverageShares"],
 "Temettu odemesi": ["PaymentsOfDividends","PaymentsOfDividendsCommonStock","DividendsPaidClassifiedAsFinancingActivities"],
}
def fy_years(units):
    ys=set()
    for u,arr in units.items():
        for x in arr:
            if x.get("form") in ("10-K","20-F","40-F") and x.get("fp")=="FY":
                ys.add(x.get("fy"))
    return ys
def has_q(units):
    return any(x.get("form")=="10-Q" for arr in units.values() for x in arr)
for t in sys.argv[1:]:  # etiket_kontrol: önce `bash indir.sh`
    d=json.load(open(t+".json")); f=d["facts"]
    tax = [k for k in f if k!="dei"]
    print(f"\n===== {t} ({d['entityName']}) taksonomi: {tax}")
    dei=f.get("dei",{})
    print("  kapak hisse sayisi (dei):", "EntityCommonStockSharesOutstanding" in dei)
    for g,tags in GROUPS.items():
        found=[]
        for tx in tax:
            for tg in tags:
                if tg in f[tx]:
                    ys=fy_years(f[tx][tg]["units"]); 
                    rec=[y for y in ys if y and y>=2021]
                    found.append(f"{tg}[{len(rec)}y'21+{' Q' if has_q(f[tx][tg]['units']) else ''}]")
        print(f"  {g:34s} {'; '.join(found) if found else '— YOK'}")
