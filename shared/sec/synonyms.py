"""Synonym lists per figure (roadmap section 3, "SEC data — synonym method").

For each year separately, code tries a figure's list in order and takes the first name found, so a company that renames a
tag is caught on its own (Coca-Cola: 2023 `LongTermDebt`, 2024 `LongTermDebtAndCapitalLeaseObligations`). A new name is
added here when the `missing_data` ledger shows one. Each taxonomy has its own lists (`us-gaap` for 10-K / 10-Q, `ifrs-full`
for many 20-F filers).
"""

# figure → names tried in order. `duration` figures cover a period; the others are balance-sheet points (instant).
SYNONYMS: dict[str, dict[str, list[str]]] = {
    "us-gaap": {
        "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                    "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
        "cost": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
        "gross": ["GrossProfit"],
        "operating": ["OperatingIncomeLoss"],
        "pretax": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                   "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
        "tax": ["IncomeTaxExpenseBenefit"],
        "net": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss"],
        "interest": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense"],
        "net_interest_income": ["InterestIncomeExpenseNonoperatingNet", "InterestIncomeExpenseNet"],
        "interest_income": ["InvestmentIncomeInterest", "InterestIncomeOther", "InvestmentIncomeInterestAndDividend"],
        "op_cash": ["NetCashProvidedByUsedInOperatingActivities"],
        "capex": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
        "stock_comp": ["ShareBasedCompensation", "AllocatedShareBasedCompensationExpense"],
        "dividends": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock", "PaymentsOfOrdinaryDividends"],
        "eps": ["EarningsPerShareDiluted"],
        "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
        "gain_on_sale": ["GainLossOnSaleOfBusiness", "DisposalGroupNotDiscontinuedOperationGainLossOnDisposal"],
        "acquisitions": ["PaymentsToAcquireBusinessesNetOfCashAcquired"],
        # instant (balance sheet)
        "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
        "short_term_investments": ["ShortTermInvestments", "OtherShortTermInvestments"],
        "marketable_securities": ["MarketableSecuritiesCurrent"],
        "short_term_investments_partial": ["AvailableForSaleSecuritiesDebtSecuritiesCurrent",
                                           "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent"],
        "assets": ["Assets"],
        "current_liabilities": ["LiabilitiesCurrent"],
        "liabilities": ["Liabilities"],
        "leases": ["OperatingLeaseLiability"],
    },
    "ifrs-full": {
        "revenue": ["Revenue"],
        "cost": ["CostOfSales"],
        "gross": ["GrossProfit"],
        "operating": ["ProfitLossFromOperatingActivities"],
        "pretax": ["ProfitLossBeforeTax"],
        "tax": ["IncomeTaxExpenseContinuingOperations"],
        "net": ["ProfitLossAttributableToOwnersOfParent", "ProfitLoss"],
        "interest": ["InterestExpense", "InterestExpenseOnBorrowings"],
        "net_interest_income": [],
        "interest_income": ["InterestRevenueCalculatedUsingEffectiveInterestMethod", "FinanceIncome"],
        "op_cash": ["CashFlowsFromUsedInOperatingActivities"],
        "capex": ["PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"],
        "stock_comp": ["AdjustmentsForSharebasedPayments", "ExpenseFromSharebasedPaymentTransactionsWithEmployees"],
        "dividends": ["DividendsPaidClassifiedAsFinancingActivities", "DividendsPaid"],
        "eps": ["DilutedEarningsLossPerShare"],
        "shares": ["AdjustedWeightedAverageShares", "WeightedAverageShares"],
        "gain_on_sale": [],
        "acquisitions": [],
        "cash": ["CashAndCashEquivalents"],
        "short_term_investments": ["CurrentInvestments"],
        "marketable_securities": ["CurrentFinancialAssetsAtFairValueThroughProfitOrLoss"],
        "short_term_investments_partial": [],
        "assets": ["Assets"],
        "current_liabilities": ["CurrentLiabilities"],
        "liabilities": ["Liabilities"],
        "leases": ["LeaseLiabilities"],
    },
}

INSTANT = {"cash", "short_term_investments", "marketable_securities", "short_term_investments_partial", "assets",
           "current_liabilities", "liabilities", "leases"}

# figures whose unit is not the reporting currency
UNIT_KIND = {"shares": "shares", "eps": "per_share"}

# Debt candidates, tried in order: (names, short-term already included?, all parts required?).
# The first complete group gives the total; the others are a check (roadmap: "a group counts only if all of its parts are
# found"; the convertible group: any part). `LongTermDebtNoncurrent` + current portion is tried before `LongTermDebt`
# (Pfizer 2020: `LongTermDebt` held a single 4 bn item).
DEBT_GROUPS: dict[str, list[tuple[list[str], bool, bool]]] = {
    "us-gaap": [
        (["LongTermDebtNoncurrent", "LongTermDebtCurrent"], False, True),
        (["LongTermDebtNoncurrent", "DebtCurrent"], True, True),
        (["LongTermDebt"], False, True),
        (["LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent"], False, True),
        (["ConvertibleDebtNoncurrent", "ConvertibleDebtCurrent", "ConvertibleNotesPayable", "LongTermNotesPayable"], False,
         False),
    ],
    "ifrs-full": [
        (["Borrowings"], True, True),
        (["LongtermBorrowings", "CurrentPortionOfLongtermBorrowings", "ShorttermBorrowings"], True, False),
        (["NoncurrentPortionOfNoncurrentBorrowings", "CurrentPortionOfNoncurrentBorrowings", "CurrentBorrowings"], True,
         False),
    ],
}

# Added only when the group does not already include short-term debt; only the first one found
# (`ShortTermBorrowings` often includes `CommercialPaper`).
SHORT_TERM_DEBT: dict[str, list[str]] = {"us-gaap": ["ShortTermBorrowings", "CommercialPaper"], "ifrs-full": []}


def all_names(taxonomy: str) -> set[str]:
    names = {n for names in SYNONYMS[taxonomy].values() for n in names}
    names |= {n for group, _, _ in DEBT_GROUPS[taxonomy] for n in group}
    names |= set(SHORT_TERM_DEBT[taxonomy])
    return names
