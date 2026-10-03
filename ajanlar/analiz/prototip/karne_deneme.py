"""Agent 3 trial (prototype, not production).

Rules: docs/YOL_HARITASI_v2.md section 3 ("Agent 3 rules"), version after the two external reviews (2026-10-03).
Names follow docs/GLOSSARY.md. Input: SEC companyfacts `<T>.json` + submissions `<T>_sub.json` (`bash indir.sh`)
and Yahoo data `yahoo.json` (`uv run --with yfinance python yahoo_indir.py`).

Run: python3 karne_deneme.py KO NVDA ...
"""
import json
import os
import sys
from datetime import date

FORMS = {"10-K", "10-K/A", "20-F", "20-F/A"}

# GICS sector, assigned by hand in the trial (production: tag mapping)
SECTOR = {"KO": "Consumer Staples", "NVDA": "Information Technology", "NKE": "Consumer Discretionary",
          "SBUX": "Consumer Discretionary", "PFE": "Health Care", "INTC": "Information Technology",
          "BA": "Industrials", "SNAP": "Communication Services", "DOW": "Materials",
          "RIVN": "Consumer Discretionary", "NVO": "Health Care"}

# Cyclical industries by SEC SIC code: semiconductors, autos, airlines, shipping, homebuilding,
# chemicals (drugs 2830-2836 and soaps/cosmetics 2840-2844 excluded), steel, mining
CYCLICAL_SIC = [(3674, 3674), (3711, 3716), (4512, 4522), (4400, 4499), (1520, 1531),
                (2800, 2829), (2850, 2899), (3310, 3329), (1000, 1499)]

# Synonym lists per taxonomy (tried in order, per year)
SYN = {
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
        "cash": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
        "sti": ["ShortTermInvestments", "OtherShortTermInvestments"],
        "ms": ["MarketableSecuritiesCurrent"],
        "sti_partial": ["AvailableForSaleSecuritiesDebtSecuritiesCurrent",
                        "DebtSecuritiesAvailableForSaleExcludingAccruedInterestCurrent"],
        "assets": ["Assets"],
        "current_liabilities": ["LiabilitiesCurrent"],
        "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
        "dividends": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock", "PaymentsOfOrdinaryDividends"],
        "eps": ["EarningsPerShareDiluted"],
        "gain_on_sale": ["GainLossOnSaleOfBusiness", "DisposalGroupNotDiscontinuedOperationGainLossOnDisposal"],
        "acquisitions": ["PaymentsToAcquireBusinessesNetOfCashAcquired"],
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
        "cash": ["CashAndCashEquivalents"],
        "sti": ["CurrentInvestments"],
        "ms": ["CurrentFinancialAssetsAtFairValueThroughProfitOrLoss"],
        "sti_partial": [],
        "assets": ["Assets"],
        "current_liabilities": ["CurrentLiabilities"],
        "shares": ["AdjustedWeightedAverageShares", "WeightedAverageShares"],
        "dividends": ["DividendsPaidClassifiedAsFinancingActivities", "DividendsPaid"],
        "eps": ["DilutedEarningsLossPerShare"],
        "gain_on_sale": [],
        "acquisitions": [],
        "leases": ["LeaseLiabilities"],
    },
}

# Debt candidates: (tags, short-term already included?, all parts required?) — first complete group wins, the others are a check
DEBT = {
    "us-gaap": [(["LongTermDebtNoncurrent", "LongTermDebtCurrent"], False, True),
                (["LongTermDebtNoncurrent", "DebtCurrent"], True, True),
                (["LongTermDebt"], False, True),
                (["LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent"], False, True),
                (["ConvertibleDebtNoncurrent", "ConvertibleDebtCurrent", "ConvertibleNotesPayable", "LongTermNotesPayable"], False, False)],
    "ifrs-full": [(["Borrowings"], True, True),
                  (["LongtermBorrowings", "CurrentPortionOfLongtermBorrowings", "ShorttermBorrowings"], True, False),
                  (["NoncurrentPortionOfNoncurrentBorrowings", "CurrentPortionOfNoncurrentBorrowings", "CurrentBorrowings"], True, False)],
}
SHORT_TERM = {"us-gaap": ["ShortTermBorrowings", "CommercialPaper"], "ifrs-full": []}  # first found (ShortTermBorrowings often includes CP)

