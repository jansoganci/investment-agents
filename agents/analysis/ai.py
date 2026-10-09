"""Agent 3's AI parts (roadmap section 3, "Agent 3's AI parts — how phase 2 builds them"):

    why answers (a quote for every ❌ and every flag) · the first thesis · the thesis check · the drop-alert check ·
    the auditor's checks · the sell suggestion

The AI never produces figures; code checks first: every quote must appear in the filing word for word, or the answer is
not shown as a fact. The AI parts never stop the numbers: on any AI failure the card still gets its numbers and says so.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field

from agents.analysis import sell
from shared import ai, auditor, config
from shared.sec import FORMS_QUARTER, filing

KINDS = ("company_specific", "general_risk")
STATUSES = ("intact", "broken", "watch")
MAX_ITEMS = 12

MEASURE_TERMS = {
    "revenue_growth_3y": ["revenue"], "margin_stability": ["gross margin", "gross profit"],
    "operating_margin": ["operating income", "income from operations", "operating margin"],
    "capital_return": ["return on", "impairment", "goodwill", "property and equipment", "capital expenditures"],
    "cash_conversion": ["operating activities", "working capital", "income taxes", "cash flows"],
    "interest_cover": ["interest expense"], "debt_years": ["senior notes", "debt", "borrowings"],
    "share_count": ["repurchase", "shares outstanding", "stock split", "dilut"],
    "gross_profit_growth": ["gross profit", "gross margin"], "cash_runway": ["liquidity", "cash and cash equivalents"],
    "debt": ["senior notes", "debt", "borrowings", "credit facility"], "dividend_cover": ["dividend"],
}
FLAG_TERMS = {
    "one_off": ["gain on", "one-time", "settlement", "non-recurring", "tax", "impairment", "sale of"],
    "data_check": ["debt", "senior notes", "cash and cash equivalents", "marketable securities", "stock split", "shares"],
    "borderline": ["dividend", "margin", "capital expenditures"],
    "free_cash_negative": ["operating activities", "capital expenditures", "purchases of property"],
}

WHY_SYSTEM = """You help a long-term stock investor understand one company's numbers. You are given items (a weak measure or a
flag) and excerpts of the company's own filing. For each item answer in at most two plain sentences WHY, using only the
excerpts, and copy the sentence from the excerpts that supports your answer as `quote`, word for word.
If the excerpts do not explain the item, say so in `answer` and leave `quote` empty.
`kind`: "company_specific" if the quote describes a real event or fact of THIS company; "general_risk" if it is a general
risk sentence any company could write.
Answer with JSON only: a list of {"id": "<item id>", "answer": "...", "quote": "...", "kind": "company_specific"|"general_risk"}."""

THESIS_SYSTEM = """You write the investment thesis of one company for a long-term investor, in plain English, from the numbers
and the excerpts you are given. Answer with JSON only:
{"reasons": ["why it is owned", ...at most 3], "breaks": ["a thing that would break the thesis", exactly 3]}
Each break must be something an investor could see happen in a later filing (a measure turning, a segment shrinking, debt
rising past a level), not a vague worry."""

CHECK_SYSTEM = """You check whether a company's thesis is still true after its newest filing. You are given the thesis (why it
is owned and 3 things that would break it), my later notes, the new numbers, and excerpts. Answer with JSON only:
{"status": "intact" | "broken" | "watch", "point": <1, 2 or 3: the break that happened, or null>, "reason": "one or two
sentences", "quote": "the sentence from the excerpts that shows it, word for word, or empty"}
`broken` only when one of the 3 things really happened and you can quote it. When unsure, answer "watch".
NEW NUMBERS are current: where the thesis states an older figure or says a figure could not be computed, use NEW NUMBERS."""

DROP_SYSTEM = """A stock I follow fell sharply. Using the thesis and the excerpts of its latest filing (and news, if any is given),
say whether the thesis is still true. Answer with JSON only:
{"status": "intact" | "broken" | "watch", "reason": "one or two sentences", "quote": "word for word from the filing, or empty"}
News alone can only ever mean "watch". When unsure, answer "watch"."""


class AIFormatError(Exception):
    """The model's answer could not be used (not JSON, or the wrong shape) even after one more try."""


@dataclass
class Why:
    id: str
    what: str
    answer: str
    quote: str
    kind: str | None
    verified: bool


@dataclass
class Context:
    ticker: str
    company: str
    in_portfolio: bool = False
    first: bool = True                      # no earlier fundamental entry
    grades: list = field(default_factory=list)   # earlier entries' grades, oldest first
    previous_thesis: str | None = None
    previous_thesis_date: str | None = None
    filing: str | None = None               # the filing the figures come from (named in a sell suggestion)
    notes: list = field(default_factory=list)    # my notes since that thesis
    run: object = None
    stock_id: int | None = None
    rng: random.Random = field(default_factory=random.Random)
    model: str | None = None                # a one-off model for the strong job (/analyze KO opus-5.5)
    news: list | None = None
    families: set = field(default_factory=set)   # makers of the models that wrote this analysis
    models: list = field(default_factory=list)   # provider:model that really answered, in order
    no_fallback: bool = False               # the strong-model test: no other model may answer instead


@dataclass
class AIPart:
    why: list = field(default_factory=list)
    thesis: dict | None = None              # {"reasons": [...], "breaks": [...]} written now
    thesis_status: str | None = None
    check: dict | None = None               # {"status", "point", "reason", "quote"} of the thesis check
    audits: list = field(default_factory=list)
    unverified: bool = False
    sell: dict | None = None                # {"trigger", "text", "status": "sent"|"held"}
    notes: list = field(default_factory=list)

    def lines(self) -> list[str]:
        out = list(self.notes)
        if self.unverified:
            out.append("UNVERIFIED: the auditor disagrees — " + "; ".join(
                f"{a.audit}: " + ", ".join(f"{i['id']} ({i['reason']})" for i in a.failed()) for a in self.audits
                if a.result == "fail"))
        elif any(a.result == "not_found" for a in self.audits):
            out.append("The auditor could not confirm everything (see the card's audit lines).")
        if self.check and self.check["status"] != "intact":
            out.append(f"Thesis {self.check['status']}: {self.check['reason']}")
        return out


# --- talking to the model --------------------------------------------------------------------------------------------------

def parse_json(text: str):
    """The first JSON object or list in an answer (a code fence or text around it is tolerated)."""
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        raise ValueError("no JSON in the answer")
    start = min(starts)
    closer = "}" if text[start] == "{" else "]"
    end = text.rfind(closer)
    if end < start:
        raise ValueError("the JSON is not closed")
    return json.loads(text[start:end + 1])


def ask_json(job: str, system: str, prompt: str, check, ctx: Context):
    """One call; a second try (told what was wrong) when the answer is not usable. `check(data)` raises ValueError."""
    problem = None
    for _ in range(2):
        text = prompt if problem is None else prompt + f"\n\nYour previous answer could not be used ({problem}). Answer again, JSON only."
        reply = ai.call(job, text, system=system, run=ctx.run, stock_id=ctx.stock_id, model=ctx.model if job == "strong" else None,
                        only_first=ctx.no_fallback)
        ctx.families.add(ai.family(reply.provider, reply.model))
        ctx.models.append(f"{reply.provider}:{reply.model}")
        try:
            data = parse_json(reply.text)
            check(data)
            return data
        except (ValueError, KeyError, TypeError) as exc:  # json.JSONDecodeError is a ValueError
            problem = str(exc)
    raise AIFormatError(problem or "unusable answer")


def _facts_block(r) -> str:
    """One line per measure. A mark with no single value is the mark itself (`debt: good, decisive`);
    a measure with neither a value nor a mark stays `not_computed`."""
    rows = []
    for name, m in r.measures.items():
        decisive = ", decisive" if m["decisive"] else ""
        if m["value"] is None and m["mark"]:
            rows.append(f"{name}: {m['mark']}{decisive}")
        elif m["value"] is None:
            rows.append(f"{name}: not_computed")
        else:
            rows.append(f"{name}: {m['value']} ({m['mark'] or 'not_computed'}{decisive})")
    return "\n".join(rows)


def _excerpts(text: str, terms: list[str]) -> str:
    cfg = config.settings().get("ai") or {}
    return "\n---\n".join(filing.excerpts(text, terms, cfg.get("excerpt_chars", 12000)))


# --- why answers -----------------------------------------------------------------------------------------------------------

def why_items(r) -> list[dict]:
    items = []
    for name, m in r.measures.items():
        if m["mark"] == "weak":
            items.append({"id": f"M:{name}", "what": f"measure {name} is weak (value {m['value']}; {m.get('note') or 'no note'})",
                          "terms": MEASURE_TERMS.get(name, [])})
    for code, f in open_flags(r):
        if f["flag"] == "borderline":  # "within 10% of a threshold": nothing to explain (roadmap, "After the first real-model run")
            continue
        items.append({"id": code, "what": f"flag {f['flag']}: {f['detail']}", "terms": FLAG_TERMS.get(f["flag"], [])})
    return items[:MAX_ITEMS]


def open_flags(r) -> list[tuple[str, dict]]:
    """(code, flag) of the warnings still open: the ones I closed are not asked about again."""
    codes = getattr(r, "codes", None) or [f"U{i}" for i in range(1, len(r.flags) + 1)]
    closed = getattr(r, "closed", set())
    return [(c, f) for c, f in zip(codes, r.flags) if c not in closed]


def ask_why(r, text: str, ctx: Context) -> list[Why]:
    items = why_items(r)
    if not items:
        return []
    terms = sorted({t for i in items for t in i["terms"]})
    prompt = (f"Company: {ctx.company} ({ctx.ticker}), type {r.lynch_type}, grade {r.grade}.\nITEMS:\n"
              + json.dumps([{"id": i["id"], "what": i["what"]} for i in items], ensure_ascii=False, indent=1)
              + "\n\nFILING EXCERPTS:\n" + _excerpts(text, terms))

    def check(data):
        if not isinstance(data, list):
            raise ValueError("expected a list")

    answers = {str(a.get("id")): a for a in ask_json("strong", WHY_SYSTEM, prompt, check, ctx) if isinstance(a, dict)}
    min_chars = (config.settings().get("ai") or {}).get("min_quote_chars", 20)
    out = []
    for i in items:
        a = answers.get(i["id"], {})
        quote, kind = (a.get("quote") or "").strip(), a.get("kind")
        verified = bool(quote) and filing.quote_in(text, quote, min_chars)
        out.append(Why(i["id"], i["what"], (a.get("answer") or "").strip() if verified else "no verified quote — not shown as a fact",
                       quote if verified else "", kind if verified and kind in KINDS else None, verified))
    return out


# --- the thesis ------------------------------------------------------------------------------------------------------------

def first_thesis(r, why: list[Why], text: str, ctx: Context) -> dict:
    prompt = (f"Company: {ctx.company} ({ctx.ticker}). Lynch type {r.lynch_type}, grade {r.grade}.\nNUMBERS:\n{_facts_block(r)}\n"
              "WHY ANSWERS:\n" + "\n".join(f"- {w.what}: {w.answer}" for w in why if w.verified)
              + "\n\nFILING EXCERPTS:\n" + _excerpts(text, ["we sell", "our customers", "segment", "revenue", "competition", "products"]))

    def check(d):
        if not (isinstance(d.get("reasons"), list) and 1 <= len(d["reasons"]) <= 3 and all(isinstance(x, str) and x for x in d["reasons"])):
            raise ValueError("`reasons` must be 1 to 3 sentences")
        if not (isinstance(d.get("breaks"), list) and len(d["breaks"]) == 3 and all(isinstance(x, str) and x for x in d["breaks"])):
            raise ValueError("`breaks` must be exactly 3 sentences")

    data = ask_json("strong", THESIS_SYSTEM, prompt, check, ctx)
    return {"reasons": [x.strip() for x in data["reasons"]], "breaks": [x.strip() for x in data["breaks"]]}


def thesis_text(t: dict) -> str:
    return ("Why it is owned:\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(t["reasons"], 1))
            + "\nWhat would break it:\n" + "\n".join(f"{i}. {x}" for i, x in enumerate(t["breaks"], 1)))


def thesis_check(r, why: list[Why], text: str, ctx: Context) -> dict:
    prompt = (f"Company: {ctx.company} ({ctx.ticker}). Newest grade {r.grade}, type {r.lynch_type}.\nTHESIS:\n{ctx.previous_thesis}\n"
              "MY LATER NOTES:\n" + ("\n".join(ctx.notes) or "(none)") + f"\nNEW NUMBERS:\n{_facts_block(r)}\n"
              "WHY ANSWERS:\n" + "\n".join(f"- {w.what}: {w.answer}" for w in why if w.verified)
              + "\n\nFILING EXCERPTS:\n" + _excerpts(text, ["risk", "revenue", "debt", "decline", "decrease", "customers"]))

    def check(d):
        if d.get("status") not in STATUSES:
            raise ValueError("`status` must be intact, broken or watch")

    d = ask_json("strong", CHECK_SYSTEM, prompt, check, ctx)
    status, quote = d["status"], (d.get("quote") or "").strip()
    reason = (d.get("reason") or "").strip()
    min_chars = (config.settings().get("ai") or {}).get("min_quote_chars", 20)
    if status == "broken" and not (quote and filing.quote_in(text, quote, min_chars)):
        # a thesis is never declared broken without evidence from the filing (and a sell suggestion rests on it)
        status, reason = "watch", f"the model said broken but gave no verified quote ({reason})"
        quote = ""
    point = d.get("point") if d.get("point") in (1, 2, 3) else None
    return {"status": status, "point": point, "reason": reason, "quote": quote if filing.quote_in(text, quote, min_chars) else ""}


def drop_alert_check(r, text: str, ctx: Context) -> dict:
    """The -20% drop alert: the latest filing (+ news if any). News alone only ever says `watch`."""
    news = ctx.news or []
    prompt = (f"Company: {ctx.company} ({ctx.ticker}). Newest grade {r.grade}.\nTHESIS:\n{ctx.previous_thesis or '(none written)'}\n"
              "NEWS:\n" + ("\n".join(f"- {n}" for n in news) or "(no news available — filing only)")
              + "\n\nFILING EXCERPTS:\n" + _excerpts(text, ["risk", "revenue", "debt", "decline", "customers", "guidance"]))

    def check(d):
        if d.get("status") not in STATUSES:
            raise ValueError("`status` must be intact, broken or watch")

    d = ask_json("strong", DROP_SYSTEM, prompt, check, ctx)
    status, quote = d["status"], (d.get("quote") or "").strip()
    min_chars = (config.settings().get("ai") or {}).get("min_quote_chars", 20)
    in_filing = bool(quote) and filing.quote_in(text, quote, min_chars)
    if status == "broken" and not in_filing:
        status = "watch"  # news (or an unverified claim) alone never breaks a thesis
    return {"status": status, "reason": (d.get("reason") or "").strip(), "quote": quote if in_filing else "",
            "news_used": bool(news)}


# --- the auditor's checks -------------------------------------------------------------------------------------------------

FIGURE_TERMS = {
    "revenue": ["total revenue", "revenue"], "operating": ["income from operations", "operating income"],
    "net": ["net income"], "op_cash": ["net cash provided by operating activities"],
    "capex": ["purchases related to property and equipment", "purchases of property"],
    "shares": ["diluted", "weighted average shares"],
}


def figure_items(r) -> list[dict]:
    last, items = r.last, []
    for fig, terms in FIGURE_TERMS.items():
        v = (r.figures.get(fig) or {}).get(last)
        if v is None:
            continue
        # the period is a short code the rule card explains: the words of a claim become the excerpts' search terms, and a
        # longer text pushed balance-sheet rows out of them
        item = {"id": fig, "claim": f"{fig} = {v.value:,.0f} ({v.tag}), period end {last} ({_period(v)}), in {r.currency}",
                "terms": terms, "values": [] if v.form == "user" else [v.value]}
        if v.ttm:  # a last-4-quarters total is in no filing: its two year-to-date parts are (GE, 2026-10-06)
            item["values"] = [v.ttm["ytd"], v.ttm["ytd_previous_year"]]  # the 4-quarter total itself is printed nowhere
            item["note"] = (f"TTM = the last annual report's {v.ttm['annual']:,.0f} (in the 10-K, not in this filing) + this year to "
                            f"date {v.ttm['ytd']:,.0f} − the same period a year before {v.ttm['ytd_previous_year']:,.0f}. Check the "
                            "two year-to-date figures against this filing; never fail the total for differing from one column")
        items.append(item)
    if last in r.liquid:
        v = r.liquid[last]
        items.append({"id": "liquid", "claim": "liquid assets = " + " + ".join(f"{k} {x:,.0f}" for k, x in v.parts.items())
                      + f" = {v.value:,.0f}, period end {last} (BS)", "note": "by our rule only cash, short-term investments and marketable debt securities count; "
                      "equity securities and stakes in other companies are left out on purpose; only parts with a balance-sheet line "
                      "of their own count: a part with no line of its own (e.g. time deposits inside other current assets) is not "
                      "counted — never fail liquid assets for leaving it out; restricted cash counts when the filing reports cash "
                      "and restricted cash as one line — never fail for that", "terms": ["cash and cash equivalents", "marketable securities", "short-term investments"],
                      "values": [v.value, *v.parts.values()]})
    if last in r.debt:
        v = r.debt[last]
        items.append({"id": "debt", "claim": "debt = " + " + ".join(f"{k} {x:,.0f}" for k, x in v.parts.items())
                      + f" = {v.value:,.0f}, period end {last} (BS)" + (" (assumed 0: nothing reported)" if getattr(v, "assumed", False) else ""),
                      "terms": ["senior notes", "long-term debt", "short-term debt", "borrowings", "notes payable"],
                      "values": [] if getattr(v, "assumed", False) else [v.value, *v.parts.values()]})
    return items


def _period(v) -> str:
    """The period code of a figure (rule card 1 explains them): a 4-quarter total compared with a 6-month row is a false fail."""
    if v.form == "user":
        return "given by me"
    if v.ttm:
        return "TTM"
    if v.form in FORMS_QUARTER:
        return "Q"
    return "FY"


def reading_items(why: list[Why]) -> list[dict]:
    return [{"id": w.id, "claim": w.answer, "quote": w.quote, "kind": w.kind, "what": w.what, "terms": []}
            for w in why if w.verified]


def should_audit(ctx: Context, r, previous_grade: str | None, data_check: bool) -> set[str]:
    """Which cards run on this analysis (roadmap, "When agent 3's auditor runs")."""
    kinds = set()
    if ctx.first or (previous_grade in ("solid", "weak") and r.grade in ("solid", "weak") and previous_grade != r.grade):
        kinds |= {"figure", "reading"}
    if data_check:
        kinds.add("figure")
    sample = (config.settings().get("ai") or {}).get("audit_sample", 5)
    if sample and ctx.rng.randrange(sample) == 0:
        kinds |= {"figure", "reading"}
    return kinds


def run_ai(r, text: str, ctx: Context) -> AIPart:
    """All of agent 3's AI parts for one analysis. Never raises for an AI problem: it notes it and carries on."""
    part = AIPart()
    if r.out_of_scope:
        return part
    try:
        part.why = ask_why(r, text, ctx)
    except (ai.AIError, AIFormatError) as exc:
        part.notes.append(f"The 'why?' answers are missing: {exc}")
    try:
        if ctx.previous_thesis is None:
            part.thesis = first_thesis(r, part.why, text, ctx)
            part.thesis_status = "intact"
        else:
            part.check = thesis_check(r, part.why, text, ctx)
            part.thesis_status = part.check["status"]
    except (ai.AIError, AIFormatError) as exc:
        part.notes.append(f"The thesis could not be written or checked: {exc}")

    previous_grade = ctx.grades[-1] if ctx.grades else None
    data_check = any(f["flag"] == "data_check" for _, f in open_flags(r))
    kinds = should_audit(ctx, r, previous_grade, data_check)
    trig = sell.trigger(ctx.in_portfolio, r.grade, ctx.grades, part.thesis_status)
    if trig:
        kinds |= {"figure", "reading", "sell"}  # before a sell suggestion everything behind it is checked

    done = {}

    def audit(kind, items):
        if kind in done or not items:
            return done.get(kind)
        writer = ctx.families or {ai.entry_family(ai.chain("strong", None, ctx.model)[0])}
        res = auditor.audit(kind, items, text, run=ctx.run, stock_id=ctx.stock_id, exclude_families=writer)
        part.audits.append(res)
        done[kind] = res
        return res

    if "figure" in kinds:
        audit("figure", figure_items(r))
    if "reading" in kinds:
        audit("reading", reading_items(part.why))
    part.unverified = any(a.result == "fail" for a in part.audits)

    if trig:
        evidence = _evidence(r, part, trig)
        item = {"id": "sell", "claim": f"{sell.TRIGGERS[trig]} — " + " | ".join(evidence), "terms": ["risk", "revenue", "debt"]}
        audit("sell", [item])
        held = hold_reason(done)
        text_out = sell.message(ctx.ticker, trig, evidence, data_check, held, ctx.filing)
        part.sell = {"trigger": trig, "text": text_out, "status": "held" if held else "sent", "evidence": evidence}
    return part


def hold_reason(done: dict) -> tuple[str, str] | None:
    """Why a sell suggestion is held back, or None when every audit behind it passed (roadmap, "Changes after the phase 2 audit").
    The figure audit and the sell audit must have run and passed; the reading audit must pass when it ran."""
    for kind in ("figure", "sell"):
        if done.get(kind) is None:
            return "not_run", f"the {kind} audit did not run"
    ran = [a for a in done.values() if a is not None]
    errors = [a for a in ran if a.error]
    if errors:
        return "not_run", "; ".join(f"{a.audit}: {a.error}" for a in errors)
    failed = [a for a in ran if a.result == "fail"]
    if failed:
        return "disagrees", "; ".join(f"{a.audit}: " + ", ".join(i["id"] for i in a.failed()) for a in failed)
    unconfirmed = [a for a in ran if a.result != "pass"]
    if unconfirmed:
        return "unconfirmed", "; ".join(
            f"{a.audit} ({sum(i['verdict'] != 'pass' for i in a.items)} of {len(a.items)} items not confirmed)" for a in unconfirmed)
    return None


def _evidence(r, part: AIPart, trig: str) -> list[str]:
    ev = [f"grade {r.grade}; decisive measures: " + ", ".join(f"{n} {m['mark'] or 'not_computed'}" for n, m in r.measures.items() if m["decisive"])]
    if trig == "thesis_broken" and part.check:
        ev.append(f"thesis point {part.check['point']}: {part.check['reason']}" + (f' — "{part.check["quote"]}"' if part.check["quote"] else ""))
    ev += [f"{w.what}: {w.answer}" + (f' — "{w.quote}"' if w.quote else "") for w in part.why if w.verified][:3]
    return ev
