"""Agent 3 — the numbers (roadmap section 3, "Agent 3 rules"). Code measures and raises questions; it does not judge.

    result = analyse(facts, ticker, market)

Everything here is arithmetic on SEC figures (`shared.sec.facts`) plus Yahoo's split history, market value and FX
(`Market`). No AI. A value that cannot be computed is None (`not_computed` on the card); missing is never zero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from shared import sectors
from shared.sec.facts import Facts

NAMES = {1: "revenue_growth_3y", 2: "margin_stability", 3: "operating_margin", 4: "capital_return",
         5: "cash_conversion", 6: "interest_cover", 7: "debt_years", 8: "share_count", 9: "gross_profit_growth",
         10: "cash_runway", "B": "debt", "T": "dividend_cover"}
UNITS = {1: "ratio", 2: "pp", 3: "ratio", 4: "ratio", 5: "ratio", 6: "times", 7: "years", 8: "ratio", 9: "ratio",
         10: "years"}

# Thresholds: (✅ from, ➖ from); higher is better unless listed in LOWER_BETTER.
TH = {1: (.15, .08), 2: (-1, -3), 3: (.15, .05), 4: (.15, .08), 5: (.80, .50), 6: (8, 3), 7: (3, 5), 8: (0, .10),
      9: (.20, .10), 10: (3, 1.5)}
LOWER_BETTER = {7, 8}
TH10_STRICT = (5, 3)  # 10*: a fast grower that does not produce cash from the business

DECISIVE = {"stalwart": [2, 3, 4, 5], "fast_grower": [1, 9, 2, 10, 8], "slow_grower": [2, 4, 5, "B", "T"],
            "cyclical": [4, "B", 8], "unprofitable": [2, 3, 4, 5]}

GOOD, MID, WEAK = "good", "mid", "weak"
SPECIAL_TEXT = {"cash_over_debt": "cash > debt", "produces_cash": "the business produces cash",
                "no_cash_with_debt": "does not produce cash from the business, and has debt (research item)",
                "just_turned_profit": "just turned from a loss to a profit", "loss_then_and_now": "a loss 3 years ago and now"}
ORDER = [WEAK, MID, GOOD]
SPLIT_RATIOS = (2, 3, 4, 5, 8, 10, 20)


@dataclass
class Market:
    """What Yahoo gives: split history (None = Yahoo did not answer), market value in USD, price, FX to USD."""
    splits: list[tuple[str, float]] | None = None
    market_value: float | None = None
    price: float | None = None
    fx: float | None = 1.0
    as_of: str | None = None


@dataclass
class Result:
    ticker: str
    name: str | None
    taxonomy: str
    currency: str
    sic: int | None
    sector: str
    out_of_scope: str | None
    ends: list[str]
    last: str | None
    ttm: bool
    lynch_type: str | None = None
    grade: str = "unclear"
    rules: list[str] = field(default_factory=list)
    measures: dict = field(default_factory=dict)   # name → {value, mark, decisive, unit, xbrl, note}
    flags: list[dict] = field(default_factory=list)  # {flag, detail}
    notes: list[str] = field(default_factory=list)
    price: dict = field(default_factory=dict)
    free_cash: dict = field(default_factory=dict)
    figures: dict = field(default_factory=dict)    # figure → {end: Value} (for `financials` and the trace)
    missing: list[dict] = field(default_factory=list)
    liquid: dict = field(default_factory=dict)
    debt: dict = field(default_factory=dict)


def _avg(vals, need=2):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if len(vals) >= need else None


def _years(a: str, b: str) -> float:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days / 365.25


def _cagr(a, b, years):
    if a is None or b is None or a <= 0 or b <= 0 or years <= 0:
        return None
    return (b / a) ** (1 / years) - 1


def _mark(k, v, strict10=False):
    if v is None:
        return None
    good, mid = TH10_STRICT if (k == 10 and strict10) else TH[k]
    if k in LOWER_BETTER:
        return GOOD if v <= good else (MID if v <= mid else WEAK)
    return GOOD if v >= good else (MID if v >= mid else WEAK)


def _vals(series: dict) -> dict:
    return {e: v.value for e, v in series.items()}


# figures whose absence goes to the `missing_data` ledger (the ones the measures need)
LEDGER_FIGURES = ("revenue", "net", "op_cash", "capex", "stock_comp", "cash", "assets", "current_liabilities", "shares",
                  "debt")


def analyse(facts: Facts, ticker: str, market: Market | None = None) -> Result:
    market = market or Market()
    Y = facts.ends
    r = Result(ticker=ticker.upper(), name=facts.name, taxonomy=facts.taxonomy, currency=facts.currency, sic=facts.sic,
               sector=sectors.sector_for(facts.sic, ticker), out_of_scope=None, ends=list(Y),
               last=Y[-1] if Y else None, ttm=bool(facts.ttm_end))
    get = facts.annual
    rev_s = get("revenue")
    r.figures["revenue"] = rev_s

    # --- out of scope (approach 2; decision 2026-10-05) -----------------------------------------------------------------
    label = sectors.out_of_scope_for(facts.sic)
    if label is None and facts.annual_ends and not any(e in rev_s for e in facts.annual_ends[-3:]):
        label = "pre_revenue"
    if label or not Y:
        r.out_of_scope = label
        r.grade = "unclear"
        r.missing = [m for m in facts.misses if m["figure"] == "revenue" and m["end"] in facts.annual_ends[-3:]]
        if not Y:
            r.notes.append("no annual figures found in SEC data")
        return r

    rev = _vals(rev_s)
    cost, gross = _vals(get("cost")), _vals(get("gross"))
    op_rep, pretax, tax, net = _vals(get("operating")), _vals(get("pretax")), _vals(get("tax")), _vals(get("net"))
    interest_s = get("interest")
    interest = _vals(interest_s)
    net_int, int_inc = _vals(get("net_interest_income")), _vals(get("interest_income"))
    op_cash, capex, sbc = _vals(get("op_cash")), _vals(get("capex")), _vals(get("stock_comp"))
    assets, cur_liab, liab = _vals(get("assets")), _vals(get("current_liabilities")), _vals(get("liabilities"))
    shares, divs, eps = _vals(get("shares")), _vals(get("dividends")), _vals(get("eps"))
    gain, acq, leases = _vals(get("gain_on_sale")), _vals(get("acquisitions")), _vals(get("leases"))
    liquid_s, debt_s = facts.liquid(), facts.debt()
    liquid = _vals(liquid_s)
    debt = {e: d.value for e, d in debt_s.items()}
    r.liquid, r.debt = liquid_s, debt_s
    for fig in ("cost", "gross", "operating", "pretax", "tax", "net", "interest", "op_cash", "capex", "stock_comp",
                "assets", "current_liabilities", "liabilities", "shares", "dividends", "eps", "cash",
                "short_term_investments", "marketable_securities"):
        r.figures[fig] = get(fig)
    flags, notes = r.flags, r.notes

    # --- consistency checks: a sudden drop to zero / a 10-times jump in revenue is flagged and not used -----------------
    for a_, b_ in zip(Y, Y[1:]):
        if rev.get(a_) and b_ in rev:
            ratio = rev[b_] / rev[a_] if rev[a_] else None
            if rev[b_] == 0 or (ratio is not None and (ratio > 10 or ratio < 0.1)):
                flags.append({"flag": "data_check", "detail": f"revenue {rev[a_]/1e9:.2f} → {rev[b_]/1e9:.2f} bn ({b_[:4]}); not used"})
                rev.pop(b_)
    for e in Y:  # gross profit = revenue − cost
        if e in gross and e in rev and e in cost and rev[e] and abs(gross[e] - (rev[e] - cost[e])) > 0.02 * abs(rev[e]):
            flags.append({"flag": "data_check", "detail": f"gross profit ≠ revenue − cost ({e[:4]})"})
        if e not in gross and e in rev and e in cost:
            gross[e] = rev[e] - cost[e]

    # operating profit: reported, otherwise pre-tax − net interest income (approximate), otherwise not computed
    for e in Y:
        if e not in net_int and e in int_inc and e in interest:
            net_int[e] = int_inc[e] - interest[e]
    op, op_src = {}, {}
    for e in Y:
        if e in op_rep:
            op[e], op_src[e] = op_rep[e], "reported"
        elif e in pretax and e in net_int:
            op[e], op_src[e] = pretax[e] - net_int[e], "approximate: pre-tax − net interest income"

    fcf = {e: op_cash[e] - capex[e] - sbc[e] for e in Y if e in op_cash and e in capex and e in sbc}
    last = Y[-1]
    i3 = Y[-4] if len(Y) >= 4 else Y[0]
    n3 = _years(i3, last)
    fcf3 = _avg([fcf.get(e) for e in Y[-3:]])
    debt_last = debt.get(last)
    r.free_cash = {"value": fcf.get(last), "average_3y": fcf3, "stock_comp": sbc.get(last),
                   "path_5y": {e: fcf.get(e) for e in Y[-5:]}}

    M, N, X = {}, {}, {}  # values, notes, source names
    # 1 revenue growth (3-year average annual)
    M[1] = _cagr(rev.get(i3), rev.get(last), n3)
    X[1] = rev_s[last].tag if last in rev_s else None

    # 2 margin stability: the worse of (latest − previous 4-year average) and (latest − previous year), in points
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
    M[2] = None
    if len(ys) >= 3 and ys[-1] == last:
        prev_avg = _avg([mg[e] for e in ys[:-1]])
        M[2] = min((mg[last] - prev_avg) * 100, (mg[last] - mg[ys[-2]]) * 100)
        N[2] = f"{kind} margin {mg[last]*100:.1f}% (previous years' average {prev_avg*100:.1f}%, previous year {mg[ys[-2]]*100:.1f}%)"
    # 3 operating margin
    M[3] = op[last] / rev[last] if last in op and rev.get(last) else None
    N[3] = op_src.get(last, "not reported, no net-interest figure")
    X[3] = r.figures["operating"][last].tag if last in r.figures["operating"] else None

    # 4 capital return per year = operating profit × (1 − tax rate) ÷ (total assets − current liabilities − liquid)
    roce = {}
    for e in Y[-5:]:
        if e not in op or e not in assets or e not in cur_liab or e not in liquid:
            continue
        p, tx = pretax.get(e), tax.get(e)
        rate = min(max(tx / p, 0), 0.35) if p and p > 0 and tx is not None else 0.21
        tied_up = assets[e] - cur_liab[e] - liquid[e]
        if tied_up > 0:
            roce[e] = op[e] * (1 - rate) / tied_up
    r5 = _avg([roce.get(e) for e in Y[-5:]], need=3)
    r3 = _avg([roce.get(e) for e in Y[-3:]])

    # 5 cash conversion (3 years): free cash ÷ net profit; not computed if net profit ≤ 0
    yy = [e for e in Y[-3:] if e in fcf and e in net]
    sn = sum(net[e] for e in yy)
    M[5] = sum(fcf[e] for e in yy) / sn if len(yy) >= 2 and sn > 0 else None
    if len(yy) >= 2 and sn <= 0:
        N[5] = "net profit ≤ 0"

    # 6 interest cover — not required if cash > debt; cash interest paid is never used
    cash_over_debt = last in liquid and debt_last is not None and liquid[last] >= debt_last
    special = {}
    if cash_over_debt:
        M[6], special[6], N[6] = None, "cash_over_debt", "cash > debt"
    elif interest.get(last) and last in op:
        M[6], X[6] = op[last] / interest[last], interest_s[last].tag
    else:
        M[6], N[6] = None, "interest expense not found"

    # 7 debt years = net debt ÷ free cash (3-year average)
    M[7] = None
    if debt_last is not None and last in liquid:
        if debt_last - liquid[last] <= 0:
            special[7] = "cash_over_debt"
        elif fcf3 is not None and fcf3 <= 0:
            special[7] = "no_cash_with_debt"
            N[7] = "does not produce cash from the business, and has debt (research item)"
        elif fcf3 is not None:
            M[7] = (debt_last - liquid[last]) / fcf3
    if last in debt_s:
        X[7] = debt_s[last].tag

    # 8 share count (5 years): the IPO year is skipped; splits both ways adjusted only if Yahoo confirms them
    hy = [e for e in Y if e in shares]
    if facts.first_fy and hy and int(hy[0][:4]) <= facts.first_fy:
        hy = [e for e in hy if int(e[:4]) > facts.first_fy]
    hy = hy[-6:]
    adj = dict(shares)
    confirmed = []
    if market.splits is not None and Y:
        window = date.fromordinal(date.fromisoformat(Y[0]).toordinal() - 400).isoformat()
        confirmed = [ratio for d_, ratio in market.splits if d_ >= window]
    split_bad, split_notes, applied = False, [], []
    for a_, b_ in zip(hy, hy[1:]):
        if not adj.get(a_):
            continue
        ratio = adj[b_] / adj[a_]
        for k in SPLIT_RATIOS:
            hit = next((kk for kk in (k, 1 / k) if abs(ratio - kk) / kk < 0.06), None)
            if hit is None:
                continue
            if any(abs(x - hit) / hit < 0.06 for x in confirmed):
                for e in hy[:hy.index(b_)]:
                    adj[e] *= hit
                applied.append((b_, hit))
                split_notes.append(f"split ×{hit:g} adjusted (Yahoo confirmed)")
            else:
                split_bad = True
                split_notes.append(f"jump ×{hit:g} not confirmed by Yahoo")
            break
    M[8] = None if split_bad or len(hy) < 2 else adj[hy[-1]] / adj[hy[0]] - 1
    if hy:
        N[8] = f"{hy[0][:4]}→{hy[-1][:4]}" + ("; " + ", ".join(split_notes) if split_notes else "")
    if split_bad:
        flags.append({"flag": "data_check", "detail": "share-count jump not confirmed by Yahoo (possible merger)"})

    # 9 gross-profit growth
    a9, b9 = gross.get(i3), gross.get(last)
    M[9] = _cagr(a9, b9, n3)
    if M[9] is None and a9 is not None and b9 is not None:
        if a9 <= 0 < b9:
            special[9], N[9] = "just_turned_profit", "just turned from a loss to a profit"
        elif a9 <= 0 and b9 <= 0:
            special[9], N[9] = "loss_then_and_now", "a loss 3 years ago and now"

    # 10 cash runway = cash on hand ÷ annual cash burn (3-year average)
    M[10] = None
    if fcf3 is not None and fcf3 >= 0:
        special[10] = "produces_cash"
    elif fcf3 is not None and last in liquid:
        M[10] = liquid[last] / -fcf3
        if debt_last and debt_last > liquid[last]:
            notes.append("part of the cash on hand is debt")

    # --- type (Lynch; the first rule that matches wins) ------------------------------------------------------------------
    years = []
    for e in Y[-5:]:
        v = op.get(e)
        if v is None:
            v = pretax.get(e)  # the sign only
        if v is not None:
            years.append(v > 0)
    profits, losses = years.count(True), years.count(False)
    cyc_sector = r.sector in ("Energy", "Materials") or sectors.is_cyclical_sic(facts.sic)
    if len(years) < 3:
        lynch_type = None
    elif (cyc_sector and profits >= 1) or (profits and losses):
        lynch_type = "cyclical"
    elif profits < 4 and fcf3 is not None and fcf3 < 0:
        lynch_type = "unprofitable"
    elif M[1] is not None and M[1] >= .15:
        lynch_type = "fast_grower"
    elif profits < 4:
        lynch_type = "unprofitable"
    elif M[1] is not None and M[1] >= .05:
        lynch_type = "stalwart"
    elif M[1] is not None:
        lynch_type = "slow_grower"
    else:
        lynch_type = None
    r.lynch_type = lynch_type

    M[4] = r5 if lynch_type == "cyclical" else (min(r3, r5) if r3 is not None and r5 is not None else r5)
    if r3 is not None and r5 is not None:
        N[4] = f"3-year {r3*100:.1f}% · 5-year {r5*100:.1f}%"

    # --- marks ------------------------------------------------------------------------------------------------------------
    strict10 = lynch_type == "fast_grower" and fcf3 is not None and fcf3 < 0
    R = {k: _mark(k, M[k], strict10) for k in range(1, 11)}
    if special.get(6) == "cash_over_debt":
        R[6] = GOOD
    if special.get(7) == "cash_over_debt":
        R[7] = GOOD
    elif special.get(7) == "no_cash_with_debt":
        R[7] = WEAK
    if special.get(9) == "just_turned_profit":
        R[9] = MID
    elif special.get(9) == "loss_then_and_now":
        R[9] = WEAK
    if special.get(10) == "produces_cash":
        R[10] = GOOD
    # debt (6 + 7 together): the interest-cover mark is the base; a ❌ paydown time takes it one step down
    R["B"] = R[6] if R[6] is not None else R[7]
    if R["B"] is not None and R[6] is not None and R[7] == WEAK:
        R["B"] = ORDER[max(ORDER.index(R["B"]) - 1, 0)]
    # T dividend covered by cash (5-year total)
    y5 = [e for e in Y[-5:] if e in fcf and e in divs]
    R["T"] = None
    if divs and len(y5) >= 2:
        f5, d5 = sum(fcf[e] for e in y5), sum(divs[e] for e in y5)
        R["T"] = GOOD if f5 >= d5 else WEAK
        N["T"] = f"free cash {f5/1e9:.2f} vs dividends {d5/1e9:.2f} bn over {len(y5)} years"

    # --- grade ------------------------------------------------------------------------------------------------------------
    dec = DECISIVE.get(lynch_type, [])
    marks = [R[k] for k in dec]
    if lynch_type is None:
        grade = "unclear"
    else:
        computed = [m for m in marks if m is not None]
        if len(computed) * 2 < len(marks):
            grade = "unclear"
        elif marks.count(WEAK) >= 2:
            grade = "weak"
        elif marks.count(WEAK) == 0 and marks.count(GOOD) * 2 >= len(marks):
            grade = "solid"
        else:
            grade = "mid"
    if grade == "solid" and M[1] is not None and M[1] < 0:
        grade = "mid"
        r.rules.append("shrink_rule")
    if grade == "solid" and lynch_type == "fast_grower" and R[3] == WEAK and fcf3 is not None and fcf3 < 0:
        grade = "mid"
        r.rules.append("fast_grower_safety")
    r.grade = grade

    for k in list(range(1, 11)) + ["B", "T"]:
        r.measures[NAMES[k]] = {"value": M.get(k), "mark": R[k], "decisive": k in dec, "unit": UNITS.get(k),
                                "xbrl": X.get(k), "note": N.get(k) or SPECIAL_TEXT.get(special.get(k))}

    # --- flags (they never change the grade) -------------------------------------------------------------------------------
    if len(Y) >= 3 and all(e in op_cash and e in net for e in Y[-3:]):
        oc0, oc2 = op_cash[Y[-3]], op_cash[last]
        if oc0 > 0 and oc2 < 0.7 * oc0 and net[last] > net[Y[-3]]:
            flags.append({"flag": "one_off", "detail": "operating cash fell more than 30% in 2 years while net profit rose"})
    if gain.get(last) and last in op and op[last] > 0 and gain[last] > 0.5 * op[last]:
        flags.append({"flag": "one_off", "detail": f"a gain on a sale ({gain[last]/1e9:.1f} bn) explains most of operating profit"})
    fl = [fcf.get(e) for e in Y[-3:]]
    if len(fl) == 3 and None not in fl and fl[-1] < 0 and fl[0] > fl[1] > fl[2]:
        flags.append({"flag": "fcf_falling", "detail": "latest free cash negative and falling for 3 years"})
    recent = Y[-4:]
    for a_, b_ in zip(recent, recent[1:]):
        if liquid.get(a_) and b_ in liquid and liquid[b_] / liquid[a_] - 1 < -0.5:
            flags.append({"flag": "data_check", "detail": f"liquid assets {liquid[a_]/1e9:.1f} → {liquid[b_]/1e9:.1f} bn ({b_[:4]})"})
        if debt.get(a_) and b_ in debt:
            if debt[b_] == 0:
                flags.append({"flag": "data_check", "detail": f"debt dropped to zero ({b_[:4]})"})
            elif abs(debt[b_] / debt[a_] - 1) > 0.3:
                flags.append({"flag": "data_check", "detail": f"debt {debt[a_]/1e9:.1f} → {debt[b_]/1e9:.1f} bn ({b_[:4]})"})
    if last in debt_s and debt_s[last].disagree:
        flags.append({"flag": "data_check", "detail": "debt candidates disagree: "
                      + " / ".join(f"{c/1e9:.1f}" for c in debt_s[last].candidates) + " bn"})
    if debt_last is not None and liab.get(last) and debt_last > liab[last]:
        flags.append({"flag": "data_check", "detail": "debt is larger than total liabilities"})
    for k in dec:
        if isinstance(k, int) and isinstance(M.get(k), float):
            for th in TH[k]:
                if th and abs(M[k] - th) <= 0.1 * abs(th):
                    flags.append({"flag": "borderline", "detail": NAMES[k]})
                    break
    if "T" in dec and len(y5) >= 2:
        f5, d5 = sum(fcf[e] for e in y5), sum(divs[e] for e in y5)
        if d5 and abs(f5 - d5) <= 0.1 * d5:
            flags.append({"flag": "borderline", "detail": "dividend_cover"})
    if leases.get(last):
        notes.append(f"lease_heavy: leases {leases[last]/1e9:.1f} bn (debt including leases "
                     f"{((debt_last or 0) + leases[last])/1e9:.1f} bn)")
    if acq.get(last):
        notes.append(f"acquisitive: {acq[last]/1e9:.1f} bn spent on acquisitions in the latest year")

    # --- price line (never part of the grade) ------------------------------------------------------------------------------
    r.price = price_line(market, fcf3, fcf.get(last), net.get(last), divs.get(last), eps, i3, last, n3, applied)

    # --- the ledger: figures the measures needed and did not find ----------------------------------------------------------
    window = set(Y[-5:])
    wanted = set(LEDGER_FIGURES)
    if not cash_over_debt and last not in interest:
        wanted.add("interest")
    if any(e not in op for e in window):
        wanted.add("operating")
    r.missing = [m for m in facts.misses if m["figure"] in wanted and m["end"] in window]
    return r


def price_line(market: Market, fcf3, fcf_last, net_last, div_last, eps, i3, last, n3, applied) -> dict:
    """PEG (EPS growth capped at 25%), Lynch's dividend ratio, FCF yield on the 3-year average. Market value = Yahoo's
    (decision 2026-10-05); without it everything here stays `not_computed`."""
    out = {"price": market.price, "market_value": market.market_value, "fx": market.fx, "as_of": market.as_of,
           "pe": None, "peg": None, "eps_growth_3y": None, "lynch_dividend_ratio": None, "fcf_yield": None,
           "fcf_yield_latest": None}
    mv, fx = market.market_value, market.fx
    if not mv or not fx:
        return out
    if fcf3 is not None:
        out["fcf_yield"] = fcf3 * fx / mv
    if fcf_last is not None:
        out["fcf_yield_latest"] = fcf_last * fx / mv
    eps_old = eps.get(i3)
    for b_, k in applied:  # the same split adjustment as the share count (shares ×k → EPS ÷k)
        if eps_old is not None and i3 < b_ <= last:
            eps_old /= k
    growth = _cagr(eps_old, eps.get(last), n3)
    pe = mv / (net_last * fx) if net_last and net_last > 0 else None
    out["pe"] = pe
    out["eps_growth_3y"] = growth
    if pe and growth and growth > 0:
        g = min(growth, 0.25) * 100
        out["peg"] = pe / g
        if div_last:
            out["lynch_dividend_ratio"] = (g + div_last * fx / mv * 100) / pe
    return out


def verdicts(price: dict) -> dict:
    """attractive / fair / expensive for each price measure (roadmap section 3)."""
    def v(x, good, ok, higher_better):
        if x is None:
            return None
        if higher_better:
            return "attractive" if x >= good else ("fair" if x >= ok else "expensive")
        return "attractive" if x <= good else ("fair" if x <= ok else "expensive")
    return {"peg": v(price.get("peg"), 1, 2, False),
            "lynch_dividend_ratio": v(price.get("lynch_dividend_ratio"), 2, 1, True),
            "fcf_yield": v(price.get("fcf_yield"), 0.05, 0.02, True)}
