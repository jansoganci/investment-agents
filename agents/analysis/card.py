"""The card (`card.md`): roadmap section 3, "Card format"; skeleton in BAGLAM.md section 7.

- The header (YAML front matter) shows the current state. Only code changes it, and only these fields:
  `status`, `in_portfolio`, `lynch_type`, `grade`, `last_entry` (and `ticker` / `sector` through `rename_ticker` /
  `change_sector`, each with a dated note). `opened` never changes.
- Entries are appended at the end and never edited: `## <date> · <record> · <who> [· <source>]`.
- Figures live only in the YAML data block of an entry; prose sits under `### Summary` · `### Thesis` · `### What changed`.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import yaml

from agents.analysis.measures import Result, verdicts

HEADER_ORDER = ("ticker", "company", "exchange", "country", "sector", "subsector", "status", "in_portfolio",
                "lynch_type", "grade", "last_entry", "opened", "publish")
CODE_FIELDS = {"status", "in_portfolio", "lynch_type", "grade", "last_entry"}
NOT_COMPUTED = "not_computed"


def _header_text(head: dict) -> str:
    lines = ["---"]
    for k in list(HEADER_ORDER) + [k for k in head if k not in HEADER_ORDER]:  # fields we do not know are kept
        v = head.get(k)
        lines.append(f"{k}: {'' if v is None else v}".rstrip())
    lines.append("---")
    return "\n".join(lines) + "\n"


def write(path: Path, text: str) -> None:
    """Write the whole file at once: a temporary file, then a rename (never a half-written card)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def new_card(stock: dict) -> str:
    """A bare card for a stock that has none yet (until agent 2 opens cards, phase 5)."""
    head = {k: stock.get(k) for k in HEADER_ORDER}
    head["publish"] = "no"
    return (_header_text(head) + f"# {stock['company']} ({stock['ticker']})\n"
            "> Story: (not written yet — 2 sentences: what it sells, where the money comes from)\n")


def split(text: str) -> tuple[dict, str]:
    """(header fields, everything after the header)."""
    if not text.startswith("---\n"):
        raise ValueError("a card starts with its header")
    end = text.index("\n---\n", 4)
    head = {}
    for line in text[4:end].splitlines():
        key, _, value = line.partition(":")
        head[key.strip()] = value.strip() or None
    return head, text[end + 5:]


def append(path: Path, entry: str, header_changes: dict) -> None:
    """Append one entry and update the header's code fields. Nothing before the new entry is changed."""
    bad = set(header_changes) - CODE_FIELDS
    if bad:
        raise ValueError(f"only code fields change in the header, not {sorted(bad)}")
    text = path.read_text(encoding="utf-8")
    head, body = split(text)
    head.update({k: v for k, v in header_changes.items()})
    if entry:
        body = body.rstrip("\n") + "\n\n" + entry.rstrip("\n") + "\n"
    write(path, _header_text(head) + body)


def rename_ticker(path: Path, old: str, new: str, day: str, note: str) -> Path:
    """A ticker change (FB → META): same company, same card. The folder takes the new ticker, the header's `ticker`
    changes and a dated note says so; nothing else changes."""
    head, body = split(path.read_text(encoding="utf-8"))
    head["ticker"] = new
    body = body.rstrip("\n") + "\n\n" + note_entry(day, note).rstrip("\n") + "\n"
    folder = path.parent
    target = folder.with_name(new + folder.name[len(old):]) if folder.name.startswith(old + " - ") else folder
    if target != folder:
        os.replace(folder, target)
    write(target / path.name, _header_text(head) + body)
    return target / path.name


def change_sector(path: Path, old: str | None, new: str, day: str) -> None:
    """A sector change from the sector table or `sector_overrides` (roadmap rule 34): the header's `sector` changes and a dated
    note says so; nothing else changes."""
    head, body = split(path.read_text(encoding="utf-8"))
    head["sector"] = new
    note = f"Sector: {old} → {new} (sector table / settings.yaml sector_overrides)"
    body = body.rstrip("\n") + "\n\n" + note_entry(day, note, who="agent_3").rstrip("\n") + "\n"
    write(path, _header_text(head) + body)


