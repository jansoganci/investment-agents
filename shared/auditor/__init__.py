"""The AI auditor (roadmap section 3, "AI auditor"): one engine, one rule card per place (`shared/auditor/cards/`).

It checks and never produces figures. Code checks come first: every quote an item gives must appear in the filing word for
word, or the item is `not_found`. A different model family from the writer (`auditor` job in `settings.yaml`).

    result = auditor.audit("figure", items, text, run=run)      # AuditResult
    auditor.save(conn, stock_id, result)                        # a row in `audits`

Overall result (roadmap, "Changes after the phase 2 audit"): `pass` only when every item passes; `fail` when any item fails; otherwise
`not_found` (could not confirm — noted, but the card is not marked unverified). No items: `not_found`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from shared import ai, clock, config
from shared.sec import filing

CARDS = Path(__file__).resolve().parent / "cards"
KINDS = ("figure", "reading", "sell")
VERDICTS = ("pass", "fail", "not_found")

ENGINE = """You are an auditor. You check; you never produce or correct figures and you never write new claims.
Answer with JSON only, no other text: a list of objects, one per item you were given, in this form:
{"id": "<the item's id>", "verdict": "pass" | "fail" | "not_found", "quote": "<the row or sentence from the filing, word for word>", "reason": "<one short sentence>"}
A `quote` must be copied from the excerpts exactly. When a figure sits on several rows (for example the parts of liquid assets), copy each
row exactly and separate the rows with " | ". If you cannot find the evidence in the excerpts, the verdict is "not_found".
Below is the rule card for this check.

"""


@dataclass
class AuditResult:
    audit: str
    result: str                       # pass / fail / not_found
    items: list[dict] = field(default_factory=list)
    model: str = ""
    cost_usd: float | None = None
    error: str | None = None          # the auditor could not answer (all providers failed, bad answer): no verdict

    def failed(self) -> list[dict]:
        return [i for i in self.items if i["verdict"] == "fail"]


def card_text(kind: str) -> str:
    return (CARDS / f"{kind}.md").read_text(encoding="utf-8")


def parse_items(text: str) -> list[dict]:
    """The model's answer → a list of dicts (a code fence or text around the JSON is tolerated)."""
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        raise ValueError("no JSON list in the answer")
    data = json.loads(m.group(0))
    if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
        raise ValueError("the answer is not a list of objects")
    return data


def audit(kind: str, items: list[dict], text: str, *, run=None, stock_id=None, model: str | None = None,
          exclude_families: set | None = None) -> AuditResult:
    """`items`: [{"id", "claim", ...}]; `text`: the filing text the quotes must be found in."""
    if kind not in KINDS:
        raise ValueError(f"unknown audit '{kind}'")
    cfg = config.settings().get("ai") or {}
    terms = {t for i in items for t in i.get("terms", [])}
    terms |= {w for i in items for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", i.get("claim", ""))}
    excerpts = filing.excerpts(text, sorted(terms)[:60], cfg.get("excerpt_chars", 12000))
    prompt = json.dumps({"items": [{k: v for k, v in i.items() if k != "terms"} for i in items]}, ensure_ascii=False,
                        indent=1) + "\n\nFILING EXCERPTS:\n" + "\n---\n".join(excerpts)
    try:
        reply = ai.call("auditor", prompt, system=ENGINE + card_text(kind), run=run, stock_id=stock_id, model=model,
                        exclude_families=exclude_families)
        parsed = parse_items(reply.text)
    except (ai.AIError, ValueError, json.JSONDecodeError) as exc:
        return AuditResult(kind, "not_found", [], error=f"{type(exc).__name__}: {exc}")
    by_id = {str(p.get("id")): p for p in parsed}
    out = []
    for i in items:
        p = by_id.get(str(i["id"]), {})
        verdict = p.get("verdict") if p.get("verdict") in VERDICTS else "not_found"
        quote = (p.get("quote") or "").strip()
        reason = p.get("reason") or ""
        needs_number = kind in ("figure", "sell") and not re.search(r"\d", quote)  # "in millions" proves nothing about a figure
        if verdict in ("pass", "fail") and (needs_number or not filing.quote_ok(text, quote, cfg.get("min_quote_chars", 20))):
            # a verdict that does not carry a real quote is not believed (a fail without evidence would be as bad as a pass)
            verdict, reason = "not_found", f"no verified quote ({reason})".strip()
        out.append({"id": str(i["id"]), "verdict": verdict, "quote": quote, "reason": reason})
    result = overall(out)
    return AuditResult(kind, result, out, model=reply.model, cost_usd=reply.cost_usd)


def overall(items: list[dict]) -> str:
    if any(i["verdict"] == "fail" for i in items):
        return "fail"
    if items and all(i["verdict"] == "pass" for i in items):
        return "pass"
    return "not_found"


def save(conn, stock_id: int | None, result: AuditResult, filing_accn: str | None = None) -> int:
    """One row in `audits` (inside the caller's write lock)."""
    detail = {"items": result.items}
    if result.error:
        detail["error"] = result.error
    cur = conn.execute("INSERT INTO audits (stock_id, audit, result, detail, model, cost_usd, created_at, filing) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (stock_id, result.audit, result.result, json.dumps(detail, ensure_ascii=False), result.model,
                        result.cost_usd or 0, clock.utc_iso(), filing_accn))
    return cur.lastrowid
