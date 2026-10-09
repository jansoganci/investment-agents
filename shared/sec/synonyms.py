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
        "gain_on_sale": ["GainLossOnSaleOfBusiness", "DisposalGroupNotDiscontinuedOperationGainLossOnDisposal",
                         "GainLossOnDispositionOfAssets"],
        "acquisitions": ["PaymentsToAcquireBusinessesNetOfCashAcquired"],
        # instant (balance sheet)
        "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
        "short_term_investments": ["ShortTermInvestments", "OtherShortTermInvestments"],
        # `MarketableSecurities` only counts when no `MarketableSecuritiesNoncurrent` is reported that year (then it is the
        # current line; Coca-Cola renamed its line in 2021). `DebtSecuritiesCurrent`: Nvidia from its July 2026 10-Q
        "marketable_securities": ["MarketableSecuritiesCurrent", "MarketableSecurities", "DebtSecuritiesCurrent"],
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
        # GE's 10-Qs (2026): the long-term part under the lease-inclusive name, the short-term part as `DebtCurrent`
        # (17.157 + 2.000 = 19.157 bn, the filing's total borrowings). Last, so it never replaces a group above; where one
        # of them is also complete it agrees within 1% (Boeing every year, GE 2023–2024).
        (["LongTermDebtAndCapitalLeaseObligations", "DebtCurrent"], True, True),
    ],
    "ifrs-full": [
        (["Borrowings"], True, True),
        (["LongtermBorrowings", "CurrentPortionOfLongtermBorrowings", "ShorttermBorrowings"], True, False),
        (["NoncurrentPortionOfNoncurrentBorrowings", "CurrentPortionOfNoncurrentBorrowings", "CurrentBorrowings"], True,
         False),
    ],
}

# Tried only when no group above is complete — never a candidate next to one (it is a part of the first group; Nike 2026 got a
# false "candidates disagree" when it was): Rivian and McDonald's (2026) report only the long-term line, no current portion
# (roadmap rule 45). Short-term borrowings are still added.
DEBT_LAST_RESORT: dict[str, list[tuple[list[str], bool, bool]]] = {
    "us-gaap": [(["LongTermDebtNoncurrent"], False, True)],
    "ifrs-full": [],
}

# Added only when the group does not already include short-term debt; only the first one found
# (`ShortTermBorrowings` often includes `CommercialPaper`).
SHORT_TERM_DEBT: dict[str, list[str]] = {"us-gaap": ["ShortTermBorrowings", "CommercialPaper"], "ifrs-full": []}


# Debt-balance names that stop the "no debt" assumption when they hold a value other than zero (roadmap section 3, "A company
# with no debt"). The group names and `SHORT_TERM_DEBT` count too.
DEBT_BALANCE_EXTRA: dict[str, list[str]] = {
    "us-gaap": ["DebtInstrumentCarryingAmount", "NotesPayable", "SeniorNotes", "SecuredDebt", "UnsecuredDebt", "LineOfCredit",
                "LongTermLineOfCredit"],
    "ifrs-full": [],
}


def debt_balance_names(taxonomy: str) -> set[str]:
    return ({n for group, _, _ in DEBT_GROUPS[taxonomy] for n in group} | set(SHORT_TERM_DEBT[taxonomy])
            | set(DEBT_BALANCE_EXTRA[taxonomy]))


# names read only to check another name (kept in the sample data)
CHECK_NAMES = {"us-gaap": {"MarketableSecuritiesNoncurrent"}, "ifrs-full": set()}


def all_names(taxonomy: str) -> set[str]:
    names = {n for names in SYNONYMS[taxonomy].values() for n in names} | CHECK_NAMES[taxonomy]
    names |= {n for group, _, _ in DEBT_GROUPS[taxonomy] + DEBT_LAST_RESORT[taxonomy] for n in group}
    names |= set(SHORT_TERM_DEBT[taxonomy]) | set(DEBT_BALANCE_EXTRA[taxonomy])
    return names