def note_entry(day: str, text: str, who: str = "user") -> str:
    return f"## {day} · note · {who}\n{text}\n"


# --- reading the card back ---------------------------------------------------------------------------------------------

_YEAR_OR_NUMBER = re.compile(r"((?<!\d)(?:19|20)\d\d(?!\d))|[-+]?\d[\d.,]*(?:e[-+]?\d+)?%?|→|×")


def flag_key(flag: dict) -> str:
    """What a warning is about: its words, with the amounts masked and the years kept ("debt 8.5 → 33.4 bn (2026)" is the same
    warning as "debt 9.1 → 12.0 bn (2026)", but a debt jump in 2029 is a new one). Roadmap, "Changes after the phase 2 audit"."""
    detail = _YEAR_OR_NUMBER.sub(lambda m: m.group(1) or "#", flag["detail"])
    detail = re.sub(r"#(?:\s*#)+", "#", detail)
    squeezed = re.sub(r"\s+", " ", detail).strip()
    return f"{flag['flag']}:{squeezed}"


def _keys(items: list[dict], name: str) -> list[str]:
    """One key per warning of an entry. Warnings of the same shape in one entry are told apart by their full text (so an order
    change or one of them disappearing cannot shift a code onto another warning)."""
    base = [flag_key({"flag": w[name], "detail": w["detail"]}) for w in items]
    out = []
    for k, w in zip(base, items):
        if base.count(k) > 1:
            full = re.sub(r"\s+", " ", w["detail"]).strip()
            k = k + "~" + hashlib.sha1(full.encode()).hexdigest()[:8]
        out.append(k)
    return out


def _yaml_of(body: str) -> dict:
    if "```yaml\n" not in body:
        return {}
    try:
        return yaml.safe_load(body.split("```yaml\n", 1)[1].split("\n```", 1)[0]) or {}
    except yaml.YAMLError:
        return {}


def assign_codes(text: str | None, flags: list[dict]) -> tuple[list[str], set[str]]:
    """(a code for each flag, the codes I closed). A condition keeps the code it first had (U1 stays U1); a new condition
    gets the next number; a closed warning stays closed while its condition is the same (same words and years; amounts may move).
    Two warnings of one shape are matched by their full text."""
    known, by_detail, top = {}, {}, 0
    for e in entries(text or ""):
        warnings = _yaml_of(e["body"]).get("warnings") or []
        for w in warnings:
            top = max(top, int(re.sub(r"\D", "", w["code"]) or 0))
            if w.get("key"):  # codes written by phase 1 have no key: they were numbered by position and are not trusted
                known.setdefault(w["key"], w["code"])
                by_detail.setdefault((w["key"].split("~")[0], re.sub(r"\s+", " ", w["detail"]).strip()), w["code"])
    codes = []
    items = [{"name": f["flag"], "detail": f["detail"]} for f in flags]
    for f, k in zip(flags, _keys(items, "name")):
        base = flag_key({"flag": f["flag"], "detail": f["detail"]})
        code = known.get(k) or by_detail.get((base, re.sub(r"\s+", " ", f["detail"]).strip()))
        if code is None:
            top += 1
            code = f"U{top}"
            known[k] = code
        codes.append(code)
    return codes, closed_warnings(text or "")


def closed_warnings(text: str) -> set[str]:
    """Warnings I closed with /closewarning (a user note "Warning U1 closed: …"), unless reopened by /undo."""
    closed = set()
    for e in entries(text):
        if e["record"] == "note" and e["who"] == "user":
            for code, what in re.findall(r"Warning (U\d+) (closed|reopened)", e["body"]):
                (closed.add if what == "closed" else closed.discard)(code)
    return closed


THESIS_NONE = ("Not written", "Unchanged")


def entries(text: str) -> list[dict]:
    """[{date, record, who, body}] in order; the body is everything under the heading."""
    out = []
    for chunk in text.split("\n## ")[1:]:
        heading, _, body = chunk.partition("\n")
        parts = [x.strip() for x in heading.split("·")]
        out.append({"date": parts[0], "record": parts[1] if len(parts) > 1 else "", "who": parts[2] if len(parts) > 2 else "",
                    "body": body})
    return out


