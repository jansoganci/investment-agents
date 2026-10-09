"""Read figures out of SEC companyfacts, with a trace for every figure (roadmap section 3, "SEC data — synonym method").

    f = Facts(company_facts_json, submissions_json)
    f.ends                     the year ends looked at: up to 6 annual year ends + the last 4 quarters (TTM) if newer
    f.annual("revenue")        {end: Value} — each year tries the synonym list in order (a renamed tag is caught)
    f.instant("cash", end)     a balance-sheet figure at a year end (TTM point: the latest quarter)
    f.liquid()                 cash + short-term investments + current marketable securities (parts added)
    f.debt()                   the first complete debt group + short-term borrowings; the other candidates are a check
    f.misses                   figures not found: year, figure, names tried (→ `missing_data`)

Missing is not zero: a figure that is not found is simply absent (None), never 0.

The last 4 quarters (TTM, US filers with a 10-Q newer than the last annual report): a flow figure = the last annual figure +
this year-to-date − last year's same period (= the 4 latest quarters summed; Q4 is the year minus 9 months). SEC reports cash
flow cumulatively, so this works for every flow figure. Balance-sheet figures come from the latest quarter. 20-F filers are
annual only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from shared.sec import FORMS_ANNUAL, FORMS_QUARTER
from shared.sec.synonyms import DEBT_GROUPS, INSTANT, SHORT_TERM_DEBT, SYNONYMS, UNIT_KIND, debt_balance_names

SAME_DAY = 10  # fiscal-year ends less than 10 days apart are the same year (52/53-week years)


def _d(s: str) -> date:
    return date.fromisoformat(s)


def _days(a: str, b: str) -> int:
    return (_d(b) - _d(a)).days


@dataclass
class Value:
    value: float
    tag: str
    form: str
    accn: str | None
    end: str
    filed: str = ""
    parts: dict = field(default_factory=dict)  # for sums: tag → value
    ttm: dict = field(default_factory=dict)  # for the last 4 quarters: annual, ytd, ytd_previous_year

    @property
    def tags(self) -> list[str]:
        return list(self.parts) if self.parts else [self.tag]


class Facts:
    def __init__(self, companyfacts: dict, submissions: dict | None = None, quarters: bool = True,
                 user_values: dict | None = None):
        """`user_values`: {(figure, year): value} I entered with /data — used only where SEC has nothing (source: user)."""
        self.user_values = user_values or {}
        all_facts = companyfacts.get("facts", {})
        known = {tax: sum(1 for n in all_facts.get(tax, {}) if n in _names(tax)) for tax in SYNONYMS}
        self.taxonomy = max(known, key=known.get)
        self.raw = all_facts.get(self.taxonomy, {})
        self.syn = SYNONYMS[self.taxonomy]
        self.currency = self._currency()
        self.sic = int(submissions["sic"]) if submissions and str(submissions.get("sic") or "").isdigit() else None
        self.name = (submissions or {}).get("name") or companyfacts.get("entityName")
        fys = [r["fy"] for body in self.raw.values() for rows in body["units"].values() for r in rows
               if r.get("form") in FORMS_ANNUAL and r.get("fy")]
        self.first_fy = min(fys) if fys else None
        latest = max(((r.get("filed", ""), r.get("accn")) for body in self.raw.values() for rows in body["units"].values()
                      for r in rows if r.get("form") in FORMS_ANNUAL | FORMS_QUARTER), default=("", None))
        self.latest_accn = latest[1]  # the newest filing whose figures are in SEC's data
        self.misses: list[dict] = []
        self._cache: dict = {}
        self.annual_ends = self._annual_ends()
        has_quarters = any(r.get("form") in FORMS_QUARTER for body in self.raw.values()
                           for rows in body["units"].values() for r in rows)
        self.annual_only = not has_quarters
        self.ttm_end = self._ttm_end() if quarters and has_quarters else None
        # the last 4 quarters take the place of the last annual report they overlap (decision 2026-10-05): sums, averages
        # and "previous year" never count the same months twice
        self.ends = (self.annual_ends[:-1] + [self.ttm_end]) if self.ttm_end else list(self.annual_ends)
        self.newer_filing = self._newer_filing(submissions)

    # --- basics -----------------------------------------------------------------------------------------------------

    def _currency(self) -> str:
        for tag in self.syn["revenue"] + self.syn["net"]:
            units = self.raw.get(tag, {}).get("units", {})
            if units:
                return max(units, key=lambda u: len(units[u]))
        return "USD"

    def _unit(self, figure: str) -> str:
        kind = UNIT_KIND.get(figure)
        if kind == "shares":
            return "shares"
        if kind == "per_share":
            return f"{self.currency}/shares"
        return self.currency

    def _rows(self, tag: str, unit: str) -> list[dict]:
        return self.raw.get(tag, {}).get("units", {}).get(unit, [])

    def _newer_filing(self, submissions: dict | None) -> dict | None:
        """The newest 10-K / 10-Q / 20-F in the filing list when its figures are not in SEC's data yet (roadmap rule 43:
        Coca-Cola, Dow and Visa, 2026-10-09 — their July 10-Qs were filed, the data still ended in March / April)."""
        recent = ((submissions or {}).get("filings") or {}).get("recent") or {}
        last_end = self.ends[-1] if self.ends else None
        for form, accn, report, filed in zip(recent.get("form", []), recent.get("accessionNumber", []),
                                             recent.get("reportDate", []), recent.get("filingDate", [])):
            if form in FORMS_ANNUAL | FORMS_QUARTER:
                if accn != self.latest_accn and last_end and report and report > last_end:
                    return {"form": form, "accn": accn, "report_date": report, "filed": filed}
                return None
        return None

    def _annual_ends(self) -> list[str]:
        raw = set()
        for fig in ("revenue", "operating", "net", "op_cash"):
            for tag in self.syn[fig]:
                for r in self._rows(tag, self.currency):
                    if r.get("form") in FORMS_ANNUAL and "start" in r and 350 <= _days(r["start"], r["end"]) <= 380:
                        raw.add(r["end"])
        merged: list[str] = []
        for e in sorted(raw):
            if merged and _days(merged[-1], e) < SAME_DAY:
                merged[-1] = e
            else:
                merged.append(e)
        return merged[-6:]

    def _ttm_end(self) -> str | None:
        if not self.annual_ends:
            return None
        last = self.annual_ends[-1]
        ends = set()
        for fig in ("revenue", "net", "op_cash"):
            for tag in self.syn[fig]:
                for r in self._rows(tag, self.currency):
                    if r.get("form") in FORMS_QUARTER and "start" in r and _days(last, r["end"]) > SAME_DAY \
                            and abs(_days(last, r["start"]) - 1) < SAME_DAY:
                        ends.add(r["end"])
        return max(ends) if ends else None

    def _best(self, tag: str, unit: str, end: str, forms: set, start: str | None = None,
              duration: tuple[int, int] | None = None) -> Value | None:
        """The latest-filed fact for this end (± a few days), and this start or duration if given."""
        best = None
        for r in self._rows(tag, unit):
            if r.get("form") not in forms or abs(_days(end, r["end"])) >= SAME_DAY:
                continue
            if duration is not None:
                if "start" not in r or not duration[0] <= _days(r["start"], r["end"]) <= duration[1]:
                    continue
            elif start is not None:
                if "start" not in r or abs(_days(start, r["start"])) >= SAME_DAY:
                    continue
            elif "start" in r:
                continue  # an instant was asked for
            if best is None or r["filed"] > best["filed"]:
                best = r
        if best is None:
            return None
        return Value(float(best["val"]), tag, best["form"], best.get("accn"), best["end"], best["filed"])

    # --- figures ------------------------------------------------------------------------------------------------------

    def _flow(self, tag: str, unit: str, end: str) -> Value | None:
        if end != self.ttm_end:
            return self._best(tag, unit, end, FORMS_ANNUAL, duration=(350, 380))
        # TTM = last annual + year-to-date now − the same period a year before
        last = self.annual_ends[-1]
        fy = self._best(tag, unit, last, FORMS_ANNUAL, duration=(350, 380))
        start_now = date.fromordinal(_d(last).toordinal() + 1).isoformat()
        ytd = self._best(tag, unit, end, FORMS_QUARTER, start=start_now)
        if fy is None or ytd is None:
            return None
        prev_end = date.fromordinal(_d(end).toordinal() - _days(self.annual_ends[-2], last)).isoformat() \
            if len(self.annual_ends) >= 2 else None
        prev_start = date.fromordinal(_d(self.annual_ends[-2]).toordinal() + 1).isoformat() \
            if len(self.annual_ends) >= 2 else None
        prev = self._best(tag, unit, prev_end, FORMS_QUARTER, start=prev_start) if prev_end else None
        if prev is None:
            return None
        return Value(fy.value + ytd.value - prev.value, tag, ytd.form, ytd.accn, end, ytd.filed,
                     ttm={"annual": fy.value, "ytd": ytd.value, "ytd_previous_year": prev.value})

    def _shares(self, tag: str, unit: str, end: str) -> Value | None:
        if end != self.ttm_end:
            return self._best(tag, unit, end, FORMS_ANNUAL, duration=(350, 380))
        q = self._best(tag, unit, end, FORMS_QUARTER, duration=(80, 100))  # the latest quarter's diluted average
        if q is None:
            start_now = date.fromordinal(_d(self.annual_ends[-1]).toordinal() + 1).isoformat()
            q = self._best(tag, unit, end, FORMS_QUARTER, start=start_now)
        return q

    def _lookup(self, figure: str, end: str) -> Value | None:
        unit = self._unit(figure)
        forms = FORMS_QUARTER if end == self.ttm_end else FORMS_ANNUAL
        for tag in self.syn[figure]:
            if tag == "MarketableSecurities" and self._best("MarketableSecuritiesNoncurrent", unit, end, forms):
                continue  # with a noncurrent line next to it, `MarketableSecurities` is not the current part
            if figure in INSTANT:
                v = self._best(tag, unit, end, forms)
            elif figure == "shares":
                v = self._shares(tag, unit, end)
            else:
                v = self._flow(tag, unit, end)
            if v is not None:
                return v
        return None

    def annual(self, figure: str) -> dict[str, Value]:
        """{end: Value} for every end looked at; a year with no value is left out and noted in `misses`."""
        if figure in self._cache:
            return self._cache[figure]
        out = {}
        for end in self.ends:
            v = self._lookup(figure, end)
            if v is None and (figure, self.year_label(end)) in self.user_values:
                v = Value(float(self.user_values[(figure, self.year_label(end))]), "user", "user", None, end)
            if v is None:
                self._miss(figure, end, self.syn[figure])
            else:
                out[end] = v
        self._cache[figure] = out
        return out

    def instant(self, figure: str, end: str) -> Value | None:
        return self.annual(figure).get(end)

    def year_label(self, end: str) -> str:
        """How a year is named to me: '2025' for an annual report, 'TTM 2026-06-28' for the last 4 quarters."""
        return f"TTM {end}" if end == self.ttm_end else end[:4]

    def _miss(self, figure: str, end: str, tried: list[str]) -> None:
        key = (figure, end)
        if key not in {(m["figure"], m["end"]) for m in self.misses}:
            self.misses.append({"figure": figure, "end": end, "year": self.year_label(end), "names_tried": list(tried)})

    # --- liquid assets and debt ------------------------------------------------------------------------------------------

    def liquid(self) -> dict[str, Value]:
        """Cash + short-term investments + current marketable securities — the parts are added, not alternatives.
        A part never reported is not held. A part reported the year before but missing this year is still counted as not
        held, but noted in `liquid_gaps` and `misses` (decision 2026-10-05: computed + a data check + the ledger).
        Without cash the total is not computed."""
        if "liquid" in self._cache:
            return self._cache["liquid"]
        cash, sti, ms = self.annual("cash"), self.annual("short_term_investments"), self.annual("marketable_securities")
        partial = self.annual("short_term_investments_partial")
        out = {}
        self.liquid_gaps: dict[str, list[str]] = {}
        for i, e in enumerate(self.ends):
            if e not in cash:
                continue
            parts = {cash[e].tag: cash[e].value}
            for src in (sti, ms):
                if e in src:
                    parts[src[e].tag] = src[e].value
            if e not in sti and e in partial and (e not in ms or ms[e].tag == "MarketableSecurities"):
                # the current debt securities stand in for the missing short-term investments line; a plain
                # `MarketableSecurities` next to them is not that line (Intel 2026: 250 m of equity, the 16.9 bn short-term
                # investments only as `AvailableForSaleSecuritiesDebtSecuritiesCurrent`; roadmap rule 44)
                parts.pop("MarketableSecurities", None)
                parts[partial[e].tag] = partial[e].value
            if i:
                prev = self.ends[i - 1]
                for figure, src in (("short_term_investments", sti), ("marketable_securities", ms)):
                    if prev in src and src[prev].value and e not in src:
                        self.liquid_gaps.setdefault(e, []).append(figure)
            out[e] = Value(sum(parts.values()), "+".join(parts), cash[e].form, cash[e].accn, e, cash[e].filed, parts)
        self._cache["liquid"] = out
        return out

    def debt(self) -> dict[str, "Debt"]:
        """Per end: the first complete group's total (+ short-term borrowings if the group lacks them) and whether the
        other candidate totals disagree (> 25%)."""
        if "debt" in self._cache:
            return self._cache["debt"]
        out = {}
        self.debt_assumed: list[str] = []  # ends counted as 0 without a figure (roadmap: "A company with no debt")
        for e in self.ends:
            forms = FORMS_QUARTER if e == self.ttm_end else FORMS_ANNUAL
            cands = []
            for names, short_in, need_all in DEBT_GROUPS[self.taxonomy]:
                found = {}
                for n in names:
                    v = self._best(n, self.currency, e, forms)
                    if v is not None:
                        found[n] = v
                if found and (len(found) == len(names) or not need_all):
                    cands.append((found, short_in))
            if not cands:
                if ("debt", self.year_label(e)) in self.user_values:
                    v = float(self.user_values[("debt", self.year_label(e))])
                    out[e] = Debt(v, "user", "user", None, e, parts={"user": v})
                    continue
                zero = self._debt_zero(e, forms)
                if zero is not None:
                    out[e] = zero
                    if zero.assumed:
                        self.debt_assumed.append(e)
                    continue
                self._miss("debt", e, [n for g, _, _ in DEBT_GROUPS[self.taxonomy] for n in g])
                continue
            found, short_in = cands[0]
            parts = {n: v.value for n, v in found.items()}
            if not short_in:
                for n in SHORT_TERM_DEBT[self.taxonomy]:
                    v = self._best(n, self.currency, e, forms)
                    if v is not None:
                        parts[n] = v.value
                        break
            totals = [sum(v.value for v in c.values()) for c, _ in cands[:3]]
            disagree = len(totals) > 1 and min(totals) > 0 and max(totals) > 1.25 * min(totals)
            first = next(iter(found.values()))
            out[e] = Debt(sum(parts.values()), "+".join(parts), first.form, first.accn, e, first.filed, parts,
                          candidates=totals, disagree=disagree)
        self._cache["debt"] = out
        return out

    def _debt_zero(self, end: str, forms) -> "Debt | None":
        """Debt of 0 for an end with no complete debt group, or None (roadmap section 3, "A company with no debt").
        Zero when every part of a group that was found is zero, or when nothing in the debt-balance names has a value other
        than zero in the 12 months up to `end`, interest expense (if any) is at most 1% of revenue, and cash and revenue exist."""
        unit = self.currency
        for names, _, _ in DEBT_GROUPS[self.taxonomy]:
            found = [self._best(n, unit, end, forms) for n in names]
            found = [v for v in found if v is not None]
            if found and all(v.value == 0 for v in found):
                return Debt(0.0, "+".join(v.tag for v in found), found[0].form, found[0].accn, end, found[0].filed,
                            {v.tag: 0.0 for v in found})
        since = date.fromordinal(_d(end).toordinal() - 365).isoformat()
        for tag in debt_balance_names(self.taxonomy):
            for rows in self.raw.get(tag, {}).get("units", {}).values():
                if any(r.get("val") and since < r.get("end", "") <= end for r in rows):
                    return None
        revenue, cash = self._lookup("revenue", end), self._lookup("cash", end)
        if revenue is None or cash is None:
            return None
        interest = self._lookup("interest", end)
        if interest is not None and revenue.value and interest.value > 0.01 * revenue.value:
            return None
        return Debt(0.0, "assumed", "assumed", None, end, "", {"assumed": 0.0}, assumed=True)


@dataclass
class Debt(Value):
    candidates: list = field(default_factory=list)
    disagree: bool = False
    assumed: bool = False  # counted as 0 because nothing is reported (a company with no debt)


def _names(taxonomy: str) -> set[str]:
    from shared.sec.synonyms import all_names

    return all_names(taxonomy)