# Thresholds: (good, mid) — higher is better unless listed in LOWER_BETTER
TH = {1: (.15, .08), 2: (-1, -3), 3: (.15, .05), 4: (.15, .08), 5: (.80, .50), 6: (8, 3), 7: (3, 5), 8: (0, .10),
      9: (.20, .10), 10: (3, 1.5)}
LOWER_BETTER = {7, 8}
TH10_STRICT = (5, 3)

DECISIVE = {"stalwart": [2, 3, 4, 5], "fast_grower": [1, 9, 2, 10, 8], "slow_grower": [2, 4, 5, "B", "T"],
            "cyclical": [4, "B", 8], "unprofitable": [2, 3, 4, 5]}
NAMES = {1: "revenue_growth_3y", 2: "margin_stability", 3: "operating_margin", 4: "capital_return",
         5: "cash_conversion", 6: "interest_cover", 7: "debt_years", 8: "share_count", 9: "gross_profit_growth",
         10: "cash_runway", "B": "debt", "T": "dividend_cover"}
GOOD, MID, WEAK, NONE = "✅", "➖", "❌", "·"


def d(s):
    return date.fromisoformat(s)


def avg(vals, need=2):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if len(vals) >= need else None


def cagr(a, b, n):
    if a is None or b is None or a <= 0 or b <= 0 or n <= 0:
        return None
    return (b / a) ** (1 / n) - 1


def mark(k, v, strict10=False):
    if v is None:
        return NONE
    good, mid = TH10_STRICT if (k == 10 and strict10) else TH[k]
    if k in LOWER_BETTER:
        return GOOD if v <= good else (MID if v <= mid else WEAK)
    return GOOD if v >= good else (MID if v >= mid else WEAK)


class Company:
    def __init__(self, t):
        self.t = t
        facts = json.load(open(f"{t}.json"))["facts"]
        self.tax = "us-gaap" if len(facts.get("us-gaap", {})) > 50 else "ifrs-full"
        self.f = facts[self.tax]
        self.syn = SYN[self.tax]
        self.unit = self._currency()
        fys = [x["fy"] for v in self.f.values() for u in v["units"].values() for x in u
               if x.get("form") in FORMS and x.get("fy")]
        self.first_fy = min(fys)
        self.sic = None
        if os.path.exists(f"{t}_sub.json"):
            self.sic = int(json.load(open(f"{t}_sub.json"))["sic"] or 0)
        self.ends = self._year_ends()

    def _currency(self):
        for tag in self.syn["revenue"]:
            if tag in self.f:
                return max(self.f[tag]["units"], key=lambda u: len(self.f[tag]["units"][u]))
        return "USD"

    def _facts(self, tag, unit, duration):
        out = {}
        for x in self.f.get(tag, {}).get("units", {}).get(unit, []):
            if x.get("form") not in FORMS or ("start" in x) != duration:
                continue
            if duration and not 350 <= (d(x["end"]) - d(x["start"])).days <= 380:
                continue
            if x["end"] not in out or x["filed"] > out[x["end"]][1]:
                out[x["end"]] = (x["val"], x["filed"])
        return {k: v[0] for k, v in out.items()}

    def _year_ends(self):
        raw = set()
        for tag in self.syn["revenue"] + self.syn["operating"]:
            raw |= set(self._facts(tag, self.unit, True))
        merged = []
        for e in sorted(raw):  # 52/53-week years: ends less than 10 days apart are one year
            if merged and (d(e) - d(merged[-1])).days < 10:
                merged[-1] = e
            else:
                merged.append(e)
        return merged[-6:]

    def _at(self, table, e):
        for k, v in table.items():
            if abs((d(k) - d(e)).days) < 10:
                return v
        return None

    def series(self, key, unit=None, duration=True):
        """{year end: (value, tag)} — each year tries the synonym list in order."""
        tables = [(tag, self._facts(tag, unit or self.unit, duration)) for tag in self.syn[key]]
        out = {}
        for e in self.ends:
            for tag, tb in tables:
                v = self._at(tb, e)
                if v is not None:
                    out[e] = (v, tag)
                    break
        return out

    def debt(self):
        """{year end: (total, source tags, candidates disagree?)}"""
        out = {}
        for e in self.ends:
            cands = []
            for tags, st_in, need_all in DEBT[self.tax]:
                vals = [(tg, self._at(self._facts(tg, self.unit, False), e)) for tg in tags]
                found = [(tg, v) for tg, v in vals if v is not None]
                vals = found if (len(found) == len(tags) or (found and not need_all)) else []
                if vals:
                    cands.append((sum(v for _, v in vals), [tg for tg, _ in vals], st_in))
            if not cands:
                out[e] = (None, [], False)
                continue
            total, src, st_in = cands[0]
            if not st_in:
                for tg in SHORT_TERM[self.tax]:
                    v = self._at(self._facts(tg, self.unit, False), e)
                    if v:
                        total += v
                        src = src + [tg]
                        break
            longs = [c[0] for c in cands[:3]]
            disagree = len(longs) > 1 and max(longs) > 1.25 * min(longs) and min(longs) > 0
            out[e] = (total, src, disagree)
        return out