def last_thesis(text: str) -> tuple[str, str] | None:
    """(date, thesis text) of the newest entry that really has a thesis; None when no entry has one yet."""
    for e in reversed(entries(text)):
        if "### Thesis\n" not in e["body"]:
            continue
        thesis = e["body"].split("### Thesis\n", 1)[1].split("\n### ", 1)[0].strip()
        if thesis and not thesis.startswith(THESIS_NONE):
            return e["date"], thesis
    return None


def notes_since(text: str, day: str) -> list[str]:
    """My notes (`record: note`, who: user) on or after `day`, e.g. a corrected thesis or a closed warning."""
    return [f"{e['date']}: {e['body'].strip()}" for e in entries(text)
            if e["record"] == "note" and e["who"] == "user" and e["date"] >= day]


# --- the fundamental entry --------------------------------------------------------------------------------------------

def _num(v, digits=4):
    if v is None:
        return NOT_COMPUTED
    if isinstance(v, float):
        return round(v, digits) if abs(v) < 1000 else round(v)
    return v


def _block(data: dict) -> str:
    return "```yaml\n" + yaml.safe_dump(data, sort_keys=False, default_flow_style=None, allow_unicode=True,
                                        width=140) + "```\n"


def data_block(r: Result, source: dict, part=None) -> dict:
    src = {k: source.get(k) for k in ("report", "period_end", "url", "as_of", "filing")}
    data: dict = {"source": src}
    if r.out_of_scope:
        data.update({"grade": "unclear", "out_of_scope": r.out_of_scope, "sic": r.sic})
        return data
    data.update({"lynch_type": r.lynch_type or "unclear", "grade": r.grade,
                 "shrink_rule": "yes" if "shrink_rule" in r.rules else "no"})
    if "fast_grower_safety" in r.rules:
        data["fast_grower_safety"] = "yes"
    data["measures"] = {}
    for name, m in r.measures.items():
        item = {"value": _num(m["value"]), "mark": m["mark"] or NOT_COMPUTED,
                "decisive": "yes" if m["decisive"] else "no"}
        if m.get("unit") and m["value"] is not None:
            item["unit"] = m["unit"]
        if m.get("xbrl"):
            item["xbrl"] = m["xbrl"]
        if m.get("note"):
            item["note"] = m["note"]
        data["measures"][name] = item
    fc = r.free_cash
    data["free_cash"] = {"value": _num(fc.get("value")), "average_3y": _num(fc.get("average_3y")),
                         "stock_comp": _num(fc.get("stock_comp")), "currency": r.currency,
                         "path_5y": {e: _num(v) for e, v in (fc.get("path_5y") or {}).items()}}
    p = r.price
    data["price"] = {"price": _num(p.get("price")), "market_value": _num(p.get("market_value")),
                     "pe": _num(p.get("pe")), "peg": _num(p.get("peg")),
                     "lynch_dividend_ratio": _num(p.get("lynch_dividend_ratio")),
                     "fcf_yield": _num(p.get("fcf_yield")), "fcf_yield_latest": _num(p.get("fcf_yield_latest"))}
    v = verdicts(p)
    data["price"]["verdict"] = {k: (x or NOT_COMPUTED) for k, x in v.items()}
    last = r.last
    if last in r.liquid:
        data["liquid"] = {"value": _num(r.liquid[last].value), "parts": r.liquid[last].parts}
    if last in r.debt:
        data["debt"] = {"value": _num(r.debt[last].value), "parts": r.debt[last].parts}
    why = {w.id: w for w in (part.why if part else [])}
    data["warnings"] = []
    codes = getattr(r, "codes", None) or [f"U{i}" for i in range(1, len(r.flags) + 1)]
    closed = getattr(r, "closed", set())
    for code, f, key in zip(codes, r.flags, _keys([{"name": f["flag"], "detail": f["detail"]} for f in r.flags], "name")):
        w = {"code": code, "name": f["flag"], "flag_status": "closed" if code in closed else "open", "detail": f["detail"],
             "key": key}
        if code in why:  # what the AI said, with its quote (shown only when the quote is in the filing)
            x = why[code]
            w.update({"kind": x.kind or NOT_COMPUTED, "answer": x.answer, "quote": x.quote or None})
        data["warnings"].append(w)
    if part:
        for name, item in data["measures"].items():
            if f"M:{name}" in why:
                x = why[f"M:{name}"]
                item["why"] = {"answer": x.answer, "quote": x.quote or None, "kind": x.kind or NOT_COMPUTED}
    data["info"] = list(r.notes)
    data["gaps"] = [f"{m['figure']} not found ({m['year']})" for m in r.missing]
    if part:
        if part.thesis_status:
            data["thesis_status"] = part.thesis_status
        if part.check:
            data["thesis_check"] = {k: v for k, v in part.check.items() if v not in (None, "")}
        if part.audits:
            data["audits"] = [{"audit": a.audit, "result": a.result, "model": a.model or None,
                               "items": [{"id": i["id"], "verdict": i["verdict"], "reason": i["reason"]}
                                         for i in a.items if i["verdict"] != "pass"] or None,
                               "error": a.error} for a in part.audits]
        if part.unverified:
            data["unverified"] = "yes"
        if part.sell:
            data["sell_suggestion"] = {"trigger": part.sell["trigger"], "status": part.sell["status"]}
    return data


