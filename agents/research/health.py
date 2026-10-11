"""quick_health (roadmap, "Score rules" 5): is it worth spending money on agent 3's deep analysis? Five loose checks from SEC's
annual figures, computed with agent 3's numbers (`Result.series`), so the free-cash definition is the same everywhere.

A check that cannot be computed is `unclear`: it is not a fail and it is left out of the arithmetic (missing data ≠ bad)."""

from __future__ import annotations

from dataclasses import dataclass, field

SPLIT_RATIOS = (2, 3, 4, 5, 8, 10, 20)
CHECKS = ("profit", "cash", "shrink", "debt", "dilution")
LABEL = {"profit": "Profit", "cash": "Cash", "shrink": "Shrink", "debt": "Debt", "dilution": "Dilution"}


@dataclass
class Health:
    checks: list = field(default_factory=list)     # {name, status: pass|fail|unclear, detail}
    points: int = 1
    reason: str = ""

    def status(self, name: str) -> str:
        return next(c["status"] for c in self.checks if c["name"] == name)


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def _looks_like_split(a: float, b: float) -> bool:
    if not a or not b:
        return False
    ratio = b / a
    return any(abs(ratio - k) / k < 0.06 or abs(ratio - 1 / k) * k < 0.06 for k in SPLIT_RATIOS)


def _bn(x: float) -> str:
    return f"{x / 1e9:.2f} bn"


def run_checks(series: dict) -> list[dict]:
    ends = series.get("ends") or []
    rev, op, fcf = series.get("revenue", {}), series.get("operating", {}), series.get("fcf", {})
    shares, debt, liquid = series.get("shares", {}), series.get("debt", {}), series.get("liquid", {})
    if not ends:
        return [_check(n, "unclear", "no annual figures") for n in CHECKS]
    last = ends[-1]
    first3 = ends[-4] if len(ends) >= 4 else None
    out = []

    # Profit: the latest year's operating profit is above zero
    if last in op:
        out.append(_check("profit", "pass" if op[last] > 0 else "fail", f"operating profit {_bn(op[last])} in {last[:4]}"))
    else:
        out.append(_check("profit", "unclear", f"operating profit {last[:4]} was not found"))

    # Cash: free cash flow above zero in at least 2 of the last 3 years
    years = ends[-3:]
    known = [fcf[e] for e in years if e in fcf]
    positive = sum(1 for v in known if v > 0)
    best = positive + (len(years) - len(known))
    path = ", ".join(f"{e[:4]} {_bn(fcf[e])}" for e in years if e in fcf)
    if positive >= 2:
        out.append(_check("cash", "pass", f"free cash flow above zero in {positive} of the last 3 years ({path})"))
    elif best < 2:
        out.append(_check("cash", "fail", f"free cash flow above zero in {positive} of the last 3 years ({path or 'no figures'})"))
    else:
        out.append(_check("cash", "unclear", f"free cash flow is missing for {len(years) - len(known)} of the last 3 years ({path})"))

    # Shrink: revenue grew over 3 years
    if first3 and first3 in rev and last in rev and rev[first3] > 0:
        grew = rev[last] > rev[first3]
        out.append(_check("shrink", "pass" if grew else "fail",
                          f"revenue {_bn(rev[first3])} ({first3[:4]}) → {_bn(rev[last])} ({last[:4]})"))
    else:
        out.append(_check("shrink", "unclear", "revenue for a 3-year comparison was not found"))

    # Debt: net debt / free cash flow below 4 years, or cash greater than debt
    d, liq = debt.get(last), liquid.get(last)
    fcf3 = [fcf[e] for e in ends[-3:] if e in fcf]
    avg = sum(fcf3) / len(fcf3) if len(fcf3) >= 2 else None
    if d is None:
        out.append(_check("debt", "unclear", "debt was not found"))
    elif d == 0:
        out.append(_check("debt", "pass", "no debt"))
    elif liq is not None and liq > d:
        out.append(_check("debt", "pass", f"cash and investments {_bn(liq)} are more than debt {_bn(d)}"))
    elif avg is None or liq is None:
        out.append(_check("debt", "unclear", f"debt {_bn(d)}; the cash or the free cash flow needed to judge it was not found"))
    elif avg <= 0:
        out.append(_check("debt", "fail", f"debt {_bn(d)} is more than cash {_bn(liq)} and free cash flow is not positive"))
    else:
        years_to_pay = (d - liq) / avg
        out.append(_check("debt", "pass" if years_to_pay < 4 else "fail",
                          f"net debt {_bn(d - liq)} is {years_to_pay:.1f} years of free cash flow"))

    # Dilution: the share count has not risen by more than 10% in 3 years (a split-sized jump is not dilution)
    if first3 and first3 in shares and last in shares and shares[first3] > 0:
        window = [e for e in ends if first3 <= e <= last and e in shares]
        if any(_looks_like_split(shares[a], shares[b]) for a, b in zip(window, window[1:])):
            out.append(_check("dilution", "unclear", "the share count jumps like a split; not judged"))
        else:
            change = shares[last] / shares[first3] - 1
            out.append(_check("dilution", "pass" if change <= 0.10 else "fail", f"share count {change:+.1%} in 3 years"))
    else:
        out.append(_check("dilution", "unclear", "the share count for a 3-year comparison was not found"))
    return out


def points_for(checks: list[dict]) -> int:
    computed = [c for c in checks if c["status"] != "unclear"]
    n, passed = len(computed), sum(1 for c in computed if c["status"] == "pass")
    if n < 3:
        return 1                               # unclear: neither reward nor penalty
    if n == 5:
        return 0 if passed <= 2 else 1 if passed <= 4 else 2
    short = n - passed
    return 2 if short == 0 else 1 if short == 1 else 0


def reason_text(checks: list[dict], points: int) -> str:
    computed = [c for c in checks if c["status"] != "unclear"]
    if len(computed) < 3:
        gaps = "; ".join(f"{LABEL[c['name']]}: {c['detail']}" for c in checks if c["status"] == "unclear")
        return f"unclear — only {len(computed)} of 5 checks could be computed ({gaps})"
    passed = [LABEL[c["name"]] for c in computed if c["status"] == "pass"]
    failed = [LABEL[c["name"]] for c in computed if c["status"] == "fail"]
    text = f"{len(passed)} of {len(computed)} computed checks passed"
    if failed:
        text += "; failed: " + ", ".join(f"{LABEL[c['name']]} ({c['detail']})" for c in computed if c["status"] == "fail")
    unclear = [LABEL[c["name"]] for c in checks if c["status"] == "unclear"]
    if unclear:
        text += "; not computed: " + ", ".join(unclear)
    return text


def quick_health(result) -> Health:
    """`result`: agent 3's `Result` (an out-of-scope company has no series: everything is unclear)."""
    series = getattr(result, "series", None) or {}
    checks = run_checks(series)
    points = points_for(checks)
    reason = reason_text(checks, points)
    if getattr(result, "out_of_scope", None):
        reason = f"unclear — out of scope for the analysis: {result.out_of_scope}"
    return Health(checks, points, reason)