def analyse(t, yahoo=None):
    c = Company(t)
    Y = c.ends
    yh = (yahoo or {}).get(t, {})
    g = lambda k, **kw: {e: v[0] for e, v in c.series(k, **kw).items()}
    rev, cost, gross = g("revenue"), g("cost"), g("gross")
    op_rep, pretax, tax, net = g("operating"), g("pretax"), g("tax"), g("net")
    interest_s = c.series("interest")
    interest = {e: v[0] for e, v in interest_s.items()}
    net_int = g("net_interest_income")
    int_inc = g("interest_income")
    for e in Y:  # no net tag: net interest income = interest income − interest expense (both accrual, never cash interest)
        if e not in net_int and e in int_inc and e in interest:
            net_int[e] = int_inc[e] - interest[e]
    op_cash, capex, sbc = g("op_cash"), g("capex"), g("stock_comp")
    cash, sti, ms, sti_p = (g(k, duration=False) for k in ("cash", "sti", "ms", "sti_partial"))
    assets, cur_liab = g("assets", duration=False), g("current_liabilities", duration=False)
    shares = g("shares", unit="shares")
    divs = g("dividends")
    eps = g("eps", unit=f"{c.unit}/shares")
    gain = g("gain_on_sale")
    acq = g("acquisitions")
    leases = g("leases", duration=False)
    debt = c.debt()
    flags, notes = [], []

    for e in Y:  # gross profit: reported, otherwise revenue − cost
        if e not in gross and e in rev and e in cost:
            gross[e] = rev[e] - cost[e]
    op, op_src = {}, {}
    for e in Y:  # operating profit: reported, otherwise pre-tax − net interest income, otherwise not computed
        if e in op_rep:
            op[e], op_src[e] = op_rep[e], "reported"
        elif e in pretax and e in net_int:
            op[e], op_src[e] = pretax[e] - net_int[e], "approx: pre-tax − net interest"
    liquid = {}
    for e in Y:  # cash + short-term investments + marketable securities (parts added; absent part = not held)
        if e not in cash:
            continue
        parts = (sti.get(e) or 0) + (ms.get(e) or 0)
        if e not in sti and e not in ms:
            parts = sti_p.get(e) or 0
        liquid[e] = cash[e] + parts
    fcf = {e: op_cash[e] - capex[e] - sbc[e] for e in Y if e in op_cash and e in capex and e in sbc}
    last = Y[-1]
    i3 = Y[-4] if len(Y) >= 4 else Y[0]
    n3 = len(Y) - 1 - Y.index(i3)
    fcf3 = avg([fcf.get(e) for e in Y[-3:]])
    debt_last = debt[last][0]

    M, N = {}, {}  # values, notes
    # 1 revenue growth (3y)
    M[1] = cagr(rev.get(i3), rev.get(last), n3)
    # 2 margin stability: worse of (latest − avg of previous 4) and (latest − previous); outlier years left out
    def margins(num):
        out = {}
        for e in Y:
            if e in num and rev.get(e) and rev.get(last) and rev[e] >= 0.1 * rev[last]:
                m = num[e] / rev[e]
                if abs(m) <= 1:
                    out[e] = m
        return out
    mg, kind = margins(gross), "gross"
    if len(mg) < 3:
        mg, kind = margins(op), "operating"
    ys = [e for e in Y[-5:] if e in mg]
    if len(ys) >= 3 and ys[-1] == last:
        a = (mg[last] - avg([mg[e] for e in ys[:-1]])) * 100
        b = (mg[last] - mg[ys[-2]]) * 100
        M[2] = min(a, b)
        N[2] = f"{kind} margin {mg[last]*100:.1f}% (prev-4 avg {avg([mg[e] for e in ys[:-1]])*100:.1f}%, prev year {mg[ys[-2]]*100:.1f}%)"
    else:
        M[2] = None
    # 3 operating margin
    M[3] = op[last] / rev[last] if last in op and rev.get(last) else None
    N[3] = op_src.get(last, "not reported, no net-interest tag")
    # 4 capital return per year; avg3 / avg5
    roce = {}
    for e in Y[-5:]:
        if e not in op or e not in assets or e not in cur_liab or e not in liquid:
            continue
        p, tx = pretax.get(e), tax.get(e)
        rate = min(max(tx / p, 0), 0.35) if p and p > 0 and tx is not None else 0.21
        ic = assets[e] - cur_liab[e] - liquid[e]
        if ic > 0:
            roce[e] = op[e] * (1 - rate) / ic
    r5 = avg([roce.get(e) for e in Y[-5:]], need=3)
    r3 = avg([roce.get(e) for e in Y[-3:]])
    # 5 cash conversion (3y)
    yy = [e for e in Y[-3:] if e in fcf and e in net]
    sn = sum(net[e] for e in yy)
    M[5] = sum(fcf[e] for e in yy) / sn if len(yy) >= 2 and sn > 0 else None
    N[5] = "net profit ≤ 0" if len(yy) >= 2 and sn <= 0 else ""
    # 6 interest cover (cash interest never used)
    cash_over_debt = last in liquid and debt_last is not None and liquid[last] >= debt_last
    if cash_over_debt:
        M[6], N[6] = "NN", "cash > debt"
    elif interest.get(last) and last in op:
        M[6], N[6] = op[last] / interest[last], interest_s[last][1]
    else:
        M[6], N[6] = None, "not computed"
    # 7 debt years
    if debt_last is None or last not in liquid:
        M[7] = None
    elif debt_last - liquid[last] <= 0:
        M[7] = "NN"
    elif fcf3 is None:
        M[7] = None
    elif fcf3 <= 0:
        M[7] = "FCF-"
    else:
        M[7] = (debt_last - liquid[last]) / fcf3
    N[7] = "+".join(debt[last][1]) or "no debt tag"
    # 8 share count: IPO year skipped; splits (both ways) adjusted only if Yahoo confirms
    hy = [e for e in Y if e in shares and int(e[:4]) > c.first_fy] if int(Y[0][:4]) <= c.first_fy else [e for e in Y if e in shares]
    hy = hy[-6:]
    adj, split_note, split_bad, splits_applied = dict(shares), [], False, []
    window_start = date.fromordinal(d(Y[0]).toordinal() - 400).isoformat()  # only splits in the years we look at
    confirmed = [r for dt, r in yh.get("splits", []) if dt >= window_start]
    for a_, b_ in zip(hy, hy[1:]):
        r = adj[b_] / adj[a_]
        for k in (2, 3, 4, 5, 8, 10, 20):
            for kk in (k, 1 / k):
                if abs(r - kk) / kk < 0.06:
                    if any(abs(x - kk) / kk < 0.06 for x in confirmed):
                        for e in hy[:hy.index(b_)]:
                            adj[e] *= kk
                        splits_applied.append((b_, kk))
                        split_note.append(f"split ×{kk:g} adjusted (Yahoo confirmed)")
                    else:
                        split_bad = True
                        split_note.append(f"jump ×{kk:g} not confirmed by Yahoo")
                    break
            else:
                continue
            break
    M[8] = None if split_bad or len(hy) < 2 else adj[hy[-1]] / adj[hy[0]] - 1
    N[8] = f"{hy[0][:4]}→{hy[-1][:4]} " + ", ".join(split_note) if hy else ""
    if split_bad:
        flags.append("data_check: share-count jump not confirmed (possible merger)")
    # 9 gross-profit growth
    a9, b9 = gross.get(i3), gross.get(last)
    M[9] = cagr(a9, b9, n3)
    if M[9] is None and a9 is not None and b9 is not None:
        M[9] = "POS" if a9 <= 0 < b9 else ("NEG" if a9 <= 0 and b9 <= 0 else None)
    # 10 cash runway
    if fcf3 is None:
        M[10] = None
    elif fcf3 >= 0:
        M[10] = "FCF+"
    else:
        M[10] = liquid[last] / -fcf3 if last in liquid else None
        if debt_last and last in liquid and debt_last > liquid[last]:
            notes.append("part of the cash on hand is debt")

    # type (Lynch, new order)
    years = []
    for e in Y[-5:]:
        v = op.get(e, op_rep.get(e))
        if v is None:
            v = pretax.get(e)  # sign only
        if v is not None:
            years.append(v > 0)
    profits, losses = years.count(True), years.count(False)
    sic_cyc = c.sic is not None and any(lo <= c.sic <= hi for lo, hi in CYCLICAL_SIC)
    sector_cyc = SECTOR.get(t) in ("Energy", "Materials") or sic_cyc
    if len(years) < 3:
        lynch_type = "unclear"
    elif (sector_cyc and profits >= 1) or (profits and losses):
        lynch_type = "cyclical"
    elif profits < 4 and fcf3 is not None and fcf3 < 0:
        lynch_type = "unprofitable"
    elif M[1] is not None and M[1] >= .15:
        lynch_type = "fast_grower"
    elif profits < 4:
        lynch_type = "unprofitable"
    elif M[1] is not None and M[1] >= .05:
        lynch_type = "stalwart"
    else:
        lynch_type = "slow_grower"

    M[4] = r5 if lynch_type == "cyclical" else (min(r3, r5) if r3 is not None and r5 is not None else r5)
    N[4] = f"3y {r3*100:.1f}% · 5y {r5*100:.1f}%" if r3 is not None and r5 is not None else f"{len(roce)} years"
    strict10 = lynch_type == "fast_grower" and fcf3 is not None and fcf3 < 0
    R = {k: mark(k, M[k], strict10) if isinstance(M[k], (int, float)) or M[k] is None else None for k in range(1, 11)}
    R[6] = GOOD if M[6] == "NN" else R[6]
    R[7] = GOOD if M[7] == "NN" else (WEAK if M[7] == "FCF-" else R[7])
    R[9] = MID if M[9] == "POS" else (WEAK if M[9] == "NEG" else R[9])
    R[10] = GOOD if M[10] == "FCF+" else R[10]
    order = [WEAK, MID, GOOD]
    R["B"] = R[6] if R[6] != NONE else R[7]
    if R["B"] != NONE and R[6] != NONE and R[7] == WEAK:
        R["B"] = order[max(order.index(R["B"]) - 1, 0)]
    y5 = [e for e in Y[-5:] if e in fcf and e in divs]
    R["T"] = NONE if not divs else (GOOD if len(y5) >= 2 and sum(fcf[e] for e in y5) >= sum(divs[e] for e in y5)
                                    else (WEAK if len(y5) >= 2 else NONE))

    # grade
    if lynch_type == "unclear":
        grade, dec, marks = "unclear", [], []
    else:
        dec = DECISIVE[lynch_type]
        marks = [R[k] for k in dec]
        computed = [m for m in marks if m != NONE]
        if len(computed) * 2 < len(marks):
            grade = "unclear"
        elif marks.count(WEAK) >= 2:
            grade = "weak"
        elif marks.count(WEAK) == 0 and marks.count(GOOD) * 2 >= len(marks):
            grade = "solid"
        else:
            grade = "mid"
    rules = []
    if grade == "solid" and M[1] is not None and M[1] < 0:
        grade = "mid"; rules.append("shrink_rule")
    if grade == "solid" and lynch_type == "fast_grower" and R[3] == WEAK and fcf3 is not None and fcf3 < 0:
        grade = "mid"; rules.append("fast_grower_safety")

    # flags (never change the grade)
    if len(Y) >= 3 and all(e in op_cash and e in net for e in Y[-3:]):
        oc0, oc2 = op_cash[Y[-3]], op_cash[last]
        if oc0 > 0 and oc2 < 0.7 * oc0 and net[last] > net[Y[-3]]:
            flags.append("one_off: operating cash fell >30% in 2 years while net profit rose")
    if gain.get(last) and last in op and op[last] > 0 and gain[last] > 0.5 * op[last]:
        flags.append(f"one_off: gain on a sale {gain[last]/1e9:.1f} bn explains most of operating profit")
    fl = [fcf.get(e) for e in Y[-3:]]
    if None not in fl and fl[-1] < 0 and fl[0] > fl[1] > fl[2]:
        flags.append("fcf_falling: latest free cash negative and falling 3 years")
    for name, ser in (("liquid assets", liquid), ("debt", {e: v[0] for e, v in debt.items() if v[0]})):
        recent = Y[-4:]
        for a_, b_ in zip(recent, recent[1:]):
            if not (ser.get(a_) and ser.get(b_) is not None):
                continue
            ch = ser[b_] / ser[a_] - 1
            if (name == "liquid assets" and ch < -0.5) or (name == "debt" and abs(ch) > 0.3):
                flags.append(f"data_check: {name} {ser[a_]/1e9:.1f} → {ser[b_]/1e9:.1f} bn ({b_[:4]})")
    if debt[last][2]:
        flags.append("data_check: debt candidates disagree")
    for k in dec:
        if isinstance(k, int) and isinstance(M[k], float):
            for th in TH[k]:
                if th and abs(M[k] - th) <= 0.1 * abs(th):
                    flags.append(f"borderline: {NAMES[k]}")
                    break
    if "T" in dec and len(y5) >= 2:
        f5, d5 = sum(fcf[e] for e in y5), sum(divs[e] for e in y5)
        if d5 and abs(f5 - d5) <= 0.1 * d5:
            flags.append(f"borderline: dividend_cover (free cash {f5/1e9:.1f} vs dividends {d5/1e9:.1f} bn over 5 years)")
    if leases.get(last):
        notes.append(f"lease_heavy info: leases {leases[last]/1e9:.1f} bn (debt incl. leases {((debt_last or 0)+leases[last])/1e9:.1f} bn)")
    if acq.get(last):
        notes.append(f"acquisitive info: acquisitions {acq[last]/1e9:.1f} bn in the latest year")

    # price line (not part of the grade)
    price = {}
    if yh.get("market_cap"):
        fx = yh.get("fx", 1.0)
        mc = yh["market_cap"]
        if fcf3 is not None:
            price["fcf_yield"] = fcf3 * fx / mc
        if fcf.get(last) is not None:
            price["fcf_yield_latest"] = fcf[last] * fx / mc
        eps_old = eps.get(i3)
        for b_, kk in splits_applied:  # same split adjustment as the share count (shares ×k → EPS ÷k)
            if eps_old is not None and i3 < b_ <= last:
                eps_old /= kk
        ge = cagr(eps_old, eps.get(last), n3)
        pe = mc / (net[last] * fx) if net.get(last) and net[last] > 0 else None  # P/E on the latest fiscal year
        div_yield = divs[last] * fx / mc if divs.get(last) else None
        if pe:
            price["pe"] = pe
        if pe and ge and ge > 0:
            gcap = min(ge, 0.25)
            price["peg"] = pe / (gcap * 100)
            price["eps_growth_3y"] = ge
            if div_yield:
                price["lynch_dividend_ratio"] = (gcap * 100 + div_yield * 100) / pe

    return dict(t=t, tax=c.tax, unit=c.unit, sic=c.sic, last=last, Y=Y, lynch_type=lynch_type, grade=grade, rules=rules,
                M=M, R=R, N=N, dec=dec, marks=marks, flags=flags, notes=notes, price=price, fcf=fcf, fcf3=fcf3,
                liquid=liquid, debt=debt, roce=roce)