def _summary(r: Result) -> str:
    if r.out_of_scope:
        return f"unclear — out of scope: {r.out_of_scope} (SIC {r.sic}). The 10 measures and the price line are not computed."
    dec = [f"{n} {m['mark'] or NOT_COMPUTED}" for n, m in r.measures.items() if m["decisive"]]
    s = f"Grade {r.grade} · {r.lynch_type or 'type unclear'}. Decisive measures: {', '.join(dec) or 'none'}."
    if r.rules:
        s += f" Rules applied: {', '.join(r.rules)}."
    if r.flags:
        s += f" Flags: {', '.join(sorted({f['flag'] for f in r.flags}))}."
    if r.price.get("market_value") is None:
        s += " Price line not computed (no market value from Yahoo)."
    return s


def _thesis_section(part, previous_thesis_date: str | None) -> str:
    if part is None:
        return "Not written yet — the first thesis is written by agent 3's AI (run with --ai or /analyze)."
    from agents.analysis.ai import thesis_text

    if part.thesis:
        return thesis_text(part.thesis)
    if part.check:
        c = part.check
        line = f"Unchanged — see the thesis of {previous_thesis_date}. Status: {c['status']}. {c['reason']}".strip()
        return line + (f'\nQuote: "{c["quote"]}"' if c["quote"] else "")
    if previous_thesis_date:
        return f"Unchanged — see the thesis of {previous_thesis_date}. Not checked this time: the AI answer could not be used (see the info lines)."
    return "Not written yet — the AI answer could not be used this time (see the info lines)."


def fundamental_entry(r: Result, source: dict, day: str, previous: dict | None, part=None,
                      previous_thesis_date: str | None = None) -> str:
    heading = f"## {day} · fundamental · agent_3 · {source['label']}\n"
    if previous is None:
        changed = "First fundamental entry."
    else:
        bits = []
        if previous.get("grade") != r.grade:
            bits.append(f"grade {previous.get('grade')} → {r.grade}")
        if previous.get("lynch_type") != r.lynch_type:
            bits.append(f"type {previous.get('lynch_type')} → {r.lynch_type}")
        changed = ("; ".join(bits) + ".") if bits else "Grade and type unchanged."
    summary = _summary(r)
    if part is not None and part.unverified:
        summary += " UNVERIFIED: the auditor disagrees (see the audits in the data block)."
    return (heading + _block(data_block(r, source, part)) + "### Summary\n" + summary + "\n### Thesis\n"
            + _thesis_section(part, previous_thesis_date) + "\n### What changed\n" + changed + "\n")