def fmt(k, v):
    if v is None:
        return "—"
    special = {"NN": "cash > debt", "FCF-": "no cash generation, has debt", "FCF+": "generates cash",
               "POS": "just turned to profit", "NEG": "loss then and now"}
    if v in special:
        return special[v]
    if k == 2:
        return f"{v:+.1f} pt"
    if k in (6, 7, 10):
        return f"{v:.1f}"
    return f"{v*100:+.1f}%" if k in (1, 8, 9) else f"{v*100:.1f}%"


def load_yahoo():
    return json.load(open("yahoo.json")) if os.path.exists("yahoo.json") else {}


if __name__ == "__main__":
    yahoo = load_yahoo()
    for t in sys.argv[1:]:
        r = analyse(t, yahoo)
        extra = f" ({', '.join(r['rules'])})" if r["rules"] else ""
        print(f"\n===== {t} · {r['tax']} {r['unit']} · SIC {r['sic']} · latest {r['last']} · {r['lynch_type']} → {r['grade'].upper()}{extra}")
        for k in range(1, 11):
            dm = "◆" if k in r["dec"] else " "
            print(f"  {dm} {k:>2} {NAMES[k]:20s} {r['R'][k] or NONE} {fmt(k, r['M'][k]):28s} {r['N'].get(k, '')}")
        for k in ("B", "T"):
            dm = "◆" if k in r["dec"] else " "
            print(f"  {dm} {k:>2} {NAMES[k]:20s} {r['R'][k]}")
        f3 = "—" if r["fcf3"] is None else f"{r['fcf3']/1e9:.2f} bn"
        print(f"     free cash 3y avg: {f3}"
              f" · liquid: {r['liquid'].get(r['last'], 0)/1e9:.2f} bn · debt: {(r['debt'][r['last']][0] or 0)/1e9:.2f} bn")
        if r["price"]:
            p = r["price"]
            print("     price: " + " · ".join(f"{k} {v:.2f}" if k in ("pe", "peg", "lynch_dividend_ratio") else f"{k} {v*100:.1f}%"
                                         for k, v in p.items()))
        for x in r["flags"] + r["notes"]:
            print(f"     ⚑ {x}")
